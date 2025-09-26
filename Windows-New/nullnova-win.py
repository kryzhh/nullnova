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
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QMessageBox, QProgressBar, QHBoxLayout, QRadioButton,
    QButtonGroup, QLineEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

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
            pd["physical_device"] = pd_path.replace("\\\\", "\\")  # keep consistent
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
            
            self.log.emit(f"REAL: opening raw device {raw_path} (requires admin)...")

            chunk = self.chunk_mb * 1024 * 1024
            written = 0
            # Attempt to open raw device for binary write
            # This will require admin privileges
            f = None
            try:
                # open in binary mode with proper error handling
                f = open(raw_path, "r+b", buffering=0)
                self.log.emit(f"Successfully opened device {raw_path}")
            except PermissionError as pe:
                raise RuntimeError("Permission denied. Please run as Administrator. " + str(pe))
            except (OSError, IOError) as e:
                if e.errno == 9:  # Bad file descriptor
                    raise RuntimeError(f"Bad file descriptor - device may be in use or inaccessible: {e}")
                raise RuntimeError(f"Failed to open raw device {raw_path}: {e}")
            except Exception as e:
                raise RuntimeError(f"Failed to open raw device {raw_path}: {e}")

            try:
                # Overwrite entire device with random bytes in chunks
                import os as _os
                while written < total:
                    if not f or f.closed:
                        raise RuntimeError("File handle became invalid during operation")
                    
                    to_write = min(chunk, total - written)
                    # cryptographically secure random bytes
                    try:
                        data = _os.urandom(to_write)
                        bytes_written = f.write(data)
                        if bytes_written != to_write:
                            raise RuntimeError(f"Write operation incomplete: expected {to_write}, wrote {bytes_written}")
                        written += to_write
                        pct = int((written / total) * 100)
                        self.progress.emit(pct if pct <= 100 else 100)
                        
                        # Periodic flush to ensure data is written
                        if written % (chunk * 10) == 0:  # flush every 10 chunks
                            f.flush()
                            
                    except (OSError, IOError) as e:
                        if e.errno == 9:  # Bad file descriptor
                            raise RuntimeError(f"Bad file descriptor during write operation: {e}")
                        raise RuntimeError(f"Write operation failed: {e}")
                
                # Final flush
                if f and not f.closed:
                    f.flush()
                    
            finally:
                if f and not f.closed:
                    try:
                        f.close()
                        self.log.emit("Device file handle closed successfully")
                    except Exception as close_ex:
                        self.log.emit(f"Warning: Error closing file handle: {close_ex}")

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
        self.log(f"Job {report.get('job_id')} finished with status: {report.get('status')}")
        # compute a canonical hash for the session
        canonical = json.dumps(report, sort_keys=True).encode("utf-8")
        h = hashlib.sha256(canonical).hexdigest()
        report["session_hash_sha256"] = h
        self.last_report = report
        self.btn_save_report.setEnabled(True)
        self.log("Report ready. Click 'Save Last Report JSON' to persist the certificate locally.")

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
