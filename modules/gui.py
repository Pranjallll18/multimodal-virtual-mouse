import tkinter as tk
from tkinter import ttk
import threading
import time
import random
import config
from modules.utils import speak

class CalibrationWindow:
    def __init__(self, master):
        self.master = master
        self.top = tk.Toplevel(master)
        self.top.attributes('-fullscreen', True)
        self.top.configure(bg='#0f0f17')
        self.points = [
            ("Top Left", 100, 100),
            ("Top Right", config.SCREEN_WIDTH - 100, 100),
            ("Bottom Right", config.SCREEN_WIDTH - 100, config.SCREEN_HEIGHT - 100),
            ("Bottom Left", 100, config.SCREEN_HEIGHT - 100)
        ]
        self.current_point_idx = 0
        
        # Store recordings: list of [(x, y), ...] for each calibration point
        self.recordings = []
        self.sample_count = 0
        self.max_samples = 10  # Collect 10 samples per point
        self.current_samples = []
        
        self.label = tk.Label(self.top, text="Calibration Wizard", fg="#cdd6f4", bg="#0f0f17", font=("Outfit", 26, "bold"))
        self.label.pack(pady=40)
        
        self.canvas = tk.Canvas(self.top, width=config.SCREEN_WIDTH, height=config.SCREEN_HEIGHT, bg='#0f0f17', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.dot = None
        speak("Calibration wizard started. Keep your head still and look at the red dots as they appear.")
        self.show_next_point()

    def show_next_point(self):
        if self.current_point_idx >= len(self.points):
            self.finish_calibration()
            return
            
        name, x, y = self.points[self.current_point_idx]
        self.label.config(text=f"Look at {name} - Keep head still!")
        
        if self.dot:
            self.canvas.delete(self.dot)
            
        r = 25
        # Red outer ring, white inner dot
        self.dot = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill='#ff5555', outline='#ffffff', width=3)
        self.dot_inner = self.canvas.create_oval(x-6, y-6, x+6, y+6, fill='white')
        
        # Start countdown
        self.countdown(3)

    def countdown(self, count):
        if count > 0:
            self.label.config(text=f"Recording in {count}s... Look at the dot!")
            self.top.after(1000, lambda: self.countdown(count - 1))
        else:
            self.sample_count = 0
            self.current_samples = []
            self.sample_point()

    def sample_point(self):
        if self.sample_count < self.max_samples:
            raw_x, raw_y = config.CURRENT_RAW_IRIS
            if raw_x != 0 or raw_y != 0:
                self.current_samples.append((raw_x, raw_y))
            self.sample_count += 1
            self.label.config(text=f"Recording point... {self.sample_count}/{self.max_samples}")
            self.top.after(100, self.sample_point)
        else:
            self.finish_recording_point()
    
    def finish_recording_point(self):
        if len(self.current_samples) == 0:
            self.recordings.append(config.CURRENT_RAW_IRIS)
        else:
            avg_x = sum(s[0] for s in self.current_samples) / len(self.current_samples)
            avg_y = sum(s[1] for s in self.current_samples) / len(self.current_samples)
            self.recordings.append((avg_x, avg_y))
        
        self.canvas.delete(self.dot_inner)
        self.current_point_idx += 1
        self.show_next_point()

    def finish_calibration(self):
        self.top.destroy()
        if len(self.recordings) != 4:
            return
            
        p_tl = self.recordings[0]
        p_tr = self.recordings[1]
        p_br = self.recordings[2]
        p_bl = self.recordings[3]
        
        avg_left = (p_tl[0] + p_bl[0]) / 2.0
        avg_right = (p_tr[0] + p_br[0]) / 2.0
        avg_top = (p_tl[1] + p_tr[1]) / 2.0
        avg_bottom = (p_bl[1] + p_br[1]) / 2.0
        
        x_range = abs(avg_right - avg_left)
        y_range = abs(avg_bottom - avg_top)
        
        if x_range < 40 or y_range < 20:
            speak("Calibration range too narrow. Please try again.")
            return
        
        config.EYE_LEFT_BOUND = avg_left
        config.EYE_RIGHT_BOUND = avg_right
        config.EYE_TOP_BOUND = avg_top
        config.EYE_BOTTOM_BOUND = avg_bottom
        
        speak("Calibration successful!")
        config.save_calibration()


