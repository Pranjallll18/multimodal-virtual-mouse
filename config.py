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
SMOOTHING_FACTOR = 0.7      # Smoothing factor (0 = no smoothing, 1 = max smoothing/no movement)
                            # Increased to 0.7 for smoother, more stable cursor movement

# Sensitivity
SENSITIVITY_X = 2.5            # Horizontal sensitivity (reduced from 3.5 to lower jitter)
SENSITIVITY_Y = 3.0            # Vertical sensitivity (higher because eye vertical range is very narrow)
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
