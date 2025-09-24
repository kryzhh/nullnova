#!/usr/bin/env python3
"""
NullNova - Cross-platform Secure Drive Wiper (Windows + Linux)

This single-file GUI app is a refactor of the user's original script to support
both Windows and Linux. It avoids calling external Linux-only tools (dd, tr,
/dev/zero) and instead uses Python's file I/O to write directly to block devices.

IMPORTANT:
 - On Windows you MUST run this script as Administrator.
 - On Linux you MUST run as root or allow escalation (pkexec) before writing to
   raw devices.
 - Writing to raw block devices is destructive. Use carefully.

Dependencies:
 - Python 3.9+
 - pycryptodome (pip install pycryptodome)
 - (Optional) pyudev on Linux to improve device listing (pip install pyudev)

"""

import os
import sys
import platform
import subprocess
import json
import math
import uuid
import datetime
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import secrets
from Crypto.Cipher import AES

DEFAULT_CHUNK_SIZE = 128  # MB
CERTS_DIR = "certs"

WIPE_METHODS = {
    "DoD 5220.22-M (3 passes)": {
        "description": "Writes over your data three times to make it unrecoverable.",
        "pros": ["Very secure","Works well on most drives"],
        "cons": ["Takes longer than basic erasure","Not recommended for SSDs"],
        "suitable_for": "Regular hard drives"
    },
    "Cryptographic Erasure (AES-256)": {
        "description": "Quickly erases data by overwriting with encrypted zeros.",
        "pros": ["Fast","Safe for SSDs"],
        "cons": ["Newer method"],
        "suitable_for": "SSDs and modern drives"
    }
}

# ------------------------ Platform helpers ------------------------

def is_windows():
    return platform.system().lower() == 'windows'


def is_linux():
    return platform.system().lower() == 'linux'


def is_admin():
    if is_windows():
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


# ------------------------ Device enumeration ------------------------

def list_removable_devices_windows():
    """Use wmic to list disks. Returns list of dicts with name, size, size_gb."""
    devices = []
    try:
        proc = subprocess.run(["wmic", "diskdrive", "get", "DeviceID,Size,Model"], capture_output=True, text=True)
        out = proc.stdout.strip().splitlines()
        # Skip header lines - find a line that contains 'DeviceID'
        lines = [l.strip() for l in out if l.strip()]
        if len(lines) <= 1:
            return devices
        # WMIC output sometimes contains a header then CSV-like rows
        # We'll parse lines that look like: \\.
        for line in lines[1:]:
            parts = [p for p in line.split('  ') if p]
            if not parts:
                continue
            # try splitting by whitespace as fallback
            parts = line.split()
            if len(parts) >= 2:
                device_id = parts[0]
                size_str = parts[-1]
                try:
                    size = int(size_str)
                except Exception:
                    size = 0
                # Normalize DeviceID to \.
                name = device_id
                # Convert to physical device path: \\.
                if name and not name.startswith('\\\\'):
                    # If WMIC gave something like "\\.\PHYSICALDRIVE0" keep it
                    pass
                devices.append({
                    'name': name,
                    'size': size,
                    'size_gb': round(size / (1024**3), 2)
                })
    except Exception as e:
        print(f"[WARN] list_removable_devices_windows failed: {e}")
    return devices


