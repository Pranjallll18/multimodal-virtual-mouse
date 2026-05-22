# Configuration Settings

# Debug
DEBUG = False  # Set to True to show EAR values and other debug overlays on the video feed

# Camera
CAMERA_ID = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Blink Detection
EAR_THRESHOLD_CLICK = 0.18  # Eye Aspect Ratio threshold (Adjust per user, lowered to 0.18 for better true blink detection)
BLINK_FRAMES = 3            # Number of consecutive frames for a valid blink
CLICK_COOLDOWN = 1.0        # Seconds between clicks (Increased to prevent accidental multiple clicks)

# Smoothing
SMOOTHING_FACTOR = 0.8      # Base smoothing factor (0 = no smoothing, 1 = max smoothing/no movement)

# Sensitivity & Physiological Dev bounds
EYE_MAX_DEV_X = 0.15           # Maximum expected horizontal pupil offset from center
EYE_MAX_DEV_Y = 0.08           # Maximum expected vertical pupil offset ( eyelid restricted)
SENSITIVITY_X = 1.3            # Horizontal sensitivity multiplier
SENSITIVITY_Y = 1.6            # Vertical sensitivity multiplier (higher to make bottom reach effortless)
VERTICAL_CENTER_OFFSET = 0.04  # Shift the "center" of vertical gaze downward
                               # (iris naturally sits slightly above eye center, so cursor drifts up)
HORIZONTAL_FLIP = True         # Flip horizontal axis to correct mirrored camera view
VERTICAL_FLIP = False          # Set True if cursor Y is inverted (moves up when you look down)

# Screen Mapping
SCREEN_WIDTH = 1920         # Default (will be updated)
SCREEN_HEIGHT = 1080

# Eye Bounds (Calibration - these need to be tuned per user)
# These represent the min/max x and y coordinates of the pupil within the webcam frame or relative to eye corners
EYE_LEFT_BOUND = 0          # Example placeholder
EYE_RIGHT_BOUND = 640       # Example placeholder
EYE_TOP_BOUND = 0
EYE_BOTTOM_BOUND = 480

# Calibration Data
CALIBRATION_FILE = "calibration.json"
CURRENT_RAW_IRIS = (0, 0)   # Store (x, y) of iris center for calibration

import json
import os

def save_calibration():
    data = {
        "EYE_LEFT_BOUND": EYE_LEFT_BOUND,
        "EYE_RIGHT_BOUND": EYE_RIGHT_BOUND,
        "EYE_TOP_BOUND": EYE_TOP_BOUND,
        "EYE_BOTTOM_BOUND": EYE_BOTTOM_BOUND
    }
    try:
        with open(CALIBRATION_FILE, "w") as f:
            json.dump(data, f)
        print("Calibration saved.")
    except Exception as e:
        print(f"Error saving calibration: {e}")

def load_calibration():
    global EYE_LEFT_BOUND, EYE_RIGHT_BOUND, EYE_TOP_BOUND, EYE_BOTTOM_BOUND
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r") as f:
                data = json.load(f)
                EYE_LEFT_BOUND = data.get("EYE_LEFT_BOUND", EYE_LEFT_BOUND)
                EYE_RIGHT_BOUND = data.get("EYE_RIGHT_BOUND", EYE_RIGHT_BOUND)
                EYE_TOP_BOUND = data.get("EYE_TOP_BOUND", EYE_TOP_BOUND)
                EYE_BOTTOM_BOUND = data.get("EYE_BOTTOM_BOUND", EYE_BOTTOM_BOUND)
            print("Calibration loaded.")
        except Exception as e:
            print(f"Error loading calibration: {e}")

# Load on import
load_calibration()

# Audio TTS settings
AUDIO_TTS_ENABLED = True

# Performance Metrics (Evaluatable Mode)
METRICS_CLICKS_TOTAL = 0
METRICS_CLICKS_SUCCESS = 0
METRICS_CLICK_ACCURACY = 0.0
METRICS_DICTATION_WORDS = 0
METRICS_DICTATION_SECONDS = 0.0
METRICS_DICTATION_WPM = 0.0

# Active evaluation variables
EVAL_ACTIVE = False
EVAL_STAGE = 0  # 0: Not started, 1: Click target, 2: Voice dictation phrase
EVAL_START_TIME = 0.0
EVAL_TARGET_POS = (0, 0)
EVAL_MESSAGE_TO_SPEAK = "the quick brown fox jumps over the lazy dog"
EVAL_TASK_COMPLETIONS = 0
EVAL_TOTAL_TASKS = 0

