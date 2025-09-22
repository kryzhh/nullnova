#!/usr/bin/env python3
# ...existing imports...
import concurrent.futures
from queue import Queue
from threading import Lock

# Add after WIPE_METHODS dictionary
MAX_WORKERS = os.cpu_count() or 4  # Default to 4 if CPU count unavailable
PROGRESS_LOCK = Lock()  # For thread-safe progress updates

class NullNovaGUI:
    # ...existing __init__ and other methods...

    def is_ssd(self, device_name):
        """Check if device is an SSD."""
        dev_name = os.path.basename(device_name)
        rotational_path = f"/sys/block/{dev_name}/queue/rotational"
        
        try:
            with open(rotational_path, 'r') as f:
                return f.read().strip() == '0'  # 0 for SSD, 1 for HDD
        except:
            return False

    def setup_gui(self):
        # ...existing GUI setup code...

        # Add multithreading option after chunk size selection
        mt_frame = ttk.Frame(main_frame)
        mt_frame.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)

        self.use_multithreading = tk.BooleanVar(value=False)
        self.mt_checkbox = ttk.Checkbutton(
            mt_frame,
            text="Use Multithreading (Recommended for SSDs/USB, NOT for HDDs)",
            variable=self.use_multithreading,
            command=self.check_mt_warning
        )
        self.mt_checkbox.pack(side=tk.LEFT, padx=5)

        # Move progress frame to row 5
        self.setup_progress_frame(main_frame)
        
        # Move start button to row 6
        self.start_button.grid(row=6, column=0, columnspan=4, pady=20)

    def check_mt_warning(self):
        """Show warning when enabling multithreading."""
        if self.use_multithreading.get():
            device_idx = self.device_combo.current()
            if device_idx >= 0:
                device_info = self.devices[device_idx]
                if not self.is_ssd(device_info["name"]):
                    if not messagebox.askyesno(
                        "Warning",
                        "Multithreading is NOT recommended for HDDs as it can cause "
                        "excessive head movement and slower performance.\n\n"
                        "Are you sure you want to enable it?"
                    ):
                        self.use_multithreading.set(False)

    def wipe_chunk_mt(self, device_path, chunk_idx, chunk_offset, chunk_size, 
                     device_size, patterns, total_chunks):
        """Thread-safe chunk wiping."""
        try:
            chunk_size_actual = min(chunk_size, device_size - chunk_offset)
            
            for pass_idx, pattern in enumerate(patterns, 1):
                pattern_name = "zeros" if pattern == 0x00 else "ones" if pattern == 0xFF else "random"
                with PROGRESS_LOCK:
                    self.update_progress(
                        -1,  # Special value to indicate thread progress
                        f"Pass {pass_idx}/3 ({pattern_name}) - Chunk {chunk_idx + 1}/{total_chunks}"
                    )
                
                if not self.write_pattern(device_path, pattern, chunk_offset, chunk_size_actual):
                    return False
                
                # Sync after each pass
                self.elevated_process.stdin.write("sync\n")
                self.elevated_process.stdin.flush()
            
            # Verify chunk
            if not self.verify_chunk(device_path, chunk_offset, chunk_size_actual):
                return False
                
            print(f"[DEBUG] Thread completed chunk {chunk_idx + 1}/{total_chunks}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Thread failed for chunk {chunk_idx}: {str(e)}")
            return False

    def wipe_device(self, device_info):
        # ...existing setup code until patterns definition...

        try:
            # ...existing pipe test code...

            is_crypto = self.selected_method.get().startswith("Crypto")
            
            if is_crypto:
                return self.crypto_wipe_mt(device_info, chunks, chunk_size, device_size)
            
            if self.use_multithreading.get():
                return self.dod_wipe_mt(device_info, patterns, chunks, chunk_size, device_size)
            else:
                return self.dod_wipe_sequential(device_info, patterns, chunks, chunk_size, device_size)
                
        except Exception as e:
            print(f"[ERROR] Exception during wipe: {str(e)}")
            return False

    def dod_wipe_mt(self, device_info, patterns, chunks, chunk_size, device_size):
        """Perform DoD wipe with multithreading."""
        device_path = device_info["name"]
        operations_done = 0
        total_operations = chunks * (len(patterns) + 1)
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {}
                
                # Submit chunks in batches to control memory usage
                batch_size = min(MAX_WORKERS * 2, chunks)
                for start_idx in range(0, chunks, batch_size):
                    end_idx = min(start_idx + batch_size, chunks)
                    
                    for chunk_idx in range(start_idx, end_idx):
                        chunk_offset = chunk_idx * chunk_size
                        future = executor.submit(
                            self.wipe_chunk_mt,
                            device_path,
                            chunk_idx,
                            chunk_offset,
                            chunk_size,
                            device_size,
                            patterns,
                            chunks
                        )
                        futures[future] = chunk_idx
                    
                    # Wait for batch to complete
                    for future in concurrent.futures.as_completed(futures):
                        chunk_idx = futures[future]
                        try:
                            if not future.result(timeout=300):
                                return False
                            operations_done += len(patterns) + 1
                            self.update_progress(
                                (operations_done / total_operations) * 100,
                                f"Completed chunk {chunk_idx + 1}/{chunks}"
                            )
                        except Exception as e:
                            print(f"[ERROR] Chunk {chunk_idx} failed: {str(e)}")
                            return False
                
            return True
            
        except Exception as e:
            print(f"[ERROR] Multithreaded wipe failed: {str(e)}")
            return False

    def crypto_wipe_mt(self, device_info, chunks, chunk_size, device_size):
        """Perform cryptographic erasure with multithreading."""
        device_path = device_info["name"]
        operations_done = 0
        total_operations = chunks * 2
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {}
                
                for chunk_idx in range(chunks):
                    chunk_offset = chunk_idx * chunk_size
                    chunk_size_actual = min(chunk_size, device_size - chunk_offset)
                    
                    future = executor.submit(
                        self.crypto_wipe,
                        device_path,
                        chunk_offset,
                        chunk_size_actual
                    )
                    futures[future] = chunk_idx
                
                for future in concurrent.futures.as_completed(futures):
                    chunk_idx = futures[future]
                    try:
                        if not future.result(timeout=300):
                            return False
                        operations_done += 2
                        self.update_progress(
                            (operations_done / total_operations) * 100,
                            f"Completed crypto chunk {chunk_idx + 1}/{chunks}"
                        )
                    except Exception as e:
                        print(f"[ERROR] Crypto chunk {chunk_idx} failed: {str(e)}")
                        return False
                
            return True
            
        except Exception as e:
            print(f"[ERROR] Multithreaded crypto wipe failed: {str(e)}")
            return False

    # ...rest of existing code...

if __name__ == "__main__":
    root = tk.Tk()
    app = NullNovaGUI(root)
    root.mainloop()