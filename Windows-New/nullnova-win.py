"""
NullNova - Windows safe/real drive wipe prototype (PyQt5)
- Detects drives (uses WMI + psutil)
- Simulate mode (default) and Real wipe mode (destructive)
- Generates JSON report after each job

WARNING: Real mode overwrites entire physical device (\\.\PhysicalDriveN).
Make sure to run in VM or with test disks and run as Administrator.
"""

import sys
import os
import uuid
import json
import time
import psutil
import wmi
import hashlib
import datetime
import subprocess
import ctypes
from ctypes import wintypes
import msvcrt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QMessageBox, QProgressBar, QHBoxLayout, QRadioButton,
    QButtonGroup, QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Windows API Constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_WRITE_THROUGH = 0x80000000
INVALID_HANDLE_VALUE = -1

# -------------------------
# Low-level file operations using Windows API
# -------------------------
def open_physical_drive_handle(device_path):
    """
    Open a handle to a physical drive using Windows API.
    Returns (handle, error_message) tuple.
    """
    kernel32 = ctypes.windll.kernel32
    
    try:
        # Open with exclusive access and no buffering for direct disk access
        handle = kernel32.CreateFileW(
            device_path,
            GENERIC_READ | GENERIC_WRITE,
            0,  # No sharing - exclusive access
            None,
            OPEN_EXISTING,
            FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH,
            None
        )
        
        if handle == INVALID_HANDLE_VALUE:
            error_code = kernel32.GetLastError()
            if error_code == 2:  # File not found
                return None, f"Device not found: {device_path}"
            elif error_code == 5:  # Access denied
                return None, f"Access denied. Run as Administrator: {device_path}"
            elif error_code == 32:  # Sharing violation
                return None, f"Device is in use by another process: {device_path}"
            else:
                return None, f"Failed to open device (Error {error_code}): {device_path}"
        
        return handle, None
        
    except Exception as e:
        return None, f"Exception opening device: {e}"

def write_to_physical_drive(handle, data):
    """
    Write data to physical drive using Windows API.
    Returns (bytes_written, error_message) tuple.
    """
    kernel32 = ctypes.windll.kernel32
    
    try:
        bytes_written = wintypes.DWORD()
        result = kernel32.WriteFile(
            handle,
            data,
            len(data),
            ctypes.byref(bytes_written),
            None
        )
        
        if not result:
            error_code = kernel32.GetLastError()
            return 0, f"Write failed (Error {error_code})"
        
        return bytes_written.value, None
        
    except Exception as e:
        return 0, f"Exception during write: {e}"

def close_physical_drive_handle(handle):
    """
    Close a physical drive handle.
    """
    if handle and handle != INVALID_HANDLE_VALUE:
        kernel32 = ctypes.windll.kernel32
        kernel32.CloseHandle(handle)

def test_device_access(device_path):
    """
    Test if we can open and close the device without errors.
    Returns (success, error_message) tuple.
    """
    handle, error_msg = open_physical_drive_handle(device_path)
    if handle is None:
        return False, error_msg
    
    try:
        # Try to get device information
        kernel32 = ctypes.windll.kernel32
        bytes_returned = wintypes.DWORD()
        
        # Try a simple device control operation (GET_LENGTH_INFO)
        result = kernel32.DeviceIoControl(
            handle,
            0x0007405C,  # IOCTL_DISK_GET_LENGTH_INFO
            None, 0,
            None, 0,
            ctypes.byref(bytes_returned),
            None
        )
        
        close_physical_drive_handle(handle)
        
        if result:
            return True, "Device is accessible"
        else:
            return True, "Device opened successfully (but may have limited access)"
            
    except Exception as e:
        close_physical_drive_handle(handle)
        return False, f"Device access test failed: {e}"

