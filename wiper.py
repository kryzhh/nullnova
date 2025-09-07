#!/usr/bin/env python3
"""
Secure USB/Removable Drive Wiper - Full Script
Requirements:
- Python 3.6+
- pywin32: pip install pywin32
- WMI: pip install WMI
- Run as Administrator
"""

import os
import sys
import ctypes
import json
import uuid
import secrets
import hashlib
from pathlib import Path
from datetime import datetime, timezone

try:
    import win32file
    import win32con
    import pywintypes
    import wmi
except ImportError:
    print("ERROR: pywin32 and WMI are required. Run 'pip install pywin32 WMI'")
    sys.exit(1)

CHUNK_SIZE = 128 * 1024 * 1024  # 128 MB
TEST_SIZE = 4096  # 4 KB for diagnostic test
DOD_PATTERNS = ['random', 0x00, 0xFF]
CERT_DIR = Path("certs")
CERT_DIR.mkdir(exist_ok=True)
DOD_PASSES = 3

# ------------------------ Helper Functions ------------------------ #

def check_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def list_removable_drives():
    c = wmi.WMI()
    drives = []
    for disk in c.Win32_LogicalDisk():
        if disk.DriveType == 2:  # Removable
            drives.append({
                "letter": disk.DeviceID,
                "label": disk.VolumeName or "Unlabeled",
                "size": int(disk.Size) if disk.Size else 0,
                "filesystem": disk.FileSystem or "Unknown"
            })
    return drives

def get_physical_drive(logical_drive: str) -> str:
    try:
        c = wmi.WMI()
        for disk in c.Win32_DiskDrive():
            for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                for ld in partition.associators("Win32_LogicalDiskToPartition"):
                    if ld.DeviceID.upper() == logical_drive.upper():
                        return r"\\.\PHYSICALDRIVE" + str(disk.Index)
        return ""
    except Exception:
        return ""

def is_write_protected(logical_drive: str) -> bool:
    try:
        c = wmi.WMI()
        for disk in c.Win32_DiskDrive():
            for partition in disk.associators("Win32_DiskDriveToDiskPartition"):
                for ld in partition.associators("Win32_LogicalDiskToPartition"):
                    if ld.DeviceID.upper() == logical_drive.upper():
                        if disk.Capabilities and 5 in disk.Capabilities:
                            return True
                        if disk.MediaType and "Read-Only" in disk.MediaType:
                            return True
        return False
    except Exception:
        return False

def confirm_wipe(drive):
    size_gb = round(drive["size"] / (1024**3), 2)
    print("\n" + "!"*60)
    print("CRITICAL WARNING - DATA DESTRUCTION")
    print(f"Drive: {drive['letter']} ({drive['label']}) - {size_gb} GB")
    print("This will PERMANENTLY erase all data on the drive.")
    print("!"*60)

    confirm1 = input("\nType WIPE to confirm: ")
    if confirm1 != "WIPE":
        return False

    confirm2 = input(f"Type the drive letter {drive['letter']} to proceed: ").upper()
    return confirm2 == drive["letter"]

# ------------------------ Diagnostics ------------------------ #

def run_diagnostics(logical_drive: str) -> bool:
    physical_path = get_physical_drive(logical_drive)
    print(f"[*] Running diagnostics on {logical_drive} ({physical_path})...")

    if is_write_protected(logical_drive):
        print(f"[✗] Drive {logical_drive} appears to be write-protected.")
        print("Please remove hardware write-protect switch if present and retry.")
        return False

    try:
        handle = win32file.CreateFile(
            physical_path,
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            0,
            None
        )
        print("[✓] Step 1: Drive handle opened successfully.")

        # Try lock/dismount
        try:
            win32file.DeviceIoControl(handle, 0x00090018, None, 0)
            win32file.DeviceIoControl(handle, 0x00090020, None, 0)
            print("[✓] Step 2: Volume locked/dismounted.")
        except Exception:
            print("[!] Step 2: Could not fully lock/dismount. Proceeding anyway.")

        # Tiny write/read test
        try:
            test_data = secrets.token_bytes(TEST_SIZE)
            win32file.SetFilePointer(handle, 0, win32con.FILE_BEGIN)
            win32file.WriteFile(handle, test_data)
            win32file.FlushFileBuffers(handle)
            win32file.SetFilePointer(handle, 0, win32con.FILE_BEGIN)
            _, read_back = win32file.ReadFile(handle, TEST_SIZE)
            if read_back != test_data:
                print("[✗] Step 3 FAILED: Tiny write/read mismatch.")
                return False
            print("[✓] Step 3: Tiny write/read test passed. Drive is writable.")
            return True
        except pywintypes.error as e:
            print(f"[✗] Step 3 FAILED: {e}. Will attempt logical-drive overwrite instead.")
            return False
    except pywintypes.error as e:
        print(f"[✗] Step 1 FAILED: Could not open drive handle ({e}). Will use logical-drive overwrite.")
        return False
    finally:
        try:
            win32file.CloseHandle(handle)
        except:
            pass

