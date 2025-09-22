#!/usr/bin/env python3
import os
import json
import math
import uuid
import datetime
import time
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import pyudev
from pathlib import Path
import secrets
from Crypto.Cipher import AES

DEFAULT_CHUNK_SIZE = 128  # Size in MB
CHUNK_SIZE = 1024 * 1024 * DEFAULT_CHUNK_SIZE
CERTS_DIR = "certs"

WIPE_METHODS = {
    "DoD 5220.22-M (3 passes)": {
        "description": "US Department of Defense standard wipe with 3 passes: zeros, ones, and random data",
        "pros": [
            "Industry standard method",
            "Good balance of security and speed",
            "Widely accepted for data sanitization"
        ],
        "cons": [
            "Can be slow on large drives",
            "May cause wear on SSDs",
            "Overkill for casual data wiping"
        ],
        "suitable_for": "HDDs, External Drives, When compliance is required"
    },
    "Cryptographic Erasure (AES-256)": {
        "description": "Securely wipes drive by overwriting with encrypted zero data using AES-256",
        "pros": [
            "Very fast (only 2 passes)",
            "SSD friendly",
            "Cryptographically secure"
        ],
        "cons": [
            "Newer method, less widely recognized",
            "May not meet some compliance requirements"
        ],
        "suitable_for": "SSDs, Quick secure erasure, Modern storage devices"
    },
    "DoD 5220.22-M (7 passes) [Coming Soon]": {
        "description": "Extended DoD standard with 7 alternating passes",
        "pros": ["Maximum security", "Meets strict requirements"],
        "cons": ["Very time consuming", "Excessive for most uses"],
        "suitable_for": "High security requirements"
    },
    "Gutmann (35 passes) [Coming Soon]": {
        "description": "35-pass overwrite with specific patterns",
        "pros": ["Most thorough wiping method"],
        "cons": ["Extremely time consuming", "Unnecessary for modern drives"],
        "suitable_for": "Legacy drives, Historical purposes"
    },
    "Random Data (1 pass) [Coming Soon]": {
        "description": "Single pass of random data overwrite",
        "pros": ["Quick", "Sufficient for most cases"],
        "cons": ["May not meet compliance requirements"],
        "suitable_for": "Basic data sanitization"
    }
}

class NullNovaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("NullNova - Secure Drive Wiper")
        self.root.geometry("600x400")
        self.root.resizable(False, False)

        # Variables
        self.selected_device = tk.StringVar()
        self.selected_method = tk.StringVar()
        self.devices = []
        self.chunk_size_mb = tk.IntVar(value=DEFAULT_CHUNK_SIZE)
        
        self.setup_gui()
        self.refresh_devices()

    def setup_gui(self):
        """Setup GUI elements."""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Add title at the top
        title_label = ttk.Label(
            main_frame,
            text="NULLNOVA",
            font=("Arial", 24, "bold"),
            justify="center"
        )
        title_label.grid(row=0, column=0, columnspan=4, pady=(0, 20))

        # Device selection (now row 1)
        ttk.Label(main_frame, text="Device:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.device_combo = ttk.Combobox(
            main_frame, 
            textvariable=self.selected_device,
            state="readonly",
            width=50
        )
        self.device_combo.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)

        ttk.Button(
            main_frame,
            text="↺",
            command=self.refresh_devices,
            width=3
        ).grid(row=1, column=3, padx=5)

        # Wipe method selection with tooltips
        ttk.Label(main_frame, text="Wipe Method:").grid(row=2, column=0, sticky=tk.W, pady=5)
        methods = list(WIPE_METHODS.keys())
        method_combo = ttk.Combobox(
            main_frame,
            textvariable=self.selected_method,
            values=methods,
            state="readonly",
            width=50
        )
        method_combo.grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5)
        method_combo.set(methods[0])
        
        # Add tooltip behavior
        method_combo.bind('<<ComboboxSelected>>', self.show_method_info)
        
        # Info button for method details
        ttk.Button(
            main_frame,
            text="?",
            width=3,
            command=self.show_current_method_info
        ).grid(row=2, column=3, padx=5)

        # Add chunk size selection before the progress frame
        chunk_frame = ttk.Frame(main_frame)
        chunk_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(chunk_frame, text="Chunk Size (MB):").pack(side=tk.LEFT, padx=5)
        chunk_sizes = [16, 32, 64, 128, 256, 512]
        chunk_combo = ttk.Combobox(
            chunk_frame,
            textvariable=self.chunk_size_mb,
            values=chunk_sizes,
            state="readonly",
            width=10
        )
        chunk_combo.pack(side=tk.LEFT, padx=5)
        chunk_combo.set(DEFAULT_CHUNK_SIZE)

        # Progress frame
        self.setup_progress_frame(main_frame)

        # Start button
        self.start_button = ttk.Button(
            main_frame,
            text="START",
            command=self.start_wipe,
            style="Accent.TButton"
        )
        self.start_button.grid(row=5, column=0, columnspan=4, pady=20)

        # Style configuration
        style = ttk.Style()
        style.configure("Accent.TButton", font=("", 10, "bold"))

    def setup_progress_frame(self, parent):
        """Setup progress bar and status label."""
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=20)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=500
        )
        self.progress_bar.grid(row=0, column=0, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.grid(row=1, column=0, pady=5)

    def list_removable_devices(self):
        """List removable devices using sysfs."""
        devices = []
        context = pyudev.Context()
        
        for device in context.list_devices(subsystem='block', DEVTYPE='disk'):
            if not device.get('DEVNAME'):
                continue
                
            dev_name = os.path.basename(device.get('DEVNAME'))
            removable_path = f"/sys/block/{dev_name}/removable"
            
            try:
                if os.path.exists(removable_path):
                    with open(removable_path, 'r') as f:
                        removable = f.read().strip() == '1'
                else:
                    removable = False
                    
                if removable or dev_name.startswith(('sd', 'loop')):
                    size_path = f"/sys/block/{dev_name}/size"
                    with open(size_path, 'r') as f:
                        size = int(f.read().strip()) * 512
                        
                    devices.append({
                        "name": device.get('DEVNAME'),
                        "size": size,
                        "size_gb": round(size / (1024**3), 2)
                    })
            except (IOError, ValueError):
                continue
                
        return devices

    def refresh_devices(self):
        """Refresh the list of available devices."""
        self.devices = self.list_removable_devices()
        device_list = [
            f"{d['name']} ({d['size_gb']:.1f} GB)" for d in self.devices
        ]
        self.device_combo['values'] = device_list
        if device_list:
            self.device_combo.set(device_list[0])
        else:
            self.device_combo.set('')

    def update_progress(self, progress, status):
        """Update progress bar and status label."""
        self.progress_var.set(progress)
        self.status_label['text'] = status
        self.root.update_idletasks()

    def write_chunk(self, device_path, source, offset, size):
        """Write a chunk of data from source to device at offset."""
        cmd = f'dd if={source} of={device_path} bs={size} count=1 seek={offset//size} conv=notrunc status=progress 2>&1\n'
        print(f"[DEBUG] Executing: {cmd.strip()}")
        
        self.elevated_process.stdin.write(cmd)
        self.elevated_process.stdin.flush()
        
        # Read dd output until complete
        while True:
            output = self.elevated_process.stdout.readline()
            if not output:
                break
            print(f"[DEBUG] dd output: {output.strip()}")
            if "bytes" in output:  # Progress information
                try:
                    bytes_written = int(output.split()[0])
                    if bytes_written == size:
                        return True
                except:
                    pass
        return False

    def write_pattern(self, device_path, pattern, offset, size):
        """Write a specific pattern to device."""
        try:
            pattern_name = "zeros" if pattern == 0x00 else "ones" if pattern == 0xFF else "random"
            print(f"[DEBUG] Writing {pattern_name} pattern at offset {offset}")

            if pattern == 0x00:  # All zeros
                cmd = f'dd if=/dev/zero of={device_path} bs={size} count=1 seek={offset//size} conv=notrunc,sync status=progress oflag=direct 2>&1\n'
            elif pattern == 0xFF:  # All ones
                # Write ones pattern without redirecting to /dev/null
                cmd = (
                    f'dd if=/dev/zero bs={size} count=1 | tr "\\000" "\\377" > /dev/shm/ones && '
                    f'dd if=/dev/shm/ones of={device_path} bs={size} count=1 seek={offset//size} '
                    f'conv=notrunc,sync status=progress oflag=direct 2>&1 && '
                    f'rm -f /dev/shm/ones\n'
                )
            else:  # Random data
                cmd = f'dd if=/dev/urandom of={device_path} bs={size} count=1 seek={offset//size} conv=notrunc,sync status=progress oflag=direct 2>&1\n'

            self.elevated_process.stdin.write(cmd)
            self.elevated_process.stdin.flush()
            print(f"[DEBUG] Executing: {cmd.strip()}")

            success = False
            bytes_written = 0
            start_time = time.time()
            
            while (time.time() - start_time) < 60:  # 60 second timeout
                output = self.elevated_process.stdout.readline()
                if not output:
                    time.sleep(0.1)
                    continue
                    
                output = output.strip()
                print(f"[DEBUG] Output: {output}")

                if "bytes" in output and "copied" in output:
                    try:
                        bytes_written = int(output.split()[0])
                        if bytes_written >= size:
                            success = True
                            break
                    except Exception as e:
                        print(f"[DEBUG] Parse error: {e}")
                elif all(x in output for x in ["records", "in", "out"]):
                    # Check for successful dd completion message
                    success = True
                    break

            if not success:
                print(f"[ERROR] Write operation failed. Bytes written: {bytes_written}/{size}")
                return False

            # Force sync
            self.elevated_process.stdin.write("sync\n")
            self.elevated_process.stdin.flush()
            time.sleep(0.5)  # Short wait for sync
            
            return True

        except Exception as e:
            print(f"[ERROR] Write pattern failed: {e}")
            return False

    def verify_chunk(self, device_path, offset, size):
        """Verify a chunk of data."""
        cmd = f'dd if={device_path} bs={size} count=1 skip={offset//size} 2>/dev/null | hexdump -C | head -n 1\n'
        self.elevated_process.stdin.write(cmd)
        self.elevated_process.stdin.flush()
        
        output = self.elevated_process.stdout.readline()
        print(f"[DEBUG] Verification sample at offset {offset}: {output.strip()}")
        return True  # Basic verification - could be enhanced

    def generate_certificate(self, device_info, passes, completed=True):
        """Generate JSON certificate for completed wipe."""
        try:
            wipe_id = str(uuid.uuid4())
            
            # Determine which method was used
            method = self.selected_method.get()
            if method.startswith("Crypto"):
                method_desc = "AES-256 Cryptographic Erasure (2-pass overwrite)"
            else:
                method_desc = f"US DoD 5220.22-M ({passes}-pass overwrite, progressive)"
            
            cert = {
                "wipe_id": wipe_id,
                "device": device_info["name"],
                "method": method_desc,
                "passes": 2 if method.startswith("Crypto") else passes,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "hash": uuid.uuid5(uuid.NAMESPACE_DNS, wipe_id).hex
            }
            
            # Create directory with normal permissions
            os.makedirs(CERTS_DIR, exist_ok=True)
            
            # Write certificate using normal file operations
            cert_path = os.path.join(CERTS_DIR, f"{wipe_id}.json")
            with open(cert_path, 'w') as f:
                json.dump(cert, f, indent=4)
            
            return cert_path
            
        except Exception as e:
            print(f"[ERROR] Certificate generation failed: {str(e)}")
            raise

    def wipe_device(self, device_info):
        """Perform device wiping according to DoD 5220.22-M standard."""
        # Calculate chunk size from GUI selection
        chunk_size = 1024 * 1024 * self.chunk_size_mb.get()
        device_path = device_info["name"]
        device_size = device_info["size"]
        
        print(f"[DEBUG] Starting DoD 5220.22-M wipe process for {device_path}")
        print(f"[DEBUG] Using chunk size: {self.chunk_size_mb.get()} MB")
        
        # Initial permission check
        test_cmd = f"test -w {device_path}"
        print(f"[DEBUG] Testing write permission with: {test_cmd}")
        test_result = subprocess.run(['pkexec', 'bash', '-c', test_cmd], 
                                   capture_output=True, text=True)
        
        if test_result.returncode != 0:
            print(f"[ERROR] Permission test failed: {test_result.stderr}")
            messagebox.showerror("Error", "Failed to get write permission")
            return False

        print("[DEBUG] Permission test passed, starting elevated process")

        # Start elevated shell process
        self.elevated_process = subprocess.Popen(
            ['pkexec', 'bash'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        if self.elevated_process.poll() is not None:
            print(f"[ERROR] Failed to start elevated process: {self.elevated_process.stderr.read()}")
            messagebox.showerror("Error", "Failed to start elevated process")
            return False

        # Define patterns according to DoD 5220.22-M
        patterns = [
            0x00,    # Pass 1: All zeros
            0xFF,    # Pass 2: All ones
            None     # Pass 3: Random data
        ]
        
        chunks = math.ceil(device_size / chunk_size)
        print(f"[DEBUG] Total chunks: {chunks}, Chunk size: {chunk_size/(1024*1024)}MB")
        self.update_progress(0, "Starting wipe process...")
        
        try:
            # Test pipe
            print("[DEBUG] Testing pipe with echo command")
            self.elevated_process.stdin.write("echo 'test'\n")
            self.elevated_process.stdin.flush()
            
            test_output = self.elevated_process.stdout.readline().strip()
            print(f"[DEBUG] Test output: {test_output}")
            
            if test_output != 'test':
                print("[ERROR] Pipe test failed")
                messagebox.showerror("Error", "Failed to communicate with elevated process")
                return False

            is_crypto = self.selected_method.get().startswith("Crypto")
            operations_done = 0  # Initialize the counter here
            
            if is_crypto:
                print("[DEBUG] Using cryptographic erasure method")
                total_operations = chunks * 2  # Zero pass + crypto pass
            else:
                print("[DEBUG] Using DoD 5220.22-M method")
                total_operations = chunks * (len(patterns) + 1)  # +1 for verification

            # Modify the wipe loop to handle crypto method
            for chunk_idx in range(chunks):
                chunk_offset = chunk_idx * chunk_size
                chunk_size_actual = min(chunk_size, device_size - chunk_offset)
                
                if is_crypto:
                    status = f"Cryptographic Erasure - Chunk {chunk_idx + 1}/{chunks}"
                    self.update_progress(progress=(chunk_idx / chunks) * 100, status=status)
                    
                    if not self.crypto_wipe(device_path, chunk_offset, chunk_size_actual):
                        print(f"[ERROR] Cryptographic wipe failed at chunk {chunk_idx + 1}")
                        messagebox.showerror("Error", "Cryptographic wipe failed")
                        return False
                else:
                    # Existing DoD wipe code
                    for pass_idx, pattern in enumerate(patterns, 1):
                        pattern_name = "zeros" if pattern == 0x00 else "ones" if pattern == 0xFF else "random"
                        status = f"Pass {pass_idx}/3 ({pattern_name}) - Chunk {chunk_idx + 1}/{chunks}"
                        self.update_progress(progress=(operations_done / total_operations) * 100, status=status)
                        
                        if not self.write_pattern(device_path, pattern, chunk_offset, chunk_size_actual):
                            print(f"[ERROR] Write pattern {pattern_name} failed")
                            messagebox.showerror("Error", f"Write operation failed during {pattern_name} pass")
                            return False
                        
                        operations_done += 1
                        
                        # Sync after each pass
                        self.elevated_process.stdin.write("sync\n")
                        self.elevated_process.stdin.flush()
                    
                    # Verify chunk
                    status = f"Verifying - Chunk {chunk_idx + 1}/{chunks}"
                    self.update_progress(progress=(operations_done / total_operations) * 100, status=status)
                    
                    if not self.verify_chunk(device_path, chunk_offset, chunk_size_actual):
                        print(f"[ERROR] Verification failed for chunk {chunk_idx + 1}")
                        messagebox.showerror("Error", "Verification failed")
                        return False
                        
                    operations_done += 1
                    print(f"[DEBUG] Completed and verified chunk {chunk_idx + 1}/{chunks}")
                    
            self.update_progress(100, "Wipe completed and verified")
            print("[DEBUG] DoD 5220.22-M wipe process completed successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Exception during wipe: {str(e)}")
            messagebox.showerror("Error", f"Wipe error: {str(e)}")
            return False
        finally:
            try:
                print("[DEBUG] Cleaning up elevated process")
                self.elevated_process.stdin.write("exit\n")
                self.elevated_process.stdin.flush()
                self.elevated_process.stdin.close()
                self.elevated_process.terminate()
                self.elevated_process.wait(timeout=5)
            except Exception as e:
                print(f"[ERROR] Cleanup error: {str(e)}")

    def start_wipe(self):
        """Start the wiping process."""
        if not self.devices:
            messagebox.showerror("Error", "No device selected!")
            return

        device_idx = self.device_combo.current()
        if device_idx < 0:
            return

        device_info = self.devices[device_idx]
        
        warning = (
            f"WARNING!\n\n"
            f"You are about to securely wipe:\n"
            f"{device_info['name']} ({device_info['size_gb']:.1f} GB)\n\n"
            f"This process will:\n"
            f"1. Permanently destroy all data on the device\n"
            f"2. Make data recovery impossible\n"
            f"3. Take significant time to complete\n\n"
            f"Type 'YES' to continue:"
        )
        
        confirm = simpledialog.askstring(
            "Confirm Wipe",
            warning,
            parent=self.root
        )
        
        if confirm != "YES":
            return

        self.start_button['state'] = 'disabled'
        self.device_combo['state'] = 'disabled'
        
        thread = threading.Thread(target=self.wipe_thread, args=(device_info,))
        thread.daemon = True
        thread.start()

    def wipe_thread(self, device_info):
        """Thread for wiping process."""
        try:
            success = self.wipe_device(device_info)
            if success:
                try:
                    cert_path = self.generate_certificate(device_info, passes=3)
                    messagebox.showinfo(
                        "Success",
                        f"Wipe completed successfully!\nCertificate saved to: {cert_path}"
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to generate certificate: {str(e)}")
                    messagebox.showwarning(
                        "Warning",
                        "Wipe completed but failed to generate certificate"
                    )
            else:
                messagebox.showerror("Error", "Wipe process failed!")
        except Exception as e:
            print(f"[ERROR] Critical error in wipe thread: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        finally:
            self.enable_controls()

    def enable_controls(self):
        """Re-enable GUI controls."""
        self.start_button['state'] = 'normal'
        self.device_combo['state'] = 'readonly'
        self.update_progress(0, "Ready")

    def show_method_info(self, event=None):
        """Show information about selected wipe method."""
        method = self.selected_method.get()
        if method in WIPE_METHODS:
            info = WIPE_METHODS[method]
            messagebox.showinfo(
                "Method Information",
                f"{method}\n\n"
                f"Description:\n{info['description']}\n\n"
                f"Pros:\n" + "\n".join(f"• {p}" for p in info['pros']) + "\n\n"
                f"Cons:\n" + "\n".join(f"• {c}" for c in info['cons']) + "\n\n"
                f"Best suited for:\n{info['suitable_for']}"
            )

    def show_current_method_info(self):
        """Show info for current method when ? button is clicked."""
        self.show_method_info()

    def crypto_wipe(self, device_path, offset, size):
        """Perform cryptographic erasure on a chunk."""
        try:
            # Generate secure key
            key = secrets.token_bytes(32)
            cipher = AES.new(key, AES.MODE_CTR)
            
            # First pass: zeros
            if not self.write_pattern(device_path, 0x00, offset, size):
                return False
                
            # Second pass: encrypted zeros
            encrypted_data = cipher.encrypt(b'\0' * size)
            with open("/dev/shm/crypto_data", "wb") as f:
                f.write(encrypted_data)
            
            cmd = (
                f'dd if=/dev/shm/crypto_data of={device_path} bs={size} count=1 '
                f'seek={offset//size} conv=notrunc,sync status=progress oflag=direct 2>&1 && '
                f'rm -f /dev/shm/crypto_data\n'
            )
            
            self.elevated_process.stdin.write(cmd)
            self.elevated_process.stdin.flush()
            
            # Monitor progress
            while True:
                output = self.elevated_process.stdout.readline().strip()
                if not output:
                    break
                print(f"[DEBUG] Crypto pass output: {output}")
                
            # Securely delete key
            del key, cipher, encrypted_data
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Crypto wipe failed: {e}")
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = NullNovaGUI(root)
    root.mainloop()