def list_removable_devices_linux():
    """Use sysfs to find block devices. Returns list of dicts."""
    devices = []
    try:
        # Try pyudev if available (more robust)
        try:
            import pyudev
            context = pyudev.Context()
            for device in context.list_devices(subsystem='block', DEVTYPE='disk'):
                devnode = device.device_node
                if not devnode:
                    continue
                dev_name = os.path.basename(devnode)
                removable_path = f"/sys/block/{dev_name}/removable"
                try:
                    removable = False
                    if os.path.exists(removable_path):
                        with open(removable_path, 'r') as f:
                            removable = f.read().strip() == '1'
                    # Accept normal disks (sda, sdb, etc.) as choices too
                    size = 0
                    size_path = f"/sys/block/{dev_name}/size"
                    if os.path.exists(size_path):
                        with open(size_path, 'r') as sf:
                            size = int(sf.read().strip()) * 512
                    devices.append({'name': devnode, 'size': size, 'size_gb': round(size/(1024**3),2)})
                except Exception:
                    continue
        except Exception:
            # Fallback: scan /sys/block
            for dev_name in os.listdir('/sys/block'):
                try:
                    removable_path = f"/sys/block/{dev_name}/removable"
                    if os.path.exists(removable_path):
                        with open(removable_path, 'r') as f:
                            removable = f.read().strip() == '1'
                    else:
                        removable = False
                    # Include typical disk names
                    if removable or dev_name.startswith(('sd', 'nvme', 'hd', 'mmcblk')):
                        size_path = f"/sys/block/{dev_name}/size"
                        size = 0
                        if os.path.exists(size_path):
                            with open(size_path, 'r') as sf:
                                size = int(sf.read().strip()) * 512
                        devnode = f"/dev/{dev_name}"
                        devices.append({'name': devnode, 'size': size, 'size_gb': round(size/(1024**3),2)})
                except Exception:
                    continue
    except Exception as e:
        print(f"[WARN] list_removable_devices_linux failed: {e}")
    return devices


def list_removable_devices():
    if is_windows():
        return list_removable_devices_windows()
    elif is_linux():
        return list_removable_devices_linux()
    else:
        return []


# ------------------------ Low-level write helpers ------------------------


def open_device_for_write(path):
    """Open raw device for binary read/write.
    On Windows use \\.\PhysicalDriveX, on Linux use /dev/sdX.
    Caller must ensure admin/root privileges.
    Returns an open file object.
    """
    mode = 'r+b'  # read+write binary
    # On some platforms we may need to open with buffering=0
    return open(path, mode, buffering=0)


def write_pattern_py(device_path, pattern_byte, offset, size, progress_cb=None):
    """Write a pattern byte repeatedly to a device at offset for size bytes."""
    try:
        block = 1024 * 1024  # 1MB blocks
        written = 0
        with open_device_for_write(device_path) as f:
            f.seek(offset)
            while written < size:
                to_write = min(block, size - written)
                if pattern_byte is None:
                    data = os.urandom(to_write)
                else:
                    data = bytes([pattern_byte]) * to_write
                f.write(data)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
                written += to_write
                if progress_cb:
                    progress_cb(written, size)
        return True
    except Exception as e:
        print(f"[ERROR] write_pattern_py failed: {e}")
        return False


def crypto_write_py(device_path, offset, size, progress_cb=None):
    """Perform a cryptographic erase on a region: write zeros then encrypted zeros.
    Uses AES-CTR with a random key and discards the key.
    """
    try:
        block = 1024 * 1024
        # First pass: zeros
        if not write_pattern_py(device_path, 0x00, offset, size, progress_cb):
            return False

        # Second pass: encrypted zeros
        key = secrets.token_bytes(32)
        cipher = AES.new(key, AES.MODE_CTR)
        written = 0
        with open_device_for_write(device_path) as f:
            f.seek(offset)
            while written < size:
                to_write = min(block, size - written)
                plain = b'\x00' * to_write
                enc = cipher.encrypt(plain)
                f.write(enc)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
                written += to_write
                if progress_cb:
                    progress_cb(written, size)
        # Drop key material
        del key, cipher
        return True
    except Exception as e:
        print(f"[ERROR] crypto_write_py failed: {e}")
        return False


def verify_region(device_path, offset, size, expected_pattern=None, sample_bytes=512):
    """Read back a small sample and perform a basic sanity check.
    expected_pattern: if 0x00 or 0xFF provided, we check the first bytes match.
    For random data we do a very basic check that data is not all zeros.
    """
    try:
        with open(device_path, 'rb') as f:
            f.seek(offset)
            data = f.read(min(sample_bytes, size))
            if not data:
                return False
            if expected_pattern is None:
                # expect not-all-zero
                return any(b != 0x00 for b in data)
            else:
                return all(b == expected_pattern for b in data[:len(data)])
    except Exception as e:
        print(f"[ERROR] verify_region failed: {e}")
        return False