class EvaluationWindow:
    def __init__(self, master):
        self.master = master
        self.top = tk.Toplevel(master)
        self.top.attributes('-fullscreen', True)
        self.top.configure(bg='#0f0f17')
        
        # Select target dot position
        self.target_x = random.randint(200, config.SCREEN_WIDTH - 200)
        self.target_y = random.randint(200, config.SCREEN_HEIGHT - 200)
        config.EVAL_TARGET_POS = (self.target_x, self.target_y)
        
        config.EVAL_ACTIVE = True
        config.EVAL_STAGE = 1
        self.start_time = time.time()
        
        self.label = tk.Label(self.top, text="Performance Evaluation Wizard", fg="#cdd6f4", bg="#0f0f17", font=("Outfit", 26, "bold"))
        self.label.pack(pady=40)
        
        self.desc_label = tk.Label(self.top, text="Stage 1: Look at the Green Target and wink (blink) to left click it.", fg="#a6adc8", bg="#0f0f17", font=("Outfit", 18))
        self.desc_label.pack(pady=10)

        self.canvas = tk.Canvas(self.top, width=config.SCREEN_WIDTH, height=config.SCREEN_HEIGHT, bg='#0f0f17', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        r = 30
        self.target_ring = self.canvas.create_oval(self.target_x-r, self.target_y-r, self.target_x+r, self.target_y+r, fill='#50fa7b', outline='#ffffff', width=4)
        self.target_center = self.canvas.create_oval(self.target_x-6, self.target_y-6, self.target_x+6, self.target_y+6, fill='white')
        
        speak("Evaluation mode active. Stage one: Look at the green target and wink to left-click it.")
        
        self.check_loop()

    def check_loop(self):
        if not config.EVAL_ACTIVE:
            self.top.destroy()
            return
            
        if config.EVAL_STAGE == 2:
            # Transition to Voice Phrase
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.destroy()
            self.desc_label.config(text=f"Stage 2: Speak the sentence below clearly:\n\n\"{config.EVAL_MESSAGE_TO_SPEAK}\"", fg="#f9e2af", font=("Outfit", 22, "bold"))
            self.top.after(100, self.check_voice_loop)
            return
            
        self.top.after(100, self.check_loop)

    def check_voice_loop(self):
        if not config.EVAL_ACTIVE:
            self.top.destroy()
            return
        self.top.after(100, self.check_voice_loop)


class SettingsWindow:
    def __init__(self):
        self.root = None
        self.thread = None
        
        # Style references
        self.smooth_scale = None
        self.ear_scale = None
        
        # Performance Labels
        self.clicks_accuracy_val = None
        self.voice_wpm_val = None
        self.task_success_val = None

    def start(self):
        self.thread = threading.Thread(target=self._run_gui, daemon=True)
        self.thread.start()

    def _run_gui(self):
        self.root = tk.Tk()
        self.root.title("Multimodal Mouse - Control Panel")
        self.root.geometry("640x500")
        self.root.configure(bg="#1e1e2e")
        
        # Dark Theme Styles
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#1e1e2e', borderwidth=0)
        style.configure('TNotebook.Tab', background='#313244', foreground='#cdd6f4', padding=[15, 5], font=("Outfit", 12))
        style.map('TNotebook.Tab', background=[('selected', '#89b4fa')], foreground=[('selected', '#11111b')])
        style.configure('TFrame', background='#1e1e2e')
        style.configure('TLabel', background='#1e1e2e', foreground='#cdd6f4', font=("Outfit", 11))
        
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Controls
        tab_controls = ttk.Frame(notebook)
        notebook.add(tab_controls, text="Control System")
        self._build_controls_tab(tab_controls)
        
        # Tab 2: Evaluation & Benchmarks
        tab_eval = ttk.Frame(notebook)
        notebook.add(tab_eval, text="Evaluation & Research Benchmarks")
        self._build_eval_tab(tab_eval)
        
        # Start auto-update loop for real-time stats
        self.update_stats()
        
        self.root.mainloop()

    def _build_controls_tab(self, frame):
        # Header
        title = tk.Label(frame, text="Eye Tracking & Click Controls", fg="#89b4fa", bg="#1e1e2e", font=("Outfit", 18, "bold"))
        title.pack(pady=15)
        
        # Smoothing
        tk.Label(frame, text="Cursor Smoothing", fg="#a6adc8", bg="#1e1e2e", font=("Outfit", 12)).pack(pady=5)
        self.smooth_scale = tk.Scale(frame, from_=0.0, to=0.9, resolution=0.1, orient=tk.HORIZONTAL, bg="#313244", fg="#cdd6f4", highlightthickness=0, activebackground="#89b4fa")
        self.smooth_scale.set(config.SMOOTHING_FACTOR)
        self.smooth_scale.pack(fill=tk.X, padx=40, pady=5)
        self.smooth_scale.config(command=self.update_smooth)
        
        # EAR Threshold
        tk.Label(frame, text="Blink (Wink) Threshold EAR", fg="#a6adc8", bg="#1e1e2e", font=("Outfit", 12)).pack(pady=5)
        self.ear_scale = tk.Scale(frame, from_=0.1, to=0.4, resolution=0.01, orient=tk.HORIZONTAL, bg="#313244", fg="#cdd6f4", highlightthickness=0, activebackground="#89b4fa")
        self.ear_scale.set(config.EAR_THRESHOLD_CLICK)
        self.ear_scale.pack(fill=tk.X, padx=40, pady=5)
        self.ear_scale.config(command=self.update_ear)
        
        # Buttons
        btn_frame = tk.Frame(frame, bg="#1e1e2e")
        btn_frame.pack(pady=30)
        
        cal_btn = tk.Button(btn_frame, text="Launch Calibration Wizard", command=self.start_calibration, bg="#89b4fa", fg="#11111b", font=("Outfit", 12, "bold"), padx=15, pady=8, bd=0, activebackground="#b4befe")
        cal_btn.pack(side=tk.LEFT, padx=10)

    def _build_eval_tab(self, frame):
        # Header
        title = tk.Label(frame, text="Performance Evaluation & Benchmarks", fg="#a6e3a1", bg="#1e1e2e", font=("Outfit", 16, "bold"))
        title.pack(pady=10)
        
        desc = tk.Label(frame, text="Compare your metrics directly with state-of-the-art research benchmarks.", fg="#a6adc8", bg="#1e1e2e", font=("Outfit", 10, "italic"))
        desc.pack(pady=5)
        
        # Main Layout: 2 Columns
        cols_frame = tk.Frame(frame, bg="#1e1e2e")
        cols_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left Col: Your Stats
        left_col = tk.LabelFrame(cols_frame, text=" Your System Metrics ", fg="#a6e3a1", bg="#1e1e2e", font=("Outfit", 11, "bold"), padx=10, pady=10, bd=1, relief=tk.SOLID)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        self.clicks_accuracy_val = tk.Label(left_col, text="Click Accuracy: 0.0%", fg="#f9e2af", bg="#1e1e2e", font=("Outfit", 12, "bold"))
        self.clicks_accuracy_val.pack(anchor=tk.W, pady=8)
        
        self.voice_wpm_val = tk.Label(left_col, text="Voice Typing: 0.0 WPM", fg="#f9e2af", bg="#1e1e2e", font=("Outfit", 12, "bold"))
        self.voice_wpm_val.pack(anchor=tk.W, pady=8)
        
        self.task_success_val = tk.Label(left_col, text="Task Success Rate: 0.0%", fg="#f9e2af", bg="#1e1e2e", font=("Outfit", 12, "bold"))
        self.task_success_val.pack(anchor=tk.W, pady=8)
        
        # Right Col: Literature Stats
        right_col = tk.LabelFrame(cols_frame, text=" Research Benchmarks (SOTA) ", fg="#89b4fa", bg="#1e1e2e", font=("Outfit", 11, "bold"), padx=10, pady=10, bd=1, relief=tk.SOLID)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        lit_clicks = tk.Label(right_col, text="Wink Accuracy: 88.0% - 94.0%\n(Grauman et al., 2003)", fg="#a6adc8", bg="#1e1e2e", justify=tk.LEFT, font=("Outfit", 10))
        lit_clicks.pack(anchor=tk.W, pady=8)
        
        lit_voice = tk.Label(right_col, text="Voice Typing Speed: 15.0 - 25.0 WPM\n(Wastlund et al., 2010)", fg="#a6adc8", bg="#1e1e2e", justify=tk.LEFT, font=("Outfit", 10))
        lit_voice.pack(anchor=tk.W, pady=8)
        
        lit_tcr = tk.Label(right_col, text="Gaze Task Success: 85.0% - 92.0%\n(Fejtova et al., 2009)", fg="#a6adc8", bg="#1e1e2e", justify=tk.LEFT, font=("Outfit", 10))
        lit_tcr.pack(anchor=tk.W, pady=8)
        
        # Launch Test Button
        test_btn = tk.Button(frame, text="⚡ Run Performance Evaluation Test", command=self.start_evaluation, bg="#a6e3a1", fg="#11111b", font=("Outfit", 12, "bold"), padx=20, pady=8, bd=0, activebackground="#94e2d5")
        test_btn.pack(pady=15)

    def update_smooth(self, val):
        config.SMOOTHING_FACTOR = float(val)

    def update_ear(self, val):
        config.EAR_THRESHOLD_CLICK = float(val)

    def start_calibration(self):
        CalibrationWindow(self.root)

    def start_evaluation(self):
        EvaluationWindow(self.root)

    def update_stats(self):
        # Calculate Click accuracy
        acc = config.METRICS_CLICK_ACCURACY
        wpm = config.METRICS_DICTATION_WPM
        
        success_rate = 0.0
        if config.EVAL_TOTAL_TASKS > 0:
            success_rate = (config.EVAL_TASK_COMPLETIONS / config.EVAL_TOTAL_TASKS) * 100.0
            
        if self.clicks_accuracy_val:
            self.clicks_accuracy_val.config(text=f"Click Accuracy: {acc:.1f}%")
        if self.voice_wpm_val:
            self.voice_wpm_val.config(text=f"Voice Typing: {wpm:.1f} WPM")
        if self.task_success_val:
            self.task_success_val.config(text=f"Task Success Rate: {success_rate:.1f}%")
            
        # Re-trigger update every 500ms
        if self.root:
            self.root.after(500, self.update_stats)
