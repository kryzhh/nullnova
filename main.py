###################
# NullNova (Linux)#
###################
# If this does not win SIH 2025, I will get convinced nothing can be done of this world.

import os
import json
import hashlib
import datetime
import uuid
import pyudev # Linux only 
# For windows, will use pywin32, lemme finalise the Linux version first.

# Directory for storing JSON Certificates
CERTS_DIR = "certs"

# List devices using pyudev (Linux Only)
def list_removable_devices():
    """List removable storage devices (USB drives, SD cards, etc.) on Linux."""
    context = pyudev.Context() 
    devices = [] # List of dicts with device info
    
    for device in context.list_devices(subsystem='block', DEVTYPE='disk'):
        if device.attributes.asstring('removable') == "1": # It's as string not ass tring :skull: 
            devnode = device.device_node  # e.g. /dev/sdb
            size_attr = device.attributes.get('size')
            size_gb = int(size_attr) * 512 / (1024**3) if size_attr else 0 # Calculate the size of device
            devices.append({
                "name": devnode,
                "size_gb": round(size_gb, 2)
            })
    return devices


def choose_device():
    """Prompt user to select a removable device."""
    devices = list_removable_devices()
    if not devices:
        print("[!] No removable devices found.")
        return None
    
    print("\n=== Select a Device to Wipe ===")
    for i, d in enumerate(devices):
        print(f"{i+1}. {d['name']} - {d['size_gb']} GB")
    
    try:
        choice = int(input("\nEnter device number (or 0 to cancel): ")) - 1
        if choice == -1:
            return None
        if 0 <= choice < len(devices):
            return devices[choice]["name"]
        else:
            print("[!] Invalid choice.")
            return None
    except ValueError:
        print("[!] Invalid input.")
        return None

# Prototype overwrite function (not secure, just for demo)
def overwrite_file(path, passes=3): 
    """Dummy overwrite (for prototype only)."""
    if not os.path.isfile(path):
        print(f"[!] {path} not found")
        return False
    
    size = os.path.getsize(path)
    with open(path, "r+b") as f:
        for p in range(passes):
            f.seek(0)
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
            print(f"Pass {p+1}/{passes} done.")
    return True

# Generate JSON certificate 
# Certifcate is composed of: wipe_id (UUID), device info, method, passes, timestamp, hash
# Hash is SHA256 of wipe_id for integrity
# In real world, would sign this with a private key (That's the final goal)
# For now, just generate the JSON file
def generate_certificate(device, passes):
    """Generate JSON wipe certificate."""
    os.makedirs(CERTS_DIR, exist_ok=True)
    wipe_id = str(uuid.uuid4())
    
    cert = {
        "wipe_id": wipe_id,
        "device": device,
        "method": "US DoD 5220.22-M (3-pass overwrite)",
        "passes": passes,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "hash": hashlib.sha256(wipe_id.encode()).hexdigest()
    }
    
    cert_path = os.path.join(CERTS_DIR, f"{wipe_id}.json") # Unique filename
    with open(cert_path, "w") as f: # Write JSON file
        json.dump(cert, f, indent=4) # Pretty print
    
    print(f"[+] Wipe certificate generated: {cert_path}")
    return cert_path


if __name__ == "__main__":
    print("=== SecureWipe Prototype ===")
    
    # Step 1: Show devices
    devices = list_removable_devices()
    if devices:
        for d in devices:
            print(f"{d['name']} - {d['size_gb']} GB")
    else:
        print("No removable devices detected.")
    
    # Step 2: Ask user what to do
    print("\nOptions:")
    print("1. Wipe a removable device")
    print("2. Run dummy file wipe (test mode)")
    choice = input("Select option: ")
    
    if choice == "1":
        dev = choose_device()
        if dev:
            print(f"\n[!] WARNING: This will ERASE ALL DATA on {dev}")
            confirm = input(f"Type the device name ({dev}) to confirm: ")
            if confirm == dev:
                # For now, just simulate wipe using dummy overwrite function
                print("[*] (Prototype) Not yet wiping raw devices. Using dummy overwrite.")
                test_file = "device_simulation.bin"
                with open(test_file, "wb") as f:
                    f.write(os.urandom(1024 * 1024))  # 1MB
                if overwrite_file(test_file, passes=3):
                    generate_certificate(device=dev, passes=3)
            else:
                print("[!] Wipe cancelled.")
    
    elif choice == "2":
        test_file = "dummy.txt"
        with open(test_file, "wb") as f:
            f.write(os.urandom(1024 * 1024))  # 1MB file
        if overwrite_file(test_file, passes=3):
            generate_certificate(device=test_file, passes=3)
    else:
        print("[!] Invalid option.")


# PS: Remember to enjoy the light before it's gone.
