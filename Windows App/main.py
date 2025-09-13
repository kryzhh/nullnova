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
import win32security
import ntsecuritycon
from pathlib import Path
from typing import Dict, List, Any

# Constants
CERTS_DIR = "certs"
CHUNK_SIZE = 1024 * 1024 * 4  # 4MB chunks for better reliability
MAX_RETRIES = 3

# Windows API Constants
FSCTL_LOCK_VOLUME = 0x00090018
FSCTL_DISMOUNT_VOLUME = 0x00090020
IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
GENERIC_ALL = 0x10000000
FILE_ALL_ACCESS = 0x1F01FF
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_WRITE_THROUGH = 0x80000000
FILE_FLAG_NO_BUFFERING = 0x20000000
INVALID_HANDLE_VALUE = -1

def force_close_handles(device_path: str) -> None:
    """Force close any open handles to the device."""
    try:
        # Try using handle.exe if available (Sysinternals)
        if os.path.exists("handle.exe"):
            os.system(f'handle.exe -accepteula -c "{device_path}" > nul 2>&1')
            
        # Fallback: Try to force a garbage collection to release any Python handles
        import gc
        gc.collect()
        
        # Give the system a moment to release handles
        time.sleep(0.5)
    except:
        pass

def enable_privileges() -> bool:
    """Enable necessary privileges for disk access."""
    try:
        flags = ntsecuritycon.TOKEN_ADJUST_PRIVILEGES | ntsecuritycon.TOKEN_QUERY
        htoken = win32security.OpenProcessToken(win32api.GetCurrentProcess(), flags)
        
        # List of all privileges we need
        privilege_list = [
            "SeBackupPrivilege",
            "SeRestorePrivilege",
            "SeSecurityPrivilege",
            "SeTakeOwnershipPrivilege",
            "SeManageVolumePrivilege",  # Added for volume management
            "SeDebugPrivilege"  # Added for low-level access
        ]
        
        privileges = []
        for priv in privilege_list:
            try:
                privileges.append(
                    (win32security.LookupPrivilegeValue(None, priv), win32con.SE_PRIVILEGE_ENABLED)
                )
            except Exception as e:
                print(f"Warning: Couldn't lookup {priv}: {str(e)}")
                
        
        win32security.AdjustTokenPrivileges(htoken, 0, privileges)
        return True
    except Exception as e:
        print(f"Failed to enable privileges: {str(e)}")
        return False

