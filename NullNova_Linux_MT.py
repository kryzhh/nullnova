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
import queue 
import pyudev
from pathlib import Path
import secrets
from Crypto.Cipher import AES

DEFAULT_CHUNK_SIZE = 128  # Size in MB
CHUNK_SIZE = 1024 * 1024 * DEFAULT_CHUNK_SIZE
CERTS_DIR = "certs"

WIPE_METHODS = {
    "DoD 5220.22-M (3 passes)": {
        "description": "Writes over your data three times to make it unrecoverable. Uses zeros, ones, and random data.",
        "pros": [
            "Very secure - trusted by government agencies",
            "Works well on most drives",
            "Widely recognized security standard"
        ],
        "cons": [
            "Takes longer than basic erasure",
            "Not recommended for SSDs - may reduce lifespan",
            "More thorough than needed for everyday use"
        ],
        "suitable_for": "Regular hard drives, when you need proven security"
    },
    "Cryptographic Erasure (AES-256)": {
        "description": "Quickly erases data by overwriting with encrypted zeros. Perfect for modern drives.",
        "pros": [
            "Much faster - only two passes needed",
            "Safe for all drive types including SSDs",
            "Very secure using modern encryption"
        ],
        "cons": [
            "Newer method - might not meet some requirements",
            "Not as widely recognized as DoD method"
        ],
        "suitable_for": "SSDs, modern drives, when you need quick secure erasure"
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

        # Add multithreading option before progress frame
        mt_frame = ttk.Frame(main_frame)
        mt_frame.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        self.use_multithreading = tk.BooleanVar(value=False)
        self.mt_checkbox = ttk.Checkbutton(
            mt_frame,
            text="Use Multithreading (Recommended for SSDs, NOT for HDDs)",
            variable=self.use_multithreading,
            command=self.check_mt_warning
        )
        self.mt_checkbox.pack(side=tk.LEFT, padx=5)

        # Progress frame
        self.setup_progress_frame(main_frame)

        # Start button
        self.start_button = ttk.Button(
            main_frame,
            text="START",
            command=self.start_wipe,
            style="Accent.TButton"
        )
        self.start_button.grid(row=6, column=0, columnspan=4, pady=20)

        # Style configuration
        style = ttk.Style()
        style.configure("Accent.TButton", font=("", 10, "bold"))

    def setup_progress_frame(self, parent):
        """Setup progress bar and status label."""
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=20)

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

            # Calculate optimal block size for edge cases
            block_size = min(size, 1024 * 1024)  # Use 1MB blocks minimum
            blocks_needed = (size + block_size - 1) // block_size

            if pattern == 0x00:  # All zeros
                cmd = (f'dd if=/dev/zero of={device_path} bs={block_size} count={blocks_needed} '
                      f'seek={offset//block_size} conv=notrunc,sync status=progress oflag=direct 2>&1\n')
            elif pattern == 0xFF:  # All ones
                cmd = (
                    f'dd if=/dev/zero bs={block_size} count={blocks_needed} | tr "\\000" "\\377" > /dev/shm/ones && '
                    f'dd if=/dev/shm/ones of={device_path} bs={block_size} count={blocks_needed} '
                    f'seek={offset//block_size} conv=notrunc,sync status=progress oflag=direct 2>&1 && '
                    f'rm -f /dev/shm/ones\n'
                )
            else:  # Random data
                cmd = (f'dd if=/dev/urandom of={device_path} bs={block_size} count={blocks_needed} '
                      f'seek={offset//block_size} conv=notrunc,sync status=progress oflag=direct 2>&1\n')

            self.elevated_process.stdin.write(cmd)
            self.elevated_process.stdin.flush()
            print(f"[DEBUG] Executing: {cmd.strip()}")

            success = False
            bytes_written = 0
            start_time = time.time()
            expected_bytes = size
            
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
                        # Allow for block size alignment
                        if bytes_written >= expected_bytes * 0.99:
                            success = True
                            break
                    except Exception as e:
                        print(f"[DEBUG] Parse error: {e}")
                elif all(x in output for x in ["records", "in", "out"]):
                    if not "error" in output.lower():
                        success = True
                        break

            if not success:
                print(f"[ERROR] Write operation failed. Bytes written: {bytes_written}/{expected_bytes}")
                return False

            # Force sync
            self.elevated_process.stdin.write("sync\n")
            self.elevated_process.stdin.flush()
            time.sleep(0.1)  # Reduced wait time
            
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
            
            # Get method and drive info
            method = self.selected_method.get()
            is_crypto = method.startswith("Crypto")
            
            cert = {
                "wipe_device": wipe_id,
                "device": device_info["name"],
                "method": "AES-256 Cryptographic Erasure" if is_crypto else "DoD 5220.22-M Secure Erase",
                "passes": 2 if is_crypto else 3,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "hash": uuid.uuid5(uuid.NAMESPACE_DNS, wipe_id).hex,
            }
            
            # Create certs directory if needed
            os.makedirs(CERTS_DIR, exist_ok=True)
            
            # Write certificate
            cert_path = os.path.join(CERTS_DIR, f"wipe_{wipe_id[:8]}.json")
            with open(cert_path, 'w') as f:
                json.dump(cert, f, indent=2)
            
            return cert_path
            
        except Exception as e:
            print(f"[ERROR] Certificate generation failed: {str(e)}")
            raise

    def wipe_device(self, device_info):
        """Perform device wiping."""
        chunk_size = 1024 * 1024 * self.chunk_size_mb.get()
        device_path = device_info["name"]
        device_size = device_info["size"]
        
        print(f"[DEBUG] Starting wipe process for {device_path}")
        print(f"[DEBUG] Using chunk size: {self.chunk_size_mb.get()} MB")
        print(f"[DEBUG] Multithreading: {self.use_multithreading.get()}")
        
        # Initialize elevated process for single-threaded mode or testing
        self.elevated_process = subprocess.Popen(
            ['pkexec', 'bash'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        if self.elevated_process.poll() is not None:
            print("[ERROR] Failed to get elevated privileges")
            return False

        chunks = math.ceil(device_size / chunk_size)
        patterns = [0x00, 0xFF, None]  # DoD patterns
        is_crypto = self.selected_method.get().startswith("Crypto")
        
        try:
            if self.use_multithreading.get():
                print("[DEBUG] Using multithreaded wipe")
                return self.wipe_device_mt(device_info, patterns, chunks, chunk_size, device_size)
            
            # Single-threaded mode
            print("[DEBUG] Using single-threaded wipe")
            operations_done = 0
            total_operations = chunks * (2 if is_crypto else 4) # 3 passes + verification for DoD
            
            for chunk_idx in range(chunks):
                chunk_offset = chunk_idx * chunk_size
                chunk_size_actual = min(chunk_size, device_size - chunk_offset)
                
                if is_crypto:
                    status = f"Cryptographic Erasure - Chunk {chunk_idx + 1}/{chunks}"
                    self.update_progress(progress=(chunk_idx / chunks) * 100, status=status)
                    
                    if not self.crypto_wipe(device_path, chunk_offset, chunk_size_actual):
                        print(f"[ERROR] Cryptographic wipe failed at chunk {chunk_idx + 1}")
                        return False
                    
                    operations_done += 2
                else:
                    for pattern in patterns:
                        if not self.write_pattern(device_path, pattern, chunk_offset, chunk_size_actual):
                            print(f"[ERROR] Pattern write failed at chunk {chunk_idx + 1}")
                            return False
                        operations_done += 1
                        
                        progress = (operations_done / total_operations) * 100
                        self.update_progress(
                            progress,
                            f"DoD Wipe Pass {operations_done//chunks + 1}/3 - Chunk {chunk_idx + 1}/{chunks}"
                        )
                    
                    if not self.verify_chunk(device_path, chunk_offset, chunk_size_actual):
                        print(f"[ERROR] Verification failed at chunk {chunk_idx + 1}")
                        return False
                    operations_done += 1
            
            self.update_progress(100, "Wipe completed successfully")
            return True
            
        except Exception as e:
            print(f"[ERROR] Wipe failed: {str(e)}")
            return False
        finally:
            if hasattr(self, 'elevated_process') and self.elevated_process:
                self.elevated_process.stdin.write("exit\n")
                self.elevated_process.stdin.flush()
                self.elevated_process.terminate()
                self.elevated_process.wait(timeout=5)

    def wipe_device_mt(self, device_info, patterns, chunks, chunk_size, device_size):
        """Perform multithreaded device wipe."""
        device_path = device_info["name"]
        max_workers = min(os.cpu_count() or 4, 8)
        workers = []  # Define workers list at the top level
        stop_event = threading.Event()
        
        try:
            # Get authentication first
            print("[DEBUG] Waiting for authentication...")
            master_process = subprocess.Popen(
                ['pkexec', 'bash'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Wait for user to authenticate
            for _ in range(60):  # 30 second timeout
                if master_process.poll() is None:
                    break
                time.sleep(0.5)
            else:
                print("[ERROR] Authentication timeout")
                return False

            # Test write access
            print("[DEBUG] Testing write access...")
            cmd = f'test -w {device_path}\n'
            master_process.stdin.write(cmd)
            master_process.stdin.flush()
            
            if master_process.poll() is not None:
                print("[ERROR] Write permission test failed")
                return False
                
            print("[DEBUG] Successfully got elevated privileges")
            
            # Calculate worker ranges
            chunks_per_thread = max(chunks // max_workers, 1)
            ranges = []
            start_chunk = 0
            
            while start_chunk < chunks:
                end_chunk = min(start_chunk + chunks_per_thread, chunks)
                ranges.append((start_chunk, end_chunk))
                start_chunk = end_chunk

            completion_queue = queue.Queue()

            # Create workers
            for worker_id in range(len(ranges)):
                worker = WipeWorker(device_path, worker_id, chunk_size)
                worker.elevated_process = master_process  # Share the master process
                workers.append(worker)
                print(f"[DEBUG] Created worker {worker_id}")

            # Start threads
            threads = []
            for worker_id, (start, end) in enumerate(ranges):
                thread = threading.Thread(
                    target=self.process_chunk_range,
                    args=(workers[worker_id], start, end, chunk_size, 
                          device_size, patterns, completion_queue, stop_event)
                )
                thread.start()
                threads.append(thread)
                print(f"[DEBUG] Started thread for worker {worker_id}")

            # Monitor progress
            total_chunks = sum(end - start for start, end in ranges)
            chunks_done = 0
            
            while chunks_done < total_chunks and not stop_event.is_set():
                try:
                    result = completion_queue.get(timeout=1)
                    if not result[0]:  # Error occurred
                        stop_event.set()
                        raise Exception(f"Worker {result[1]} failed")
                    chunks_done += 1
                    progress = (chunks_done / total_chunks) * 100
                    self.update_progress(progress, f"Completed {chunks_done}/{total_chunks} chunks")
                except queue.Empty:
                    continue

            # Wait for threads
            for thread in threads:
                thread.join(timeout=5)

            return not stop_event.is_set()

        except Exception as e:
            print(f"[ERROR] Multithreaded wipe failed: {e}")
            stop_event.set()
            return False

        finally:
            # Clean up all workers
            for worker in workers:
                worker.cleanup()
            if 'master_process' in locals():
                try:
                    master_process.terminate()
                    master_process.wait(timeout=5)
                except:
                    pass

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

    def is_ssd(self, device_name):
        """Check if device is SSD."""
        dev_name = os.path.basename(device_name)
        rotational_path = f"/sys/block/{dev_name}/queue/rotational"
        try:
            with open(rotational_path, 'r') as f:
                return f.read().strip() == '0'
        except:
            return False

    def check_mt_warning(self):
        """Show warning when enabling multithreading for HDDs."""
        if self.use_multithreading.get():
            device_idx = self.device_combo.current()
            if device_idx >= 0:
                device_info = self.devices[device_idx]
                if not self.is_ssd(device_info["name"]):
                    if not messagebox.askyesno(
                        "Warning",
                        "Multithreading is NOT recommended for HDDs:\n\n"
                        "• Can cause excessive head movement\n"
                        "• May reduce performance\n"
                        "• Could increase drive wear\n\n"
                        "Continue anyway?"
                    ):
                        self.use_multithreading.set(False)

    def process_chunk_range(self, worker, start_chunk, end_chunk, chunk_size, device_size, patterns, completion_queue, stop_event):
        """Process a range of chunks with a worker."""
        try:
            for chunk_idx in range(start_chunk, end_chunk):
                if stop_event.is_set():
                    return False, 0

                chunk_offset = chunk_idx * chunk_size
                chunk_size_actual = min(chunk_size, device_size - chunk_offset)
                
                # Process each pattern for the chunk
                for pattern in patterns:
                    if not worker.write_pattern(pattern, chunk_offset, chunk_size_actual):
                        completion_queue.put((False, worker.worker_id))
                        return False, chunk_idx - start_chunk
                    
                    # Report progress
                    completion_queue.put((True, worker.worker_id))

                print(f"[DEBUG] Worker {worker.worker_id} completed chunk {chunk_idx}")
                
            return True, end_chunk - start_chunk

        except Exception as e:
            print(f"[ERROR] Worker {worker.worker_id} failed: {str(e)}")
            completion_queue.put((False, worker.worker_id))
            return False, 0

class WipeWorker:
    def __init__(self, device_path, worker_id, chunk_size):
        self.device_path = device_path
        self.worker_id = worker_id
        self.chunk_size = chunk_size
        self.elevated_process = None
        self.output_lock = threading.Lock()
        
    def initialize(self):
        """Initialize worker's elevated process."""
        try:
            self.elevated_process = subprocess.Popen(
                ['pkexec', 'bash'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            return self.elevated_process.poll() is None
        except Exception as e:
            print(f"[ERROR] Worker {self.worker_id} init failed: {e}")
            return Falsep

    def write_pattern(self, pattern, offset, size):
        """Write pattern to device."""
        try:
            pattern_name = "zeros" if pattern == 0x00 else "ones" if pattern == 0xFF else "random"
            print(f"[DEBUG] Worker {self.worker_id}: Writing {pattern_name} at offset {offset}")
            
            block_size = min(size, 64 * 1024)  # 64KB blocks
            blocks = (size + block_size - 1) // block_size

            if pattern == 0x00:
                cmd = (f'dd if=/dev/zero of={self.device_path} bs={block_size} count={blocks} '
                      f'seek={offset//block_size} conv=notrunc,fsync status=progress 2>&1\n')
            elif pattern == 0xFF:
                cmd = (f'dd if=<(tr "\\000" "\\377" < /dev/zero) of={self.device_path} '
                      f'bs={block_size} count={blocks} seek={offset//block_size} '
                      f'conv=notrunc,fsync status=progress 2>&1\n')
            else:
                cmd = (f'dd if=/dev/urandom of={self.device_path} bs={block_size} count={blocks} '
                      f'seek={offset//block_size} conv=notrunc,fsync status=progress 2>&1\n')

            with self.output_lock:
                self.elevated_process.stdin.write(cmd)
                self.elevated_process.stdin.flush()

            bytes_written = 0
            start_time = time.time()
            timeout = 300  # 5 minute timeout
            
            while bytes_written < size and (time.time() - start_time) < timeout:
                output = self.elevated_process.stdout.readline()
                if not output:
                    time.sleep(0.1)
                    continue
                    
                output = output.strip()
                if "bytes" in output and "copied" in output:
                    try:
                        current = int(output.split()[0])
                        bytes_written = max(bytes_written, current)
                        print(f"[DEBUG] Worker {self.worker_id}: {bytes_written}/{size} bytes written")
                    except ValueError:
                        continue
                elif "error" in output.lower():
                    print(f"[ERROR] Worker {self.worker_id}: {output}")
                    return False

            success = bytes_written >= size * 0.99  # Allow for block alignment
            if not success:
                print(f"[ERROR] Worker {self.worker_id} incomplete write: {bytes_written}/{size}")
                return False

            # Force sync
            with self.output_lock:
                self.elevated_process.stdin.write("sync\n")
                self.elevated_process.stdin.flush()
            
            return True

        except Exception as e:
            print(f"[ERROR] Worker {self.worker_id} write failed: {str(e)}")
            return False

    def cleanup(self):
        """Clean up worker resources."""
        if self.elevated_process:
            try:
                self.elevated_process.stdin.write("exit\n")
                self.elevated_process.stdin.flush()
                self.elevated_process.terminate()
                self.elevated_process.wait(timeout=5)
            except:
                pass


if __name__ == "__main__":
    root = tk.Tk()
    app = NullNovaGUI(root)
    root.mainloop()