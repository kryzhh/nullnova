#!/usr/bin/env python3
##########################
# NullNova (Windows)     #
# Secure Drive Wiper GUI #
##########################

import os
import sys
import json
import math
import uuid
import time
import datetime
import secrets
import ctypes
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import concurrent.futures

import win32file
import win32api
import win32con
from Crypto.Cipher import AES

DEFAULT_CHUNK_SIZE = 128  # MB
CHUNK_SIZE = 1024 * 1024 * DEFAULT_CHUNK_SIZE
CERTS_DIR = "certs"

WIPE_METHODS = {
    "DoD 5220.22-M (3 passes)": {
        "description": "US Department of Defense standard wipe with 3 passes: zeros, ones, and random data",
        "pros": ["Industry standard method", "Widely accepted"],
        "cons": ["Slow on large drives", "SSD wear"],
        "suitable_for": "HDDs, compliance use"
    },
    "Cryptographic Erasure (AES-256)": {
        "description": "Securely wipes drive by overwriting with encrypted zero data using AES-256",
        "pros": ["Very fast", "SSD friendly", "Crypto-secure"],
        "cons": ["Newer method", "Not always compliance accepted"],
        "suitable_for": "SSDs, fast erasure"
    }
}


##########################
# Backend (Windows Only) #
##########################

