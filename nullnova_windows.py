#!/usr/bin/env python3
##########################
# NullNova (Windows)     #
# US DoD 3-pass wipe     #
##########################

import os
import json
import uuid
import datetime
import time
import math
import win32file
import win32api
import win32con
import wmi
import ctypes
from pathlib import Path
from typing import Dict, List, Any

# Constants
CERTS_DIR = "certs"
CHUNK_SIZE = 1024 * 1024 * 128  # 128MB chunks

# Windows API Constants
FSCTL_LOCK_VOLUME = 0x00090018
FSCTL_DISMOUNT_VOLUME = 0x00090020
IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
FILE_READ_ATTRIBUTES = 0x0080
FILE_WRITE_ATTRIBUTES = 0x0100
INVALID_HANDLE_VALUE = -1

def obtain_lock_force(drive_handle) -> bool:
    """Force obtain a lock on the drive with multiple attempts."""
    for _ in range(20):  # Try 20 times
        try:
            # Try to lock volume
            win32file.DeviceIoControl(
                drive_handle,
                FSCTL_LOCK_VOLUME,
                None,
                None
            )
            return True
        except Exception:
            time.sleep(0.5)  # Wait 500ms between attempts
    return False

def enable_privileges() -> bool:
    """Enable necessary privileges for disk access."""
    try:
        import win32security
        import ntsecuritycon

        # Get the process token
        flags = ntsecuritycon.TOKEN_ADJUST_PRIVILEGES | ntsecuritycon.TOKEN_QUERY
        htoken = win32security.OpenProcessToken(win32api.GetCurrentProcess(), flags)
        
        # Enable SeBackupPrivilege and SeRestorePrivilege
        privileges = [
            (win32security.LookupPrivilegeValue(None, "SeBackupPrivilege"), win32con.SE_PRIVILEGE_ENABLED),
            (win32security.LookupPrivilegeValue(None, "SeRestorePrivilege"), win32con.SE_PRIVILEGE_ENABLED),
            (win32security.LookupPrivilegeValue(None, "SeSecurityPrivilege"), win32con.SE_PRIVILEGE_ENABLED),
            (win32security.LookupPrivilegeValue(None, "SeTakeOwnershipPrivilege"), win32con.SE_PRIVILEGE_ENABLED),
        ]
        
        # Adjust token privileges
        win32security.AdjustTokenPrivileges(htoken, 0, privileges)
        return True
    except Exception as e:
        print(f"Failed to enable privileges: {str(e)}")
        return False

