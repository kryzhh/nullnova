#!/usr/bin/env python3
##########################
# NullNova (Linux)       #
# US DoD 3-pass wipe     #
##########################

import os
import stat
import json
import datetime
import uuid
import subprocess
import pyudev
import math

CERTS_DIR = "certs"
CHUNK_SIZE = 1024 * 1024 * 128  # 128MB chunks

def is_block_device(path):
    """Check if the path is a block device."""
    try:
        return stat.S_ISBLK(os.stat(path).st_mode)
    except Exception:
        return False

def get_device_size(device_path):
    """Get device size in bytes."""
    try:
        with open(device_path, 'rb') as f:
            return os.lseek(f.fileno(), 0, os.SEEK_END)
    except Exception as e:
        print(f"[!] Error getting device size: {e}")
        return 0

def list_removable_devices():
    """List removable block devices (USB drives, SD cards, etc.) and loop devices for testing."""
    context = pyudev.Context()
    devices = []

    for device in context.list_devices(subsystem='block', DEVTYPE='disk'):
        devnode = device.device_node
        if not devnode or not is_block_device(devnode):
            continue

        removable = device.attributes.asstring('removable') if device.attributes.get('removable') else "0"
        if removable == "1" or devnode.startswith("/dev/loop") or devnode.startswith("/dev/sd"):
            size = get_device_size(devnode)
            size_gb = size / (1024**3)
            devices.append({
                "name": devnode,
                "size": size,
                "size_gb": round(size_gb, 2)
            })

    return devices

def choose_device():
    """Prompt user to select a block device."""
    devices = list_removable_devices()
    if not devices:
        print("[!] No devices found.")
        return None

    print("\n=== Select a Device to Wipe ===")
    for i, d in enumerate(devices):
        print(f"{i+1}. {d['name']} - {d['size_gb']} GB")

    try:
        choice = int(input("\nEnter device number (or 0 to cancel): ")) - 1
        if choice == -1:
            return None
        if 0 <= choice < len(devices):
            return devices[choice]
    except ValueError:
        pass

    print("[!] Invalid choice.")
    return None

def write_chunk(device_path, source, offset, size):
    """Write a chunk of data from source to device at offset."""
    try:
        with open(source, 'rb') as src, open(device_path, 'rb+') as dst:
            dst.seek(offset)
            data = src.read(size)
            dst.write(data)
        return True
    except Exception as e:
        print(f"[!] Write error at offset {offset}: {e}")
        return False

def wipe_device_progressive(device_info, passes=3):
    """Securely wipe a block device with progressive passes."""
    device_path = device_info["name"]
    device_size = device_info["size"]
    
    # Unmount device if mounted
    subprocess.run(["umount", device_path], stderr=subprocess.DEVNULL)

    sources = ["/dev/urandom", "/dev/zero", "/dev/urandom"]
    chunks = math.ceil(device_size / CHUNK_SIZE)
    
    print(f"[*] Starting progressive {passes}-pass wipe on {device_path}")
    print(f"[*] Device size: {device_info['size_gb']:.2f} GB")
    print(f"[*] Using {CHUNK_SIZE / (1024*1024):.0f}MB chunks")

    for chunk_idx in range(chunks):
        chunk_offset = chunk_idx * CHUNK_SIZE
        chunk_size = min(CHUNK_SIZE, device_size - chunk_offset)
        
        print(f"\nProcessing chunk {chunk_idx + 1}/{chunks} "
              f"({(chunk_offset/device_size*100):.1f}%)")
        
        # Apply all passes to current chunk before moving to next
        for pass_idx, src in enumerate(sources[:passes], 1):
            print(f"Pass {pass_idx}/{passes} using {src}...")
            if not write_chunk(device_path, src, chunk_offset, chunk_size):
                print(f"[!] Failed during pass {pass_idx} at chunk {chunk_idx + 1}")
                return False
            
        # Sync after each chunk to ensure writes are committed
        os.sync()

    print("[✔] Wipe completed successfully")
    return True

def generate_certificate(device_info, passes, completed=True):
    """Generate JSON certificate for completed wipe."""
    os.makedirs(CERTS_DIR, exist_ok=True)
    wipe_id = str(uuid.uuid4())
    
    cert = {
        "wipe_id": wipe_id,
        "device": device_info["name"],
        "device_size": device_info["size_gb"],
        "method": f"US DoD 5220.22-M ({passes}-pass overwrite, progressive)",
        "passes": passes,
        "completed": completed,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hash": uuid.uuid5(uuid.NAMESPACE_DNS, wipe_id).hex
    }

    cert_path = os.path.join(CERTS_DIR, f"{wipe_id}.json")
    with open(cert_path, "w") as f:
        json.dump(cert, f, indent=4)

    print(f"[+] Certificate saved: {cert_path}")
    return cert_path

if __name__ == "__main__":
    print("=== NullNova Prototype (Progressive Wipe) ===")

    devices = list_removable_devices()
    if devices:
        print("\nDetected devices:")
        for d in devices:
            print(f"{d['name']} - {d['size_gb']} GB")
    else:
        print("No devices detected.")

    print("\nOptions:")
    print("1. Wipe a device (US DoD 3-pass, progressive)")
    choice = input("Select option: ")

    if choice == "1":
        device_info = choose_device()
        if device_info:
            success = wipe_device_progressive(device_info, passes=3)
            generate_certificate(device_info, passes=3, completed=success)
    else:
        print("[!] Invalid option.")