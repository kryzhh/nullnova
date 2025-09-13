#!/usr/bin/env python3
# NullNova Wiper - GUI Frontend (Rufus-style)

import sys
import ctypes
from PyQt6 import QtWidgets, QtCore

# Import your existing main file functions
import main as engine  # <-- rename your original file to main.py for clean imports

class WipeThread(QtCore.QThread):
    progress = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal(bool, str)

    def __init__(self, device_info):
        super().__init__()
        self.device_info = device_info
        self._stop_flag = False

    def run(self):
        try:
            # Run full wipe using your engine function
            success = engine.wipe_device(self.device_info["name"], self.device_info)

            if success:
                cert_path = engine.create_wipe_certificate(self.device_info)
                self.finished.emit(True, cert_path)
            else:
                self.finished.emit(False, "Wipe failed")

        except Exception as e:
            self.finished.emit(False, str(e))

    def stop(self):
        self._stop_flag = True


class NullNovaGUI(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NullNova Wiper (DoD 3-Pass)")
        self.setFixedSize(500, 350)

        layout = QtWidgets.QVBoxLayout()

        # Drive selection
        self.drive_box = QtWidgets.QComboBox()
        self.refresh_button = QtWidgets.QPushButton("Refresh Drives")
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.drive_box)
        hl.addWidget(self.refresh_button)
        layout.addLayout(hl)

        # Controls
        self.start_button = QtWidgets.QPushButton("Start Wipe")
        self.progress_bar = QtWidgets.QProgressBar()
        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)

        layout.addWidget(self.start_button)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_box)

        self.setLayout(layout)

        # Connections
        self.refresh_button.clicked.connect(self.load_drives)
        self.start_button.clicked.connect(self.start_wipe)

        self.wipe_thread = None
        self.load_drives()

    def log(self, msg):
        self.log_box.append(msg)

    def load_drives(self):
        self.drive_box.clear()
        drives = engine.get_physical_drives()
        for d in drives:
            label = f"{d['friendly_name']} - {d['size_gb']} GB"
            self.drive_box.addItem(label, d)
        if not drives:
            self.log("[!] No removable drives found")

    def start_wipe(self):
        data = self.drive_box.currentData()
        if not data:
            self.log("[!] No drive selected")
            return

        confirm = QtWidgets.QMessageBox.warning(
            self, "Confirm Wipe",
            f"⚠️ WARNING: This will erase all data on {data['friendly_name']} "
            f"({data['size_gb']} GB).\n\nType YES to continue.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        if confirm != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        self.progress_bar.setValue(0)
        self.log_box.clear()
        self.log(f"[*] Starting wipe on {data['friendly_name']}...")

        self.wipe_thread = WipeThread(data)
        self.wipe_thread.progress.connect(self.update_progress)
        self.wipe_thread.finished.connect(self.wipe_done)
        self.wipe_thread.start()

    def update_progress(self, percent, msg):
        self.progress_bar.setValue(percent)
        self.log(msg)

    def wipe_done(self, success, message):
        if success:
            self.log(f"[+] Wipe completed. Certificate: {message}")
            QtWidgets.QMessageBox.information(self, "Done", f"Wipe complete.\nCertificate: {message}")
        else:
            self.log(f"[!] Wipe failed: {message}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Wipe failed: {message}")


def main():
    app = QtWidgets.QApplication(sys.argv)

    # Require admin
    if not engine.requires_admin():
        QtWidgets.QMessageBox.critical(None, "Admin Required", "Please run as Administrator.")
        return

    window = NullNovaGUI()
    window.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()