def requires_admin() -> bool:
    """Check if script is running with admin privileges and enable necessary privileges."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            return enable_privileges()
        return False
    except Exception as e:
        print(f"Admin check failed: {str(e)}")
        return False

def get_physical_drives() -> List[Dict[str, Any]]:
    """List physical removable drives using WMI with enhanced error handling."""
    devices = []
    try:
        c = wmi.WMI()
        for drive in c.Win32_DiskDrive():
            if drive.MediaType and ("Removable Media" in drive.MediaType or "USB" in drive.MediaType):
                size = int(drive.Size)
                size_gb = size / (1024**3)
                devices.append({
                    "name": r"\\.\PHYSICALDRIVE" + str(drive.Index),
                    "friendly_name": drive.Caption,
                    "size": size,
                    "size_gb": round(size_gb, 2)
                })
        return devices
    except Exception as e:
        print(f"Error listing physical drives: {str(e)}")
        return []

def get_volume_paths(device_index: int) -> List[str]:
    """Get volume paths for a physical drive."""
    try:
        volumes = []
        drive_path = f"\\\\.\\PHYSICALDRIVE{device_index}"
        # Use CreateFile to get drive handle
        drive_handle = win32file.CreateFile(
            drive_path,
            win32con.GENERIC_READ,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        
        # Get volume name from physical drive
        volumes = win32file.GetVolumePathNamesForVolumeName(drive_path)
        win32file.CloseHandle(drive_handle)
        return volumes
    except:
        return []

def dismount_volume(device_path: str) -> bool:
    """Dismount all volumes on the physical drive with enhanced access rights."""
    try:
        # Extract drive index from physical drive path
        drive_index = int(device_path.rstrip('\\').split('PHYSICALDRIVE')[-1])
        
        # Get all volumes for this drive
        c = wmi.WMI()
        success = True
        
        # Create a Security Descriptor that grants full access
        import win32security
        security = win32security.SECURITY_ATTRIBUTES()
        security.SECURITY_DESCRIPTOR = win32security.SECURITY_DESCRIPTOR()
        
        for partition in c.Win32_DiskPartition():
            if partition.DiskIndex == drive_index:
                for logical_disk in c.Win32_LogicalDisk():
                    if logical_disk.DeviceID:
                        try:
                            # Get volume handle with explicit security attributes and maximum access rights
                            vol_handle = win32file.CreateFileW(
                                f"\\\\.\\{logical_disk.DeviceID[0]}:",
                                win32con.GENERIC_READ | win32con.GENERIC_WRITE,
                                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                                security,
                                win32file.OPEN_EXISTING,
                                win32file.FILE_FLAG_NO_BUFFERING | win32file.FILE_FLAG_WRITE_THROUGH | win32file.FILE_FLAG_SEQUENTIAL_SCAN,
                                None
                            )
                            
                            if vol_handle == INVALID_HANDLE_VALUE:
                                print(f"[!] Failed to get handle for {logical_disk.DeviceID}")
                                success = False
                                continue

                            # Force obtain lock
                            if not obtain_lock_force(vol_handle):
                                print(f"[!] Could not lock {logical_disk.DeviceID}")
                                success = False
                                continue

                            # Dismount volume
                            win32file.DeviceIoControl(
                                vol_handle,
                                FSCTL_DISMOUNT_VOLUME,
                                None,
                                None
                            )
                            
                            print(f"[+] Successfully dismounted {logical_disk.DeviceID}")
                            
                        except Exception as e:
                            print(f"[!] Error dismounting {logical_disk.DeviceID}: {str(e)}")
                            success = False
                            continue
                        finally:
                            try:
                                win32file.CloseHandle(vol_handle)
                            except:
                                pass
        
        return success
                            
    except Exception as e:
        print(f"[!] Error in dismount_volume: {str(e)}")
        return False

def lock_volume(device_path: str) -> bool:
def lock_volume(device_path: str) -> bool:
    """Lock volume for exclusive access with enhanced privileges."""
    try:
        # First dismount all volumes
        if not dismount_volume(device_path):
            return False
            
        # Create security attributes for full access
        security = win32security.SECURITY_ATTRIBUTES()
        security.SECURITY_DESCRIPTOR = win32security.SECURITY_DESCRIPTOR()
        
        # Now try to get exclusive access with enhanced flags
        handle = win32file.CreateFileW(
            device_path,
            win32con.GENERIC_READ | win32con.GENERIC_WRITE | FILE_READ_ATTRIBUTES | FILE_WRITE_ATTRIBUTES,
            0,  # No sharing
            security,
            win32file.OPEN_EXISTING,
            win32file.FILE_FLAG_NO_BUFFERING | win32file.FILE_FLAG_WRITE_THROUGH | win32file.FILE_FLAG_SEQUENTIAL_SCAN,
            None
        )
        
        if handle == INVALID_HANDLE_VALUE:
            print("[!] Failed to get handle for device")
            return False
            
        # Try to force lock
        if not obtain_lock_force(handle):
            print("[!] Failed to lock device")
            win32file.CloseHandle(handle)
            return False
            
        return True
            
    except Exception as e:
        print(f"[!] Error locking volume: {str(e)}")
        return False
        
    except Exception as e:
        print(f"[!] Error locking volume: {e}")
        return False

def write_chunk(device_path: str, pattern: int, offset: int, size: int) -> bool:
    """Write a chunk of data to device at offset."""
    try:
        handle = win32file.CreateFile(
            device_path,
            win32con.GENERIC_READ | win32con.GENERIC_WRITE,
            0,  # No sharing
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        
        try:
            # Move to offset
            win32file.SetFilePointer(handle, offset, 0)
            
            # Generate pattern data
            if pattern == 0x00:  # zeros
                data = b'\x00' * size
            elif pattern == 0xFF:  # ones
                data = b'\xFF' * size
            else:  # random
                data = os.urandom(size)
                
            # Write data
            win32file.WriteFile(handle, data)
            return True
            
        finally:
            win32file.CloseHandle(handle)
            
    except Exception as e:
        print(f"[!] Write error at offset {offset}: {e}")
        return False

def wipe_device_progressive(device_info: Dict[str, Any], passes: int = 3) -> bool:
    """Securely wipe a physical drive with progressive passes."""
    device_path = device_info["name"]
    device_size = device_info["size"]
    
    patterns = [None, 0x00, 0xFF]  # None = random
    chunks = math.ceil(device_size / CHUNK_SIZE)
    
    print(f"[*] Starting progressive {passes}-pass wipe on {device_info['friendly_name']}")
    print(f"[*] Device size: {device_info['size_gb']:.2f} GB")
    print(f"[*] Using {CHUNK_SIZE / (1024*1024):.0f}MB chunks")

    for chunk_idx in range(chunks):
        chunk_offset = chunk_idx * CHUNK_SIZE
        chunk_size = min(CHUNK_SIZE, device_size - chunk_offset)
        
        print(f"\nProcessing chunk {chunk_idx + 1}/{chunks} "
              f"({(chunk_offset/device_size*100):.1f}%)")
        
        for pass_idx, pattern in enumerate(patterns[:passes], 1):
            print(f"Pass {pass_idx}/{passes} - " + 
                  ("Random" if pattern is None else f"Pattern: {pattern:02X}"))
            
            if not write_chunk(device_path, pattern, chunk_offset, chunk_size):
                return False

    print("[✔] Wipe completed successfully")
    return True

def generate_certificate(device_info: Dict[str, Any], passes: int, completed: bool = True) -> str:
    """Generate JSON certificate for completed wipe."""
    os.makedirs(CERTS_DIR, exist_ok=True)
    wipe_id = str(uuid.uuid4())
    
    cert = {
        "wipe_id": wipe_id,
        "device": device_info["friendly_name"],
        "device_path": device_info["name"],
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

def choose_device() -> Dict[str, Any]:
    """Prompt user to select a physical drive."""
    devices = get_physical_drives()
    if not devices:
        print("[!] No removable devices found.")
        return None

    print("\n=== Select a Device to Wipe ===")
    print("[!] WARNING: Make sure to select the correct device!")
    for i, d in enumerate(devices):
        print(f"{i+1}. {d['friendly_name']} - {d['size_gb']} GB")

    try:
        choice = int(input("\nEnter device number (or 0 to cancel): ")) - 1
        if choice == -1:
            return None
        if 0 <= choice < len(devices):
            confirm = input(f"\n[!] WARNING: Are you sure you want to wipe {devices[choice]['friendly_name']}? "
                          f"(Type 'YES' to confirm): ")
            return devices[choice] if confirm == "YES" else None
    except ValueError:
        pass

    print("[!] Invalid choice.")
    return None

def main():
    if not requires_admin():
        print("[!] This script requires administrator privileges!")
        print("[!] Please run as administrator.")
        return

    print("=== NullNova Prototype (Progressive Wipe) - Windows Edition ===")

    devices = get_physical_drives()
    if devices:
        print("\nDetected removable devices:")
        for d in devices:
            print(f"{d['friendly_name']} - {d['size_gb']} GB")
    else:
        print("No removable devices detected.")

    print("\nOptions:")
    print("1. Wipe a device (US DoD 3-pass, progressive)")
    choice = input("Select option: ")

    if choice == "1":
        device_info = choose_device()
        if device_info:
            if lock_volume(device_info["name"]):
                success = wipe_device_progressive(device_info, passes=3)
                generate_certificate(device_info, passes=3, completed=success)
            else:
                print("[!] Failed to lock volume. Make sure it's not in use.")
    else:
        print("[!] Invalid option.")

if __name__ == "__main__":
    main()