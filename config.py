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
SMOOTHING_FACTOR = 0.92     # Higher = smoother but slightly slower response (0=raw, 1=frozen)

# Sensitivity & Physiological Dev bounds
EYE_MAX_DEV_X = 0.12           # Horizontal max pupil deviation
EYE_MAX_DEV_Y = 0.10           # Vertical max deviation — wider range for full vertical reach
SENSITIVITY_X = 0.5            # Horizontal sensitivity multiplier (slowed down)
SENSITIVITY_Y = 0.7            # Vertical sensitivity (slowed down)
# VERTICAL_CENTER_OFFSET explains:
#   center_y = 0.5 + VERTICAL_CENTER_OFFSET
#   The iris in natural forward gaze sits at ratio_y ≈ 0.40 (upper part of eye opening)
#   So to map forward gaze → screen center, center_y must ≈ 0.40 → offset = -0.10
#   Look DOWN → ratio_y rises → norm_y positive → cursor moves DOWN (bottom of screen)
#   Look UP   → ratio_y falls → norm_y negative → cursor moves UP   (top of screen)
VERTICAL_CENTER_OFFSET = -0.10  # NEGATIVE: shifts center_y down to match natural iris position
HORIZONTAL_FLIP = True          # Flip horizontal axis to correct mirrored camera view
VERTICAL_FLIP = False           # Keep False: looking down increases ratio_y → cursor down

# Deadzone & Speed Limits
DEADZONE_RADIUS = 14           # Pixels — small jitter under this radius is ignored
MAX_CURSOR_SPEED = 40          # Max pixels the cursor can jump per frame (clamps sudden jerks)

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
METRICS_CLICKS_TOTAL: int = 0
METRICS_CLICKS_SUCCESS: int = 0
METRICS_CLICK_ACCURACY: float = 0.0
METRICS_DICTATION_WORDS: int = 0
METRICS_DICTATION_SECONDS: float = 0.0
METRICS_DICTATION_WPM: float = 0.0

# Active evaluation variables
EVAL_ACTIVE: bool = False
EVAL_STAGE: int = 0  # 0: Not started, 1: Click target, 2: Voice dictation phrase
EVAL_START_TIME: float = 0.0
EVAL_TARGET_POS: tuple[int, int] = (0, 0)
EVAL_MESSAGE_TO_SPEAK: str = "the quick brown fox jumps over the lazy dog"
EVAL_TASK_COMPLETIONS: int = 0
EVAL_TOTAL_TASKS: int = 0