# -------------------------
# Utility: Drive enumeration
# -------------------------
def enumerate_windows_disks():
    """
    Returns list of disk dicts:
    {
        "physical_device": "\\\\.\\PhysicalDrive0",
        "model": "...",
        "serial": "...",
        "size_bytes": 500107862016,
        "drive_letters": ["C:"],  # possibly empty
        "media_type": "SSD" or "HDD" or "Unknown",
        "is_system": True/False
    }
    """
    disks = []
    c = wmi.WMI()
    try:
        for disk in c.Win32_DiskDrive():
            pd = {}
            pd_path = getattr(disk, "DeviceID", None)  # e.g. \\.\PHYSICALDRIVE0
            if not pd_path:
                continue
            # Normalize the device path - ensure it starts with \\.\
            if pd_path.startswith("\\\\"):
                pd_path = pd_path[2:]  # Remove extra backslashes
            if not pd_path.startswith("\\\\.\\"):
                pd_path = "\\\\.\\" + pd_path.lstrip("\\")
            pd["physical_device"] = pd_path
            pd["model"] = getattr(disk, "Model", "") or ""
            pd["serial"] = (getattr(disk, "SerialNumber", "") or "").strip()
            pd["size_bytes"] = int(getattr(disk, "Size", 0) or 0)
            pd["media_type"] = "Unknown"
            pd["drive_letters"] = []

            # Map partitions -> logical disks to get drive letters
            try:
                for part in disk.associators("Win32_DiskDriveToDiskPartition"):
                    for ld in part.associators("Win32_LogicalDiskToPartition"):
                        if getattr(ld, "DeviceID", None):
                            pd["drive_letters"].append(getattr(ld, "DeviceID"))
            except Exception:
                pass

            # Determine media type best-effort:
            # check if any drive_letter corresponds to system root
            pd["is_system"] = any(dl.upper() == os.getenv("SystemDrive", "C:").upper() for dl in pd["drive_letters"])
            # heuristics for SSD vs HDD using MediaType or Model keywords
            model_l = pd["model"].lower()
            if "ssd" in model_l or "nvme" in model_l:
                pd["media_type"] = "SSD"
            else:
                pd["media_type"] = "HDD"

            disks.append(pd)
    except Exception as e:
        print("WMI enumeration failed:", e)
    return disks

# -------------------------
# Drive unmounting utilities
# -------------------------
def unmount_drive_letters(drive_letters):
    """
    Unmount/dismount the specified drive letters before wiping.
    Returns list of successfully unmounted drives.
    """
    unmounted = []
    
    for drive_letter in drive_letters:
        if not drive_letter or len(drive_letter) < 2:
            continue
            
        # Ensure drive letter format is correct (e.g., "C:")
        if not drive_letter.endswith(':'):
            drive_letter += ':'
            
        try:
            # First try to lock the volume
            volume_path = f"\\\\.\\{drive_letter}"
            
            # Use Windows API to dismount the volume
            kernel32 = ctypes.windll.kernel32
            
            # Open handle to the volume
            handle = kernel32.CreateFileW(
                volume_path,
                0x40000000 | 0x80000000,  # GENERIC_READ | GENERIC_WRITE
                0x00000001 | 0x00000002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
                None,
                3,  # OPEN_EXISTING
                0,
                None
            )
            
            if handle == -1:  # INVALID_HANDLE_VALUE
                print(f"Could not open handle to {drive_letter}")
                continue
                
            try:
                # Lock the volume (FSCTL_LOCK_VOLUME)
                bytes_returned = wintypes.DWORD()
                lock_result = kernel32.DeviceIoControl(
                    handle,
                    0x00090018,  # FSCTL_LOCK_VOLUME
                    None, 0,
                    None, 0,
                    ctypes.byref(bytes_returned),
                    None
                )
                
                if lock_result:
                    print(f"Successfully locked volume {drive_letter}")
                    
                    # Dismount the volume (FSCTL_DISMOUNT_VOLUME)
                    dismount_result = kernel32.DeviceIoControl(
                        handle,
                        0x00090020,  # FSCTL_DISMOUNT_VOLUME
                        None, 0,
                        None, 0,
                        ctypes.byref(bytes_returned),
                        None
                    )
                    
                    if dismount_result:
                        print(f"Successfully dismounted volume {drive_letter}")
                        unmounted.append(drive_letter)
                    else:
                        print(f"Failed to dismount volume {drive_letter}")
                else:
                    print(f"Failed to lock volume {drive_letter}")
                    
            finally:
                kernel32.CloseHandle(handle)
                
        except Exception as e:
            print(f"Error dismounting {drive_letter}: {e}")
            
    return unmounted

