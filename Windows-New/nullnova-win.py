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
            self.log.emit(f"REAL: opening raw device {raw_path} (requires admin)...")

            total = int(self.disk.get("size_bytes", 0))
            if total <= 0:
                raise RuntimeError("Invalid drive size; aborting.")

            chunk = self.chunk_mb * 1024 * 1024
            written = 0
            # Attempt to open raw device for binary write
            # This will require admin privileges
            try:
                # open in binary mode
                f = open(raw_path, "r+b", buffering=0)
            except PermissionError as pe:
                raise RuntimeError("Permission denied. Please run as Administrator. " + str(pe))
            except Exception as e:
                raise RuntimeError("Failed to open raw device. " + str(e))

            try:
                # Overwrite entire device with random bytes in chunks
                import os as _os
                while written < total:
                    to_write = min(chunk, total - written)
                    # cryptographically secure random bytes
                    data = _os.urandom(to_write)
                    f.write(data)
                    written += to_write
                    pct = int((written / total) * 100)
                    self.progress.emit(pct if pct <= 100 else 100)
                f.flush()
                # optionally fsync not available for raw device but flush was called
            finally:
                try:
                    f.close()
                except Exception:
                    pass

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