# ------------------------ Certificate generation ------------------------


def generate_certificate(device_info, method_name, passes):
    try:
        wipe_id = str(uuid.uuid4())
        cert = {
            "WipeID": wipe_id,
            "Device": device_info['name'],
            "Method": method_name,
            "Passes": passes,
            "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Hash": uuid.uuid5(uuid.NAMESPACE_DNS, wipe_id).hex
        }
        os.makedirs(CERTS_DIR, exist_ok=True)
        cert_path = os.path.join(CERTS_DIR, f"wipe_{wipe_id[:8]}.json")
        with open(cert_path, 'w') as f:
            json.dump(cert, f, indent=2)
        return cert_path
    except Exception as e:
        print(f"[ERROR] generate_certificate failed: {e}")
        raise


# ------------------------ GUI App ------------------------

class NullNovaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NullNova - Secure Drive Wiper")
        self.root.geometry("700x450")
        self.root.resizable(False, False)

        self.selected_device = tk.StringVar()
        self.selected_method = tk.StringVar()
        self.devices = []
        self.chunk_size_mb = tk.IntVar(value=DEFAULT_CHUNK_SIZE)

        self.setup_gui()
        self.refresh_devices()

    def setup_gui(self):
        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky='nsew')

        title = ttk.Label(main, text="NULLNOVA", font=("Segoe UI", 24, 'bold'))
        title.grid(row=0, column=0, columnspan=4, pady=(0,12))

        ttk.Label(main, text="Device:").grid(row=1, column=0, sticky='w')
        self.device_combo = ttk.Combobox(main, textvariable=self.selected_device, state='readonly', width=60)
        self.device_combo.grid(row=1, column=1, columnspan=2, sticky='w')
        ttk.Button(main, text="↺", width=3, command=self.refresh_devices).grid(row=1, column=3)

        ttk.Label(main, text="Wipe Method:").grid(row=2, column=0, sticky='w')
        methods = list(WIPE_METHODS.keys()) + ["Cryptographic Erasure (AES-256)"]
        self.method_combo = ttk.Combobox(main, textvariable=self.selected_method, values=methods, state='readonly', width=60)
        self.method_combo.grid(row=2, column=1, columnspan=2, sticky='w')
        self.method_combo.set(methods[0])
        ttk.Button(main, text='?', width=3, command=self.show_current_method_info).grid(row=2, column=3)

        chunk_frame = ttk.Frame(main)
        chunk_frame.grid(row=3, column=0, columnspan=4, pady=8, sticky='w')
        ttk.Label(chunk_frame, text="Chunk Size (MB):").pack(side='left')
        chunk_combo = ttk.Combobox(chunk_frame, textvariable=self.chunk_size_mb, values=[16,32,64,128,256,512], state='readonly', width=10)
        chunk_combo.pack(side='left', padx=6)
        chunk_combo.set(DEFAULT_CHUNK_SIZE)

        progress_frame = ttk.LabelFrame(main, text='Progress', padding=8)
        progress_frame.grid(row=4, column=0, columnspan=4, pady=12, sticky='ew')
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=600)
        self.progress_bar.grid(row=0, column=0, pady=6)
        self.status_label = ttk.Label(progress_frame, text='Ready')
        self.status_label.grid(row=1, column=0)

        self.start_button = ttk.Button(main, text='START', command=self.start_wipe)
        self.start_button.grid(row=5, column=0, columnspan=4, pady=10)

    def refresh_devices(self):
        self.devices = list_removable_devices()
        display = [f"{d['name']} ({d['size_gb']:.1f} GB)" for d in self.devices]
        self.device_combo['values'] = display
        if display:
            self.device_combo.set(display[0])
        else:
            self.device_combo.set('')

    def update_progress(self, progress, status):
        self.progress_var.set(progress)
        self.status_label['text'] = status
        self.root.update_idletasks()

    def show_current_method_info(self):
        method = self.selected_method.get()
        if method in WIPE_METHODS:
            info = WIPE_METHODS[method]
            messagebox.showinfo('Method Info', f"{method}\n\n{info['description']}")
        else:
            messagebox.showinfo('Method Info', method)

    def start_wipe(self):
        if not self.devices:
            messagebox.showerror('Error', 'No device found')
            return
        idx = self.device_combo.current()
        if idx < 0:
            messagebox.showerror('Error', 'Select a device')
            return
        device_info = self.devices[idx]
        confirm = simpledialog.askstring('Confirm Wipe', f"Type YES to confirm wiping {device_info['name']} ({device_info['size_gb']} GB):")
        if confirm != 'YES':
            return
        if not is_admin():
            messagebox.showerror('Permission', 'You must run this program as Administrator/root')
            return
        # disable controls
        self.start_button.config(state='disabled')
        self.device_combo.config(state='disabled')
        t = threading.Thread(target=self.wipe_thread, args=(device_info,))
        t.daemon = True
        t.start()

    def wipe_thread(self, device_info):
        try:
            ok = self.wipe_device(device_info)
            if ok:
                cert = generate_certificate(device_info, self.selected_method.get(), passes=2 if 'Crypto' in self.selected_method.get() else 3)
                messagebox.showinfo('Success', f'Wipe complete. Certificate saved to: {cert}')
            else:
                messagebox.showerror('Error', 'Wipe failed')
        except Exception as e:
            messagebox.showerror('Error', f'Exception: {e}')
        finally:
            self.start_button.config(state='normal')
            self.device_combo.config(state='readonly')
            self.update_progress(0, 'Ready')

    def wipe_device(self, device_info):
        device_path = device_info['name']
        device_size = device_info['size']
        chunk_size = self.chunk_size_mb.get() * 1024 * 1024
        chunks = max(1, math.ceil(device_size / chunk_size))
        method = self.selected_method.get()
        is_crypto = 'Crypto' in method or 'Cryptographic' in method

        def progress_cb(written, total):
            # Progress per chunk; we can compute a global percent by tracking outer variables
            percent = min(100, (written / total) * 100)
            self.update_progress(percent, f'Writing chunk... {percent:.1f}%')

        try:
            if is_crypto:
                for i in range(chunks):
                    offset = i * chunk_size
                    size_act = min(chunk_size, device_size - offset)
                    self.update_progress((i / chunks) * 100, f'Crypto Erase - chunk {i+1}/{chunks}')
                    if not crypto_write_py(device_path, offset, size_act, progress_cb):
                        return False
                self.update_progress(100, 'Done')
                return True
            else:
                patterns = [0x00, 0xFF, None]
                total_ops = chunks * (len(patterns) + 1)
                ops_done = 0
                for i in range(chunks):
                    offset = i * chunk_size
                    size_act = min(chunk_size, device_size - offset)
                    for p in patterns:
                        patname = 'random' if p is None else ('zeros' if p == 0x00 else 'ones')
                        self.update_progress((ops_done/total_ops)*100, f'Pass {ops_done+1}/{total_ops} ({patname}) chunk {i+1}/{chunks}')
                        if not write_pattern_py(device_path, p, offset, size_act, progress_cb):
                            return False
                        ops_done += 1
                    # verification
                    self.update_progress((ops_done/total_ops)*100, f'Verifying chunk {i+1}/{chunks}')
                    if not verify_region(device_path, offset, size_act, expected_pattern=None):
                        return False
                    ops_done += 1
                self.update_progress(100, 'Done')
                return True
        except Exception as e:
            print(f"[ERROR] wipe_device exception: {e}")
            return False


# ------------------------ Run ------------------------

if __name__ == '__main__':
    root = tk.Tk()
    app = NullNovaGUI(root)
    root.mainloop()
