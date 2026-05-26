import numpy as np
import cv2
import time
import sys
import os

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# ---------------------------------------------------------------------------
# MediaPipe FaceMesh indices for EAR calculation
# ---------------------------------------------------------------------------
RIGHT_EYE_IDXS = [33,  160, 158, 133, 153, 144]   # p1..p6
LEFT_EYE_IDXS  = [362, 385, 387, 263, 373, 380]   # p1..p6

# ---------------------------------------------------------------------------
# FIX 1: EAR threshold is now read from config with a safer fallback.
# Old code silently used config.EAR_THRESHOLD_CLICK everywhere — if that
# value was missing or too high it would fire clicks on every frame.
# Recommended value: 0.18  (lower = need a harder close to trigger)
# ---------------------------------------------------------------------------
_EAR_CLICK_THRESHOLD = getattr(config, 'EAR_THRESHOLD_CLICK', 0.18)

# ---------------------------------------------------------------------------
# FIX 2: Separate "natural blink" threshold — slightly higher than click
# threshold so that a gentle blink never accidentally registers as a wink.
# Old code reused the same threshold for both, making accidental clicks
# common during normal blinking.
# ---------------------------------------------------------------------------
_EAR_NATURAL_BLINK_THRESHOLD = getattr(config, 'EAR_NATURAL_BLINK_THRESHOLD',
                                        _EAR_CLICK_THRESHOLD + 0.04)

# ---------------------------------------------------------------------------
# FIX 3: Minimum frames a wink must be held to count as intentional.
# Old default was config.BLINK_FRAMES which could be as low as 1, making
# any accidental half-close trigger a click.
# Recommended: 2–3 frames  (~66–100 ms at 30 fps)
# ---------------------------------------------------------------------------
_MIN_WINK_FRAMES = getattr(config, 'BLINK_FRAMES', 2)

# ---------------------------------------------------------------------------
# FIX 4: Maximum frames a wink may last before it is ignored (held-closed).
# Without this, looking sideways with one eye squinted for >1 s keeps
# re-triggering clicks on cooldown expiry.
# Recommended: 12 frames (~400 ms at 30 fps)
# ---------------------------------------------------------------------------
_MAX_WINK_FRAMES = getattr(config, 'BLINK_MAX_FRAMES', 12)

# ---------------------------------------------------------------------------
# FIX 5: Per-click cooldown (seconds).  Was read from config but no fallback
# existed. 0.6 s prevents double-fire on slow blinkers.
# ---------------------------------------------------------------------------
_CLICK_COOLDOWN = getattr(config, 'CLICK_COOLDOWN', 0.6)


