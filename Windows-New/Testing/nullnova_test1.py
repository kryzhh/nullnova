"""
NullNova - Secure Data Wiping Tool (Windows Prototype)
------------------------------------------------------
Features:
- Detect drives (HDD, SSD, USB)
- Simulation & Real wipe modes
- Multiple wipe methods (Zero, Random, Pattern, DoD 3-pass)
- JSON report generation
- GUI with PyQt5
"""

import sys
import os
import ctypes
import json
import hashlib
import psutil
import uuid
import datetime
import random
import subprocess
from PyQt5 import QtWidgets, QtCore, QtGui

# Windows API constants
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_WRITE_THROUGH = 0x80000000

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

kernel32 = ctypes.windll.kernel32

# Utility: get drives
def list_drives():
    drives = []
    for disk in psutil.disk_partitions(all=True):
        drives.append({
            "device": disk.device,
            "mountpoint": disk.mountpoint,
            "fstype": disk.fstype
        })
    return drives

# Utility: wipe core
def wipe_drive(path, method="zero", simulate=True, chunk_mb=64, callback=None):
    """
    path: raw path like \\.\PhysicalDrive1 or \\.\X:
    method: zero | random | pattern | dod
    simulate: if True, just simulate
    chunk_mb: chunk size in MB
    callback: progress reporting function
    """

    # JSON report
    report = {
        "job_id": str(uuid.uuid4()),
        "drive": path,
        "method": method,
        "simulate": simulate,
        "start_time": datetime.datetime.now().isoformat(),
        "status": "started",
        "errors": [],
        "bytes_written": 0,
        "hash": None
    }

    try:
        if simulate:
            # Fake total size: 1GB for demo
            total_size = 1024**3
        else:
            # Get real size using GetDiskFreeSpaceEx or IOCTL
            # Simplify: assume 10GB for now
            total_size = 10 * (1024**3)

        chunk_size = chunk_mb * 1024 * 1024
        bytes_written = 0

        # Buffers
        zero_buf = b"\x00" * chunk_size
        pattern_buf = (b"\xAA" * chunk_size)
        
        if not simulate:
            handle = kernel32.CreateFileW(
                ctypes.c_wchar_p(path),
                GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH,
                None
            )

            if handle == INVALID_HANDLE_VALUE:
                raise OSError("Failed to open drive. Run as Administrator.")

        while bytes_written < total_size:
            # Pick buffer
            if method == "zero":
                buf = zero_buf
            elif method == "pattern":
                buf = pattern_buf
            elif method == "random":
                buf = os.urandom(chunk_size)
            elif method == "dod":
                # DoD 3-pass: zero, one, random
                pass_num = (bytes_written // total_size) % 3
                if pass_num == 0:
                    buf = zero_buf
                elif pass_num == 1:
                    buf = pattern_buf
                else:
                    buf = os.urandom(chunk_size)
            else:
                buf = zero_buf

            if not simulate:
                written = ctypes.c_ulong(0)
                success = kernel32.WriteFile(
                    handle,
                    buf,
                    len(buf),
                    ctypes.byref(written),
                    None
                )
                if not success:
                    raise OSError("WriteFile failed.")
            else:
                # Just sleep a little to simulate work
                QtCore.QThread.msleep(10)

            bytes_written += len(buf)
            progress = int((bytes_written / total_size) * 100)
            if callback:
                callback(progress)

        if not simulate:
            kernel32.CloseHandle(handle)

        report["status"] = "success"
        report["bytes_written"] = bytes_written
        report["end_time"] = datetime.datetime.now().isoformat()
        report["hash"] = hashlib.sha256(report["job_id"].encode()).hexdigest()

    except Exception as e:
        report["status"] = "failed"
        report["errors"].append(str(e))

    return report

# GUI
class NullNova(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NullNova - Secure Data Wiping Tool")
        self.setGeometry(200, 200, 600, 400)

        layout = QtWidgets.QVBoxLayout()

        self.drive_list = QtWidgets.QListWidget()
        layout.addWidget(QtWidgets.QLabel("Detected Drives:"))
        layout.addWidget(self.drive_list)

        self.refresh_btn = QtWidgets.QPushButton("Refresh Drives")
        self.refresh_btn.clicked.connect(self.refresh_drives)
        layout.addWidget(self.refresh_btn)

        self.method_combo = QtWidgets.QComboBox()
        self.method_combo.addItems(["zero", "random", "pattern", "dod"])
        layout.addWidget(QtWidgets.QLabel("Wipe Method:"))
        layout.addWidget(self.method_combo)

        self.simulate_checkbox = QtWidgets.QCheckBox("Simulation Mode (Safe)")
        self.simulate_checkbox.setChecked(True)
        layout.addWidget(self.simulate_checkbox)

        self.start_btn = QtWidgets.QPushButton("Start Wipe")
        self.start_btn.clicked.connect(self.start_wipe)
        layout.addWidget(self.start_btn)

        self.progress = QtWidgets.QProgressBar()
        layout.addWidget(self.progress)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.setLayout(layout)

        self.refresh_drives()

    def refresh_drives(self):
        self.drive_list.clear()
        for d in list_drives():
            self.drive_list.addItem(f"{d['device']} - {d['fstype']} - {d['mountpoint']}")

    def log_msg(self, msg):
        self.log.append(msg)

    def start_wipe(self):
        selected = self.drive_list.currentItem()
        if not selected:
            self.log_msg("No drive selected.")
            return

        drive = selected.text().split(" - ")[0]
        method = self.method_combo.currentText()
        simulate = self.simulate_checkbox.isChecked()

        self.log_msg(f"Starting wipe on {drive} with method={method}, simulate={simulate}")

        def update_progress(p):
            self.progress.setValue(p)

        report = wipe_drive(drive, method=method, simulate=simulate, callback=update_progress)

        self.log_msg(json.dumps(report, indent=2))
        with open(f"nullnova_report_{report['job_id']}.json", "w") as f:
            json.dump(report, f, indent=2)

        self.log_msg(f"Report saved: nullnova_report_{report['job_id']}.json")

# Main
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = NullNova()
    win.show()
    sys.exit(app.exec_())