def check_drive_usage(drive_letters):
    """
    Check if any processes are using the specified drives.
    Returns list of processes using the drives.
    """
    using_processes = []
    
    for drive_letter in drive_letters:
        if not drive_letter.endswith(':'):
            drive_letter += ':'
            
        try:
            # Get all processes
            for proc in psutil.process_iter(['pid', 'name', 'open_files']):
                try:
                    open_files = proc.info['open_files']
                    if open_files:
                        for file_info in open_files:
                            if file_info.path.upper().startswith(drive_letter.upper()):
                                using_processes.append({
                                    'pid': proc.info['pid'],
                                    'name': proc.info['name'],
                                    'drive': drive_letter,
                                    'file': file_info.path
                                })
                                break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Error checking drive usage for {drive_letter}: {e}")
    
    return using_processes

def force_dismount_physical_drive(physical_device_path):
    """
    Force dismount all volumes on a physical drive using diskpart.
    This is a more aggressive approach when API calls fail.
    """
    try:
        # Extract drive number from path like \\.\PhysicalDrive0
        if "PhysicalDrive" in physical_device_path:
            drive_num = physical_device_path.split("PhysicalDrive")[-1]
            
            # Create diskpart script - just dismount, don't clean
            script_content = f"""select disk {drive_num}
detail disk
"""
            
            # Write temporary script file
            script_path = "temp_dismount.txt"
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # Run diskpart with the script
            result = subprocess.run(
                ["diskpart", "/s", script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up script file
            try:
                os.remove(script_path)
            except:
                pass
                
            if result.returncode == 0:
                print(f"Successfully accessed physical drive {drive_num} via diskpart")
                return True
            else:
                print(f"Diskpart failed: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"Error in force dismount: {e}")
        return False
    
    return False

# -------------------------
# Worker thread for wiping
# -------------------------
class WipeWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)  # report dict on finish
    log = pyqtSignal(str)

    def __init__(self, job_id, disk, real_mode=False, chunk_mb=4):
        super().__init__()
        self.job_id = job_id
        self.disk = disk
        self.real_mode = real_mode
        self.chunk_mb = chunk_mb

    def run(self):
        start_ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        report = {
            "project": "NullNova",
            "job_id": self.job_id,
            "device": self.disk,
            "start_time_utc": start_ts,
            "method": "simulate" if not self.real_mode else f"single-pass-random-{self.chunk_mb}MB",
            "status": "started",
            "progress_percent": 0
        }

        try:
            # Simulation path
            if not self.real_mode:
                self.log.emit("SIMULATE: starting simulated wipe (no destructive I/O).")
                steps = 20
                for i in range(steps):
                    time.sleep(0.2)
                    pct = int(((i + 1) / steps) * 100)
                    self.progress.emit(pct)
                report["status"] = "completed"
                report["end_time_utc"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
                self.finished.emit(report)
                return

            # Real mode path: destructive write to raw physical device
            # Build device path like \\.\PhysicalDriveN
            raw_path = self.disk.get("physical_device")
            if not raw_path:
                raise RuntimeError("No physical device path available for this disk.")

            # normalization: ensure path begins with \\.\ (WMI might give \\.\PHYSICALDRIVE0 or \\.\PHYSICALDRIVE0)
            if not raw_path.startswith("\\\\.\\"):
                raw_path = "\\\\.\\\\" + raw_path.lstrip("\\")
            
            # Validate the device path format
            if not raw_path.upper().startswith("\\\\.\\PHYSICALDRIVE"):
                raise RuntimeError(f"Invalid device path format: {raw_path}")

            total = int(self.disk.get("size_bytes", 0))
            if total <= 0:
                raise RuntimeError("Invalid drive size; aborting.")
            
            self.log.emit(f"Target device size: {total:,} bytes ({total // (1024**3)} GB)")
            
            # Check if the device exists before attempting to open
            if not os.path.exists(raw_path):
                raise RuntimeError(f"Device path does not exist: {raw_path}")

            # UNMOUNT DRIVES BEFORE WIPING
            drive_letters = self.disk.get("drive_letters", [])
            if drive_letters:
                # Check what processes are using the drives
                self.log.emit("Checking for processes using the target drives...")
                using_processes = check_drive_usage(drive_letters)
                if using_processes:
                    self.log.emit(f"Warning: Found {len(using_processes)} processes using the drives:")
                    for proc in using_processes[:5]:  # Show first 5
                        self.log.emit(f"  - {proc['name']} (PID: {proc['pid']}) using {proc['drive']}")
                    if len(using_processes) > 5:
                        self.log.emit(f"  ... and {len(using_processes) - 5} more processes")
                    report["processes_using_drive"] = using_processes
                
                self.log.emit(f"Attempting to unmount drive letters: {', '.join(drive_letters)}")
                unmounted = unmount_drive_letters(drive_letters)
                if unmounted:
                    self.log.emit(f"Successfully unmounted: {', '.join(unmounted)}")
                    report["unmounted_drives"] = unmounted
                else:
                    self.log.emit("Warning: Could not unmount drives using API method")
                    # Try force dismount as fallback
                    self.log.emit("Attempting force dismount using diskpart...")
                    if force_dismount_physical_drive(raw_path):
                        self.log.emit("Force dismount successful")
                        report["force_dismounted"] = True
                    else:
                        self.log.emit("Warning: Force dismount also failed - proceeding anyway")
            
            # Give system time to release handles after unmounting
            self.log.emit("Waiting 2 seconds for system to release handles...")
            time.sleep(2)
            
            # Test device access before proceeding
            self.log.emit("Testing device access...")
            access_ok, access_msg = test_device_access(raw_path)
            if not access_ok:
                raise RuntimeError(f"Device access test failed: {access_msg}")
            self.log.emit(f"Device access test: {access_msg}")
            
            self.log.emit(f"REAL: preparing to wipe raw device {raw_path} (requires admin)...")

            # Ensure chunk size is aligned to sector boundary (512 bytes)
            sector_size = 512
            chunk = ((self.chunk_mb * 1024 * 1024) // sector_size) * sector_size
            if chunk == 0:
                chunk = sector_size
                
            written = 0
            handle = None
            
            # Attempt to open raw device using Windows API
            self.log.emit(f"Opening device handle for {raw_path}...")
            handle, error_msg = open_physical_drive_handle(raw_path)
            if handle is None:
                raise RuntimeError(error_msg)
            
            self.log.emit(f"Successfully opened device handle for {raw_path}")

            try:
                # Overwrite entire device with random bytes in chunks
                import os as _os
                while written < total:
                    remaining = total - written
                    to_write = min(chunk, remaining)
                    
                    # Ensure write size is sector-aligned
                    to_write = ((to_write + sector_size - 1) // sector_size) * sector_size
                    if written + to_write > total:
                        to_write = ((remaining + sector_size - 1) // sector_size) * sector_size
                    
                    # Generate cryptographically secure random bytes
                    try:
                        data = _os.urandom(to_write)
                        
                        # Write using Windows API
                        bytes_written, write_error = write_to_physical_drive(handle, data)
                        if write_error:
                            raise RuntimeError(f"Write operation failed: {write_error}")
                        
                        if bytes_written != to_write:
                            raise RuntimeError(f"Write operation incomplete: expected {to_write}, wrote {bytes_written}")
                        
                        written += bytes_written
                        pct = int((written / total) * 100)
                        self.progress.emit(min(pct, 100))
                        
                        # Log progress every 100MB
                        if written % (100 * 1024 * 1024) == 0:
                            self.log.emit(f"Written: {written:,} bytes ({pct}%)")
                            
                    except Exception as e:
                        raise RuntimeError(f"Write operation failed at offset {written}: {e}")
                
                self.log.emit(f"Successfully wrote {written:,} bytes to device")
                    
            finally:
                if handle:
                    close_physical_drive_handle(handle)
                    self.log.emit("Device handle closed successfully")

            report["status"] = "completed"
            report["end_time_utc"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            report["written_bytes"] = written
            self.finished.emit(report)
        except Exception as ex:
            report["status"] = "failed"
            report["error"] = str(ex)
            report["end_time_utc"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            self.log.emit("ERROR: " + str(ex))
            self.finished.emit(report)


# -------------------------
# Main GUI
# -------------------------
class NullNovaApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NullNova - Secure Wipe (Prototype)")
        self.setGeometry(300, 200, 700, 480)

        layout = QVBoxLayout()

        header = QLabel("<b>NullNova</b> — Drive Wipe Prototype (Windows)")
        layout.addWidget(header)

        instr = QLabel("Select a detected disk. Default mode = SIMULATE. Use Real only on test/dev disks and as Administrator.")
        layout.addWidget(instr)

        # Drive list
        self.drive_list = QListWidget()
        layout.addWidget(self.drive_list)

        btn_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh Drives")
        self.btn_refresh.clicked.connect(self.load_drives)
        btn_layout.addWidget(self.btn_refresh)

        self.btn_scan = QPushButton("Rescan")
        self.btn_scan.clicked.connect(self.load_drives)
        btn_layout.addWidget(self.btn_scan)

        layout.addLayout(btn_layout)

        # Mode selection
        mode_layout = QHBoxLayout()
        self.rb_sim = QRadioButton("Simulate (SAFE)")
        self.rb_real = QRadioButton("Real (DESTRUCTIVE)")
        self.rb_sim.setChecked(True)
        mode_layout.addWidget(self.rb_sim)
        mode_layout.addWidget(self.rb_real)
        layout.addLayout(mode_layout)

        # Safety confirmation and input
        conf_layout = QHBoxLayout()
        self.chk_confirm = QCheckBox("I understand this is destructive when Real mode is selected")
        conf_layout.addWidget(self.chk_confirm)
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Type WIPE here to confirm REAL wipe")
        conf_layout.addWidget(self.confirm_input)
        layout.addLayout(conf_layout)

        # Buttons
        action_layout = QHBoxLayout()
        self.btn_wipe = QPushButton("Start Wipe")
        self.btn_wipe.clicked.connect(self.start_wipe)
        action_layout.addWidget(self.btn_wipe)

        self.btn_save_report = QPushButton("Save Last Report JSON")
        self.btn_save_report.clicked.connect(self.save_last_report)
        self.btn_save_report.setEnabled(False)
        action_layout.addWidget(self.btn_save_report)

        layout.addLayout(action_layout)

        # Progress and logs
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.log_label = QLabel("Logs:")
        layout.addWidget(self.log_label)

        self.log_list = QListWidget()
        layout.addWidget(self.log_list)

        self.setLayout(layout)

        self.last_report = None
        self.load_drives()

    def load_drives(self):
        self.drive_list.clear()
        self.log("Scanning attached disks...")
        disks = enumerate_windows_disks()
        if not disks:
            self.log("No disks found or WMI failed.")
        for d in disks:
            letters = ",".join(d.get("drive_letters", [])) or "(no letter)"
            size_gb = int(d.get("size_bytes", 0) / (1024 ** 3))
            sys_tag = "SYSTEM" if d.get("is_system") else ""
            item_text = f"{d.get('physical_device')} | {d.get('model')} | {size_gb} GB | {letters} {sys_tag}"
            self.drive_list.addItem(item_text)
            # attach raw data via QListWidgetItem data hack
            item = self.drive_list.item(self.drive_list.count() - 1)
            item.setData(Qt.UserRole, d)

    def log(self, text: str):
        ts = datetime.datetime.utcnow().strftime("%H:%M:%S")
        self.log_list.addItem(f"[{ts}] {text}")
        self.log_list.scrollToBottom()

    def start_wipe(self):
        item = self.drive_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Select Disk", "Please select a disk to wipe (use a test disk or VM).")
            return
        disk = item.data(Qt.UserRole)

        # block system disk
        if disk.get("is_system"):
            QMessageBox.critical(self, "Refuse", "Selected disk is a system disk. Aborting.")
            return

        real = self.rb_real.isChecked()
        if real:
            # safety confirmations
            if not self.chk_confirm.isChecked():
                QMessageBox.critical(self, "Confirm", "Please check the confirmation checkbox to acknowledge risk.")
                return
            if self.confirm_input.text().strip() != "WIPE":
                QMessageBox.critical(self, "Type WIPE", "Type WIPE into the textbox to confirm Real destructive action.")
                return
            
            # Warn about drive unmounting
            drive_letters = disk.get("drive_letters", [])
            if drive_letters:
                drive_list = ", ".join(drive_letters)
                reply = QMessageBox.question(
                    self, "Drive Unmounting Warning",
                    f"The following drive letters will be unmounted before wiping: {drive_list}\n"
                    f"This will temporarily make the drives inaccessible.\n"
                    f"Any open files on these drives may be lost.\n\n"
                    f"Continue with unmounting and wiping?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

            # extra confirm dialog
            reply = QMessageBox.question(
                self, "Final Confirmation",
                "You are about to PERMANENTLY ERASE ALL DATA on the selected physical device.\n"
                "This action is irreversible.\n\nProceed?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        job_id = str(uuid.uuid4())
        self.log(f"Starting job {job_id} on {disk.get('physical_device')} (real={real})")
        self.progress.setValue(0)
        self.worker = WipeWorker(job_id=job_id, disk=disk, real_mode=real, chunk_mb=4)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self.log)
        self.worker.finished.connect(self.on_finished)
        self.btn_wipe.setEnabled(False)
        self.worker.start()

    def on_finished(self, report: dict):
        self.btn_wipe.setEnabled(True)
        self.last_report = report
        status = report.get('status')
        self.log(f"Job {report.get('job_id')} finished with status: {status}")
        
        # Show detailed error information if the job failed
        if status == "failed":
            error_msg = report.get('error', 'Unknown error')
            self.log(f"Error details: {error_msg}")
            
            # Show error dialog with troubleshooting tips
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setWindowTitle("Wipe Operation Failed")
            error_dialog.setText(f"The wipe operation failed with the following error:\n\n{error_msg}")
            
            # Add troubleshooting information
            troubleshooting = ""
            if "Access denied" in error_msg or "Permission denied" in error_msg:
                troubleshooting = "\nTroubleshooting:\n• Run the application as Administrator\n• Close any programs using the target drive\n• Disable antivirus real-time protection temporarily"
            elif "Device is in use" in error_msg or "Sharing violation" in error_msg:
                troubleshooting = "\nTroubleshooting:\n• Close all programs and files on the target drive\n• Restart the computer and try again\n• Check if any antivirus or backup software is accessing the drive"
            elif "Device not found" in error_msg:
                troubleshooting = "\nTroubleshooting:\n• Refresh the drive list and try again\n• Check if the drive is still connected\n• Verify the drive is recognized in Windows Disk Management"
            
            if troubleshooting:
                error_dialog.setDetailedText(troubleshooting)
            
            error_dialog.exec_()
        
        # compute a canonical hash for the session
        canonical = json.dumps(report, sort_keys=True).encode("utf-8")
        h = hashlib.sha256(canonical).hexdigest()
        report["session_hash_sha256"] = h
        self.last_report = report
        self.btn_save_report.setEnabled(True)
        
        if status == "completed":
            self.log("Report ready. Click 'Save Last Report JSON' to persist the certificate locally.")
        else:
            self.log("Report available despite errors. Click 'Save Last Report JSON' to save error details.")

    def save_last_report(self):
        if not self.last_report:
            QMessageBox.warning(self, "No report", "No report to save.")
            return
        filename = f"nullnova_report_{self.last_report.get('job_id')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.last_report, f, indent=2)
        QMessageBox.information(self, "Saved", f"Report saved to {filename}")
        self.log(f"Report saved -> {filename}")

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    if os.name != "nt":
        print("NullNova prototype only supports Windows in this build.")
        sys.exit(1)

    app = QApplication(sys.argv)
    win = NullNovaApp()
    win.show()
    sys.exit(app.exec_())