class BlinkDetector:
    def __init__(self):
        self.last_blink_time: float = 0.0

        # Frame counters — track how long each eye has been closed
        self.blink_frame_counter_left  = 0
        self.blink_frame_counter_right = 0
        self.both_closed_counter       = 0

        # FIX 6: Rolling EAR buffer for smoothing — averages last N EAR
        # readings per eye so a single noisy frame doesn't trigger a click.
        # Old code used the raw single-frame EAR with no smoothing.
        _buf = 3   # number of frames to average
        self._left_ear_buf  = [0.3] * _buf
        self._right_ear_buf = [0.3] * _buf

    # ------------------------------------------------------------------
    # Public property — used by main.py to freeze cursor during blinks
    # ------------------------------------------------------------------
    @property
    def is_eyes_closing(self):
        """True when any eye is currently closing (blink in progress)."""
        return (self.blink_frame_counter_left  > 0
                or self.blink_frame_counter_right > 0
                or self.both_closed_counter       > 0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _distance(p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))

    def _get_ear(self, landmarks, indices, frame_shape):
        """Return Eye Aspect Ratio for one eye."""
        h, w = frame_shape[:2]
        coords = [(int(landmarks[i].x * w), int(landmarks[i].y * h))
                  for i in indices]
        p1, p2, p3, p4, p5, p6 = coords
        v1 = self._distance(p2, p6)
        v2 = self._distance(p3, p5)
        hz = self._distance(p1, p4)
        return (v1 + v2) / (2.0 * hz) if hz > 0 else 0.3

    def _smooth_ear(self, buf, new_val):
        """Push new EAR value into rolling buffer and return the mean."""
        buf.pop(0)
        buf.append(new_val)
        return float(np.mean(buf))

    # ------------------------------------------------------------------
    # Main detection method
    # ------------------------------------------------------------------
    def detect_blink(self, frame, landmarks):
        """Analyse the current frame and return an action string or None.

        Returns
        -------
        "left_click"  — deliberate left-eye wink detected
        "right_click" — deliberate right-eye wink detected
        None          — no action this frame
        """
        if not landmarks:
            return None

        points = landmarks[0].landmark
        shape  = frame.shape

        # --- Raw EAR ---
        raw_left  = self._get_ear(points, LEFT_EYE_IDXS,  shape)
        raw_right = self._get_ear(points, RIGHT_EYE_IDXS, shape)

        # FIX 6: Smooth over last N frames to kill single-frame noise
        left_ear  = self._smooth_ear(self._left_ear_buf,  raw_left)
        right_ear = self._smooth_ear(self._right_ear_buf, raw_right)

        current_time = time.time()
        action = None

        # FIX 2: Use the higher natural-blink threshold to decide "both closed"
        # so that a gentle blink (EAR just dips below click threshold on one
        # side) is not mistaken for a wink.
        left_closed_natural  = left_ear  < _EAR_NATURAL_BLINK_THRESHOLD
        right_closed_natural = right_ear < _EAR_NATURAL_BLINK_THRESHOLD
        both_closed          = left_closed_natural and right_closed_natural

        # Intentional-wink thresholds (stricter — eye must close harder)
        left_wink_closed  = left_ear  < _EAR_CLICK_THRESHOLD
        right_wink_closed = right_ear < _EAR_CLICK_THRESHOLD

        if both_closed:
            # Natural bilateral blink — ignore entirely, reset wink counters
            self.both_closed_counter += 1
            self.blink_frame_counter_left  = 0
            self.blink_frame_counter_right = 0

        else:
            self.both_closed_counter = 0

            # ---- Left eye wink (left closed, right open) ----
            if left_wink_closed and not right_closed_natural:
                self.blink_frame_counter_left += 1

                # FIX 4: If held too long treat as a squint — reset silently
                if self.blink_frame_counter_left > _MAX_WINK_FRAMES:
                    self.blink_frame_counter_left = 0

            else:
                # Eye just opened — check if the closed duration was intentional
                if _MIN_WINK_FRAMES <= self.blink_frame_counter_left <= _MAX_WINK_FRAMES:
                    if current_time - self.last_blink_time > _CLICK_COOLDOWN:
                        action = "left_click"
                        self.last_blink_time = current_time
                        if getattr(config, 'DEBUG', False):
                            print(f"[blink] Left click | EAR={left_ear:.3f} "
                                  f"frames={self.blink_frame_counter_left}")
                self.blink_frame_counter_left = 0

            # ---- Right eye wink (right closed, left open) ----
            if right_wink_closed and not left_closed_natural:
                self.blink_frame_counter_right += 1

                # FIX 4: Same squint guard for right eye
                if self.blink_frame_counter_right > _MAX_WINK_FRAMES:
                    self.blink_frame_counter_right = 0

            else:
                if _MIN_WINK_FRAMES <= self.blink_frame_counter_right <= _MAX_WINK_FRAMES:
                    if current_time - self.last_blink_time > _CLICK_COOLDOWN:
                        action = "right_click"
                        self.last_blink_time = current_time
                        if getattr(config, 'DEBUG', False):
                            print(f"[blink] Right click | EAR={right_ear:.3f} "
                                  f"frames={self.blink_frame_counter_right}")
                self.blink_frame_counter_right = 0

        # FIX 7: Debug overlay — draw smoothed EAR values (not raw) and
        # show per-eye state labels so you can see what the detector sees.
        if getattr(config, 'DEBUG', False):
            left_state  = ("WINK" if left_wink_closed  else
                           "BLINK" if left_closed_natural else "open")
            right_state = ("WINK" if right_wink_closed else
                           "BLINK" if right_closed_natural else "open")

            cv2.putText(frame,
                        f"L EAR: {left_ear:.2f}  [{left_state}]"
                        f"  frames:{self.blink_frame_counter_left}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame,
                        f"R EAR: {right_ear:.2f}  [{right_state}]"
                        f"  frames:{self.blink_frame_counter_right}",
                        (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)

        return action