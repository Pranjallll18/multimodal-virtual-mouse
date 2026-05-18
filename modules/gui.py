import tkinter as tk
import threading
import time
import config

class CalibrationWindow:
    def __init__(self, master):
        self.master = master
        self.top = tk.Toplevel(master)
        self.top.attributes('-fullscreen', True)
        self.top.configure(bg='black')
        self.points = [
            ("Top Left", 50, 50),
            ("Top Right", config.SCREEN_WIDTH - 50, 50),
            ("Bottom Right", config.SCREEN_WIDTH - 50, config.SCREEN_HEIGHT - 50),
            ("Bottom Left", 50, config.SCREEN_HEIGHT - 50)
        ]
        self.current_point_idx = 0
        
        # Store recordings: list of [(x, y), ...] for each calibration point
        self.recordings = []
        self.sample_count = 0
        self.max_samples = 10  # Collect 10 samples per point
        self.current_samples = []
        
        self.label = tk.Label(self.top, text="Look at the Red Dot", fg="white", bg="black", font=("Arial", 24))
        self.label.pack(pady=50)
        
        self.canvas = tk.Canvas(self.top, width=config.SCREEN_WIDTH, height=config.SCREEN_HEIGHT, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.dot = None
        
        # Start sequence
        self.show_next_point()

    def show_next_point(self):
        if self.current_point_idx >= len(self.points):
            self.finish_calibration()
            return
            
        name, x, y = self.points[self.current_point_idx]
        self.label.config(text=f"Look at {name} - Keep head still!")
        
        if self.dot:
            self.canvas.delete(self.dot)
            
        r = 20
        self.dot = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill='red')
        
        # Start countdown
        self.countdown(3)

    def countdown(self, count):
        if count > 0:
            self.label.config(text=f"Recording in {count}... Keep looking at the dot!")
            self.top.after(1000, lambda: self.countdown(count - 1))
        else:
            # Start sampling
            self.sample_count = 0
            self.current_samples = []
            self.sample_point()

    def sample_point(self):
        """Collect multiple samples and average them for stability"""
        if self.sample_count < self.max_samples:
            raw_x, raw_y = config.CURRENT_RAW_IRIS
            if raw_x != 0 or raw_y != 0:  # Only record valid positions
                self.current_samples.append((raw_x, raw_y))
            self.sample_count += 1
            self.label.config(text=f"Recording... {self.sample_count}/{self.max_samples}")
            self.top.after(100, self.sample_point)  # Sample every 100ms
        else:
            self.finish_recording_point()
    
    def finish_recording_point(self):
        """Finish recording and average the samples"""
        if len(self.current_samples) == 0:
            print(f"Warning: No valid samples for point {self.current_point_idx}")
            # Use last known position
            self.recordings.append(config.CURRENT_RAW_IRIS)
        else:
            # Average all samples
            avg_x = sum(s[0] for s in self.current_samples) / len(self.current_samples)
            avg_y = sum(s[1] for s in self.current_samples) / len(self.current_samples)
            print(f"Recorded point {self.current_point_idx}: ({avg_x:.1f}, {avg_y:.1f}) from {len(self.current_samples)} samples")
            self.recordings.append((avg_x, avg_y))
        
        self.current_point_idx += 1
        self.show_next_point()

    def finish_calibration(self):
        self.top.destroy()
        
        if len(self.recordings) != 4:
            print("Calibration Error: Not enough points")
            return
            
        # Extract Min/Max
        # Order: TL, TR, BR, BL
        p_tl = self.recordings[0]
        p_tr = self.recordings[1]
        p_br = self.recordings[2]
        p_bl = self.recordings[3]
        
        # Logic: 
        # Left Bound (Min X) -> Average of TL.x and BL.x
        # Right Bound (Max X) -> Average of TR.x and BR.x
        # Top Bound (Min Y) -> Average of TL.y and TR.y
        # Bottom Bound (Max Y) -> Average of BL.y and BR.y
        
        avg_left = (p_tl[0] + p_bl[0]) / 2.0
        avg_right = (p_tr[0] + p_br[0]) / 2.0
        avg_top = (p_tl[1] + p_tr[1]) / 2.0
        avg_bottom = (p_bl[1] + p_br[1]) / 2.0
        
        # Validate bounds - ensure reasonable ranges
        x_range = abs(avg_right - avg_left)
        y_range = abs(avg_bottom - avg_top)
        
        if x_range < 50 or y_range < 30:
            print(f"WARNING: Calibration range too narrow! X:{x_range:.1f}px Y:{y_range:.1f}px")
            print("Please recalibrate with larger eye movements.")
            return
        
        config.EYE_LEFT_BOUND = avg_left
        config.EYE_RIGHT_BOUND = avg_right
        config.EYE_TOP_BOUND = avg_top
        config.EYE_BOTTOM_BOUND = avg_bottom
        
        print(f"✓ Calibration successful!")
        print(f"  Bounds: L={avg_left:.1f}, R={avg_right:.1f}, T={avg_top:.1f}, B={avg_bottom:.1f}")
        print(f"  Ranges: X={x_range:.1f}px, Y={y_range:.1f}px")
        config.save_calibration()

class SettingsWindow:
    def __init__(self):
        self.root = None
        self.thread = None
        self.smooth_scale = None
        self.ear_scale = None
        self.status_label = None

    def start(self):
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()

    def _run_gui(self):
        self.root = tk.Tk()
        self.root.title("Settings - Virtual Mouse")
        self.root.geometry("300x350")
        
        # Smoothing Factor
        tk.Label(self.root, text="Smoothing Factor").pack(pady=5)
        self.smooth_scale = tk.Scale(self.root, from_=0.0, to=0.9, resolution=0.1, orient=tk.HORIZONTAL, command=self.update_smooth)
        self.smooth_scale.set(config.SMOOTHING_FACTOR)
        self.smooth_scale.pack(fill=tk.X, padx=20)
        
        # EAR Threshold
        tk.Label(self.root, text="Blink Threshold (EAR)").pack(pady=5)
        self.ear_scale = tk.Scale(self.root, from_=0.1, to=0.4, resolution=0.01, orient=tk.HORIZONTAL, command=self.update_ear)
        self.ear_scale.set(config.EAR_THRESHOLD_CLICK)
        self.ear_scale.pack(fill=tk.X, padx=20)
        
        # Calibration Button
        tk.Button(self.root, text="Calibrate Eye Tracking", command=self.start_calibration, bg="blue", fg="white").pack(pady=20)
        
        # Status Label
        self.status_label = tk.Label(self.root, text="Running...", fg="green")
        self.status_label.pack(pady=5)
        
        self.root.mainloop()

    def update_smooth(self, val):
        config.SMOOTHING_FACTOR = float(val)

    def update_ear(self, val):
        config.EAR_THRESHOLD_CLICK = float(val)

    def start_calibration(self):
        CalibrationWindow(self.root)