def requires_admin():
    """Check if running with admin rights."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def list_drives():
    """List removable drives in Windows."""
    drives = []
    bitmask = win32api.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bitmask & 1:
            drive = f"{letter}:\\"
            try:
                drive_type = win32file.GetDriveType(drive)
                if drive_type == win32con.DRIVE_REMOVABLE:
                    free_bytes, total_bytes, _ = win32file.GetDiskFreeSpaceEx(drive)
                    drives.append({
                        "name": drive,
                        "path": drive,
                        "size": total_bytes,
                        "size_gb": round(total_bytes / (1024**3), 2)
                    })
            except Exception:
                pass
        bitmask >>= 1
    return drives


def write_pattern(handle, size, pattern=None):
    """Write a pattern to the drive."""
    if pattern is None:  # random
        data = os.urandom(size)
    elif isinstance(pattern, int):
        data = bytes([pattern]) * size
    else:
        data = pattern

    win32file.WriteFile(handle, data)


def crypto_wipe(handle, size):
    """Cryptographic erase using AES-256 encrypted zeros."""
    key = secrets.token_bytes(32)
    cipher = AES.new(key, AES.MODE_CTR)
    zero_data = b'\0' * size
    encrypted_data = cipher.encrypt(zero_data)
    win32file.WriteFile(handle, encrypted_data)
    del key, cipher, encrypted_data, zero_data
    return True


#################
# Tkinter GUI   #
#################

class NullNovaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NullNova - Secure Drive Wiper (Windows)")
        self.root.geometry("600x400")
        self.root.resizable(False, False)

        self.devices = []
        self.selected_device = tk.StringVar()
        self.selected_method = tk.StringVar()
        self.chunk_size_mb = tk.IntVar(value=DEFAULT_CHUNK_SIZE)
        self.stop_flag = False  # For cancellation

        self.setup_gui()
        self.refresh_devices()

    def setup_gui(self):
        main = ttk.Frame(self.root, padding=20)
        main.grid(row=0, column=0, sticky="nsew")

        ttk.Label(main, text="NULLNOVA", font=("Arial", 24, "bold")).grid(row=0, column=0, columnspan=4, pady=10)

        # Device selector
        ttk.Label(main, text="Device:").grid(row=1, column=0, sticky="w")
        self.device_combo = ttk.Combobox(main, textvariable=self.selected_device, width=50, state="readonly")
        self.device_combo.grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Button(main, text="↺", command=self.refresh_devices, width=3).grid(row=1, column=3)

        # Method selector
        ttk.Label(main, text="Wipe Method:").grid(row=2, column=0, sticky="w")
        methods = list(WIPE_METHODS.keys())
        self.method_combo = ttk.Combobox(main, textvariable=self.selected_method, values=methods, state="readonly", width=50)
        self.method_combo.grid(row=2, column=1, columnspan=2, sticky="w")
        self.method_combo.set(methods[0])
        ttk.Button(main, text="?", command=self.show_method_info, width=3).grid(row=2, column=3)

        # Chunk size
        chunk_frame = ttk.Frame(main)
        chunk_frame.grid(row=3, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Label(chunk_frame, text="Chunk Size (MB):").pack(side="left")
        sizes = [16, 32, 64, 128, 256, 512]
        chunk_combo = ttk.Combobox(chunk_frame, textvariable=self.chunk_size_mb, values=sizes, state="readonly", width=10)
        chunk_combo.set(DEFAULT_CHUNK_SIZE)
        chunk_combo.pack(side="left", padx=5)

        # Progress
        progress_frame = ttk.LabelFrame(main, text="Progress", padding=10)
        progress_frame.grid(row=4, column=0, columnspan=4, pady=15, sticky="ew")
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=500)
        self.progress_bar.grid(row=0, column=0, pady=5)
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.grid(row=1, column=0)

        # Start button
        self.start_button = ttk.Button(main, text="START", command=self.start_wipe, style="Accent.TButton")
        self.start_button.grid(row=5, column=0, columnspan=4, pady=20)

        style = ttk.Style()
        style.configure("Accent.TButton", font=("", 10, "bold"))

    def refresh_devices(self):
        self.devices = list_drives()
        items = [f"{d['name']} ({d['size_gb']:.1f} GB)" for d in self.devices]
        self.device_combo["values"] = items
        if items:
            self.device_combo.set(items[0])

    def update_progress(self, progress, status):
        self.progress_var.set(progress)
        self.status_label["text"] = status
        self.root.update_idletasks()

    def start_wipe(self):
        if not self.devices:
            messagebox.showerror("Error", "No drives detected")
            return
        idx = self.device_combo.current()
        if idx < 0:
            return
        device_info = self.devices[idx]

        confirm = simpledialog.askstring(
            "Confirm Wipe",
            f"WARNING: This will destroy all data on {device_info['name']} ({device_info['size_gb']} GB).\n\n"
            f"Type YES to continue:"
        )
        if confirm != "YES":
            return

        self.stop_flag = False
        self.start_button["state"] = "disabled"
        thread = threading.Thread(target=self.wipe_thread, args=(device_info,))
        thread.daemon = True
        thread.start()

    def wipe_thread(self, device_info):
        try:
            method = self.selected_method.get()
            chunk_size = 1024 * 1024 * self.chunk_size_mb.get()
            size = device_info["size"]
            chunks = math.ceil(size / chunk_size)

            if method.startswith("DoD"):
                patterns = [0x00, 0xFF, None]
                passes = 3
            else:
                patterns = ["crypto"]
                passes = 2

            done_chunks = 0
            total_chunks = chunks * passes

            handle = win32file.CreateFile(
                device_info["path"],
                win32con.GENERIC_WRITE,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                0,
                None
            )

            # Multithreaded chunk writes
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for p in range(passes):
                    pattern = patterns[p % len(patterns)]
                    for c in range(chunks):
                        offset = c * chunk_size
                        to_write = min(chunk_size, size - offset)
                        futures.append(executor.submit(self.write_chunk, handle, pattern, offset, to_write))

                for f in concurrent.futures.as_completed(futures):
                    if self.stop_flag:
                        handle.close()
                        self.root.after(0, self.update_progress, 0, "Cancelled")
                        return
                    f.result()  # raise exceptions if any
                    done_chunks += 1
                    progress = (done_chunks / total_chunks) * 100
                    self.root.after(0, self.update_progress, progress, f"Wiping... {done_chunks}/{total_chunks}")

            handle.close()
            cert_path = self.generate_certificate(device_info)
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Wipe completed!\nCertificate: {cert_path}"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Wipe failed: {e}"))
        finally:
            self.root.after(0, self.reset_ui)

    def write_chunk(self, handle, pattern, offset, size):
        win32file.SetFilePointer(handle, offset, win32con.FILE_BEGIN)
        if pattern == "crypto":
            key = secrets.token_bytes(32)
            cipher = AES.new(key, AES.MODE_CTR)
            data = cipher.encrypt(b'\0' * size)
            del key, cipher
        elif pattern is None:
            data = os.urandom(size)
        else:
            data = bytes([pattern]) * size
        win32file.WriteFile(handle, data)

    def reset_ui(self):
        self.start_button["state"] = "normal"
        self.update_progress(0, "Ready")

    def generate_certificate(self, device_info):
        wipe_id = str(uuid.uuid4())
        cert = {
            "id": wipe_id,
            "device": device_info["name"],
            "size_gb": device_info["size_gb"],
            "method": self.selected_method.get(),
            "timestamp": datetime.datetime.now().isoformat()
        }
        os.makedirs(CERTS_DIR, exist_ok=True)
        path = os.path.join(CERTS_DIR, f"{wipe_id}.json")
        with open(path, "w") as f:
            json.dump(cert, f, indent=4)
        return path

    def show_method_info(self):
        method = self.selected_method.get()
        if method in WIPE_METHODS:
            info = WIPE_METHODS[method]
            messagebox.showinfo(
                "Method Info",
                f"{method}\n\n"
                f"{info['description']}\n\n"
                f"Pros:\n" + "\n".join(f"• {p}" for p in info['pros']) +
                "\n\nCons:\n" + "\n".join(f"• {c}" for c in info['cons'])
            )


if __name__ == "__main__":
    if not requires_admin():
        print("Run this script as Administrator.")
        sys.exit(1)

    root = tk.Tk()
    app = NullNovaGUI(root)
    root.mainloop()