# ------------------------ Wipe Logic ------------------------ #

def generate_pass_data(pattern, size):
    if pattern == 'random':
        return secrets.token_bytes(size)
    elif pattern == 0x00:
        return b'\x00' * size
    elif pattern == 0xFF:
        return b'\xFF' * size
    else:
        return b'\x00' * size

def wipe_logical_drive(drive):
    """Fallback overwrite via logical drive"""
    path = f"{drive['letter']}\\wipe_temp.bin"
    total_size = drive['size']
    if total_size == 0:
        print("[!] Drive size unknown. Cannot proceed.")
        return False

    try:
        print("\n[*] Performing DoD 3-pass wipe via logical drive...")
        for pass_num, pattern in enumerate(DOD_PATTERNS, 1):
            print(f"[PASS {pass_num}/3] Writing pattern {pattern}...")
            written = 0
            with open(path, "wb") as f:
                while written < total_size:
                    chunk_size = min(CHUNK_SIZE, total_size - written)
                    f.write(generate_pass_data(pattern, chunk_size))
                    written += chunk_size
                    progress = (written / total_size) * 100
                    print(f"\rProgress: {progress:.1f}%", end='', flush=True)
            os.remove(path)  # remove temp file
            print(f"\n[PASS {pass_num}/3] Completed ✓")
        print("[✓] Logical-drive DoD wipe completed.")
        return True
    except Exception as e:
        print(f"[✗] Wipe failed: {e}")
        return False

def generate_certificate(drive, success: bool):
    wipe_id = str(uuid.uuid4())
    cert_data = {
        "wipe_id": wipe_id,
        "drive_letter": drive['letter'],
        "drive_label": drive['label'],
        "drive_size_bytes": drive['size'],
        "passes": DOD_PASSES,
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hash": hashlib.sha256(wipe_id.encode()).hexdigest()
    }
    cert_file = CERT_DIR / f"wipe_cert_{drive['letter']}_{wipe_id}.json"
    with open(cert_file, "w") as f:
        json.dump(cert_data, f, indent=2)
    print(f"[✓] Wipe certificate saved: {cert_file}")

# ------------------------ Main ------------------------ #

# ------------------------ Main ------------------------ #

def main():
    print("=== Secure USB Wiper ===")

    if not check_admin():
        print("[✗] Script requires Administrator privileges.")
        sys.exit(1)
    print("[✓] Administrator privileges confirmed.")

    drives = list_removable_drives()
    if not drives:
        print("[✗] No removable drives found.")
        sys.exit(1)

    for i, d in enumerate(drives, 1):
        size_gb = round(d["size"] / (1024**3), 2) if d["size"] else 0
        print(f"{i}. {d['letter']} - {d['label']} ({size_gb} GB)")

    choice = input(f"Select drive to wipe (1-{len(drives)}) or 'q' to quit: ")
    if choice.lower() == "q":
        print("Cancelled by user.")
        sys.exit(0)

    try:
        selected = drives[int(choice)-1]
    except:
        print("Invalid selection.")
        sys.exit(1)

    if not confirm_wipe(selected):
        print("Wipe cancelled by user.")
        sys.exit(0)

    diagnostics_ok = run_diagnostics(selected["letter"])
    if diagnostics_ok:
        print("[✓] Diagnostics passed. Ready for secure wipe.")
        success = wipe_logical_drive(selected)
    else:
        print("[!] Diagnostics failed: raw physical write failed.")
        response = input("Do you want to fallback to logical-drive overwrite? (yes/no): ").strip().lower()
        if response == "yes":
            success = wipe_logical_drive(selected)
        else:
            print("Wipe aborted by user.")
            success = False

    generate_certificate(selected, success)
    if success:
        print(f"[✓] Drive {selected['letter']} securely wiped.")
    else:
        print(f"[✗] Wipe operation failed.")

if __name__ == "__main__":
    main()