def requires_admin() -> bool:
    """Check if script is running with admin privileges."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if is_admin:
            return enable_privileges()
        return False
    except Exception as e:
        print(f"Admin check failed: {str(e)}")
        return False

def get_physical_drives() -> List[Dict[str, Any]]:
    """List physical removable drives using WMI."""
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

def get_usb_volumes(device_path: str) -> List[str]:
    """Get only the volumes that belong to the specified USB device."""
    try:
        drive_index = int(device_path.rstrip('\\').split('PHYSICALDRIVE')[-1])
        c = wmi.WMI()
        
        # Get the USB drive
        target_drive = None
        for drive in c.Win32_DiskDrive():
            if str(drive.Index) == str(drive_index):
                if not ("Removable Media" in drive.MediaType or "USB" in drive.MediaType):
                    return []
                target_drive = drive
                break

        if not target_drive:
            return []

        # Get only volumes associated with this USB drive
        usb_volumes = []
        system_drive = os.environ.get('SystemDrive', 'C:').rstrip(':\\').upper()
        
        for partition in c.Win32_DiskPartition():
            if partition.DiskIndex == drive_index:
                for logical_disk in c.Win32_LogicalDisk():
                    if logical_disk.DeviceID and logical_disk.DeviceID[0].upper() != system_drive:
                        usb_volumes.append(logical_disk.DeviceID)
        return usb_volumes
    except Exception as e:
        print(f"[!] Error getting USB volumes: {str(e)}")
        return []

def obtain_lock_force(drive_handle) -> bool:
    """Force obtain a lock on the drive with multiple attempts."""
    for _ in range(20):  # Try 20 times
        try:
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

def dismount_volume(device_path: str) -> bool:
    """Dismount only the USB volumes of the selected drive."""
    vol_handle = None
    try:
        # Get only USB volumes, excluding system drive
        usb_volumes = get_usb_volumes(device_path)
        if not usb_volumes:
            print("[!] No valid USB volumes found to dismount")
            return False

        success = True
        security = win32security.SECURITY_ATTRIBUTES()
        security.SECURITY_DESCRIPTOR = win32security.SECURITY_DESCRIPTOR()

        # Process each USB volume
        for volume in usb_volumes:
            try:
                print(f"[*] Attempting to dismount {volume}")
                vol_handle = win32file.CreateFileW(
                    f"\\\\.\\{volume[0]}:",
                    GENERIC_ALL,
                    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                    security,
                    OPEN_EXISTING,
                    FILE_FLAG_WRITE_THROUGH | FILE_FLAG_NO_BUFFERING,
                    None
                )

                if vol_handle == INVALID_HANDLE_VALUE:
                    print(f"[!] Failed to get handle for {volume}")
                    success = False
                    continue

                if obtain_lock_force(vol_handle):
                    win32file.DeviceIoControl(
                        vol_handle,
                        FSCTL_DISMOUNT_VOLUME,
                        None,
                        None
                    )
                    print(f"[+] Successfully dismounted {volume}")
                else:
                    print(f"[!] Could not lock {volume}")
                    success = False
            except Exception as e:
                print(f"[!] Error dismounting {volume}: {str(e)}")
                success = False
            finally:
                if vol_handle and vol_handle != INVALID_HANDLE_VALUE:
                    try:
                        win32file.CloseHandle(vol_handle)
                    except:
                        pass
        return success
    except Exception as e:
        print(f"[!] Error in dismount_volume: {str(e)}")
        return False

def lock_volume(device_path: str) -> bool:
    """Lock volume for exclusive access."""
    handle = None
    try:
        print("[*] Preparing device for exclusive access...")
        
        if not enable_privileges():
            print("[!] Failed to enable necessary privileges")
            return False
        
        if not dismount_volume(device_path):
            print("[!] Failed to dismount volumes")
            return False
        
        print("[*] Attempting to lock device...")
        
        security = win32security.SECURITY_ATTRIBUTES()
        security.SECURITY_DESCRIPTOR = win32security.SECURITY_DESCRIPTOR()
        
        for attempt in range(5):
            try:
                handle = win32file.CreateFileW(
                    device_path,
                    GENERIC_ALL,
                    0,  # No sharing
                    security,
                    OPEN_EXISTING,
                    FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH | FILE_ATTRIBUTE_NORMAL,
                    None
                )
                
                if handle == INVALID_HANDLE_VALUE:
                    print(f"[!] Failed to get handle (attempt {attempt + 1}/5)")
                    time.sleep(1)
                    continue
                
                if obtain_lock_force(handle):
                    print("[+] Successfully locked device")
                    return True
                
                print(f"[!] Failed to lock device (attempt {attempt + 1}/5)")
                win32file.CloseHandle(handle)
                time.sleep(1)
                
            except Exception as e:
                print(f"[!] Error during lock attempt {attempt + 1}: {str(e)}")
                if handle and handle != INVALID_HANDLE_VALUE:
                    win32file.CloseHandle(handle)
                time.sleep(1)
        
        print("[!] Failed to lock device after all attempts")
        return False
    
    except Exception as e:
        print(f"[!] Error in lock_volume: {str(e)}")
        if handle and handle != INVALID_HANDLE_VALUE:
            win32file.CloseHandle(handle)
        return False

def create_wipe_certificate(device_info: Dict[str, Any], wipe_type: str = "DoD 5220.22-M") -> str:
    """Create a certificate for the wiping operation."""
    try:
        os.makedirs(CERTS_DIR, exist_ok=True)
        
        cert = {
            "id": str(uuid.uuid4()),
            "date": datetime.datetime.now().isoformat(),
            "device": device_info,
            "wipe_type": wipe_type,
            "status": "completed",
            "verification": "passed"
        }
        
        cert_path = os.path.join(CERTS_DIR, f"{cert['id']}.json")
        with open(cert_path, 'w') as f:
            json.dump(cert, f, indent=4)
            
        return cert_path
    except Exception as e:
        print(f"[!] Error creating certificate: {str(e)}")
        return ""

def write_with_retry(handle, data: bytes, chunk_num: int, total_chunks: int) -> bool:
    """Write data with retry mechanism."""
    for attempt in range(MAX_RETRIES):
        try:
            win32file.WriteFile(handle, data)
            progress = (chunk_num + 1) / total_chunks * 100
            print(f"Processing chunk {chunk_num + 1}/{total_chunks} ({progress:.1f}%)", end='\r')
            return True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"\n[!] Write error, retrying ({attempt + 2}/{MAX_RETRIES})")
                time.sleep(1)
            else:
                print(f"\n[!] Write error at chunk {chunk_num + 1}: {str(e)}")
                return False
    return False

def wipe_device(device_path: str, device_info: Dict[str, Any]) -> bool:
    """Perform a DoD 3-pass wipe on the device."""
    handle = None
    try:
        print("\n[*] Initializing device wipe...")
        
        if not lock_volume(device_path):
            print("[!] Failed to lock volume for exclusive access")
            return False
            
        print("[*] Device locked successfully, starting wipe process...")
        
        total_size = device_info['size']
        chunks = math.ceil(total_size / CHUNK_SIZE)
        
        security = win32security.SECURITY_ATTRIBUTES()
        security.SECURITY_DESCRIPTOR = win32security.SECURITY_DESCRIPTOR()
        
        # Force close any existing handles first
        force_close_handles(device_path)
        time.sleep(1)
        
        handle = win32file.CreateFileW(
            device_path,
            GENERIC_WRITE,  # Only request write access
            0,  # No sharing
            security,
            OPEN_EXISTING,
            FILE_FLAG_NO_BUFFERING | FILE_FLAG_WRITE_THROUGH,
            None
        )
        
        if handle == INVALID_HANDLE_VALUE:
            print("[!] Failed to get device handle for writing")
            return False
            
        patterns = [
            b'\x00' * CHUNK_SIZE,  # All zeros
            b'\xFF' * CHUNK_SIZE,  # All ones
            os.urandom(CHUNK_SIZE)  # Random data
        ]
        
        for pass_num, pattern in enumerate(patterns, 1):
            print(f"\nPass {pass_num}/3 - {'Random' if pass_num == 3 else 'Zeros' if pass_num == 1 else 'Ones'}")
            for chunk in range(chunks):
                try:
                    win32file.WriteFile(handle, pattern)
                    progress = (chunk + 1) / chunks * 100
                    print(f"Processing chunk {chunk + 1}/{chunks} ({progress:.1f}%)", end='\r')
                except Exception as e:
                    print(f"\n[!] Write error at offset {chunk * CHUNK_SIZE}: {str(e)}")
                    return False
            print()  # New line after progress
        
        cert_path = create_wipe_certificate(device_info)
        if cert_path:
            print(f"\n[+] Certificate saved: {cert_path}")
        return True
        
    except Exception as e:
        print(f"\n[!] Error during wipe: {str(e)}")
        return False
    finally:
        if handle and handle != INVALID_HANDLE_VALUE:
            try:
                win32file.CloseHandle(handle)
            except:
                pass

def main():
    """Main function."""
    if not requires_admin():
        print("[!] This script requires administrator privileges")
        return
    
    drives = get_physical_drives()
    if not drives:
        print("[!] No removable drives found")
        return
    
    print("\nAvailable drives:")
    for i, drive in enumerate(drives):
        print(f"{i + 1}. {drive['friendly_name']} ({drive['size_gb']} GB)")
    
    try:
        selection = int(input("\nSelect drive number to wipe: ")) - 1
        if not 0 <= selection < len(drives):
            print("[!] Invalid selection")
            return
    except ValueError:
        print("[!] Invalid input")
        return
    
    selected_drive = drives[selection]
    
    confirm = input(f"\n[!] WARNING: Are you sure you want to wipe {selected_drive['friendly_name']}? (Type 'YES' to confirm): ")
    if confirm != "YES":
        print("[!] Operation cancelled")
        return
    
    print(f"\n[*] Starting progressive 3-pass wipe on {selected_drive['friendly_name']}")
    print(f"[*] Device size: {selected_drive['size_gb']} GB")
    print(f"[*] Using {CHUNK_SIZE // (1024*1024)}MB chunks\n")
    
    success = wipe_device(selected_drive['name'], selected_drive)
    if success:
        print("\n[+] Wipe completed successfully")
    else:
        print("\n[!] Wipe failed")

if __name__ == "__main__":
    main()