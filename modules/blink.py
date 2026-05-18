import numpy as np
import cv2
import time
import sys
import os

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# MediaPipe FaceMesh indices for EAR
# Right Eye
RIGHT_EYE_IDXS = [33, 160, 158, 133, 153, 144] # p1, p2, p3, p4, p5, p6
# Left Eye
LEFT_EYE_IDXS = [362, 385, 387, 263, 373, 380] # p1, p2, p3, p4, p5, p6

class BlinkDetector:
    def __init__(self):
        self.last_blink_time = 0
        self.blink_frame_counter_left = 0
        self.blink_frame_counter_right = 0
        self.both_closed_counter = 0  # Track natural (both-eyes) blinks

    @property
    def is_eyes_closing(self):
        """True when any eye is currently closing (blink in progress).
        Used by main.py to freeze cursor during blinks."""
        return (self.blink_frame_counter_left > 0
                or self.blink_frame_counter_right > 0
                or self.both_closed_counter > 0)

    def calculate_distance(self, p1, p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))

    def get_ear(self, landmarks, indices, frame_shape):
        # Retrieve landmarks
        coords = []
        for idx in indices:
            lm = landmarks[idx]
            # Convert to pixel coordinates
            coords.append((int(lm.x * frame_shape[1]), int(lm.y * frame_shape[0])))
            
        p1, p2, p3, p4, p5, p6 = coords
        
        # EAR Formula
        # EAR = (|p2 - p6| + |p3 - p5|) / (2 * |p1 - p4|)
        vertical_1 = self.calculate_distance(p2, p6)
        vertical_2 = self.calculate_distance(p3, p5)
        horizontal = self.calculate_distance(p1, p4)
        
        if horizontal == 0:
            return 0.0
            
        ear = (vertical_1 + vertical_2) / (2.0 * horizontal)
        return ear

    def detect_blink(self, frame, landmarks):
        if not landmarks:
            return None

        points = landmarks[0].landmark
        shape = frame.shape

        left_ear = self.get_ear(points, LEFT_EYE_IDXS, shape)
        right_ear = self.get_ear(points, RIGHT_EYE_IDXS, shape)

        action = None
        current_time = time.time()

        # Track individual eye blinks
        left_eye_closed = left_ear < config.EAR_THRESHOLD_CLICK
        right_eye_closed = right_ear < config.EAR_THRESHOLD_CLICK
        both_closed = left_eye_closed and right_eye_closed

        # Natural blink (both eyes) — ignore to avoid accidental clicks
        if both_closed:
            self.both_closed_counter += 1
            # Reset individual counters so a natural blink
            # is never misinterpreted as a wink
            self.blink_frame_counter_left = 0
            self.blink_frame_counter_right = 0
        else:
            self.both_closed_counter = 0

            # Left Eye Wink (left closed, right open)
            if left_eye_closed and not right_eye_closed:
                self.blink_frame_counter_left += 1
            else:
                if self.blink_frame_counter_left >= config.BLINK_FRAMES:
                    if current_time - self.last_blink_time > config.CLICK_COOLDOWN:
                        action = "left_click"
                        # pyrefly: ignore [bad-assignment]
                        self.last_blink_time = current_time
                        print(f"Left Click Triggered! Left EAR: {left_ear:.2f}")
                self.blink_frame_counter_left = 0

            # Right Eye Wink (right closed, left open)
            if right_eye_closed and not left_eye_closed:
                self.blink_frame_counter_right += 1
            else:
                if self.blink_frame_counter_right >= config.BLINK_FRAMES:
                    if current_time - self.last_blink_time > config.CLICK_COOLDOWN:
                        action = "right_click"
                        # pyrefly: ignore [bad-assignment]
                        self.last_blink_time = current_time
                        print(f"Right Click Triggered! Right EAR: {right_ear:.2f}")
                self.blink_frame_counter_right = 0

        # Draw EAR on frame for debug (controlled by config.DEBUG)
        if getattr(config, 'DEBUG', False):
            cv2.putText(frame, f"Left EAR: {left_ear:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Right EAR: {right_ear:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return action
