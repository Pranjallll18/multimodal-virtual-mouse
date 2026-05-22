import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions, RunningMode

import numpy as np
import os
import config
from modules import utils

# Path to the downloaded model file
_MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "face_landmarker.task")


class _LandmarkCompat:
    """Wraps the new FaceLandmarker result to look like the old
    mp.solutions.face_mesh NormalizedLandmarkList so that blink.py
    (which calls  landmarks[0].landmark[idx].x/y ) keeps working."""

    class _NLM:
        def __init__(self, x, y, z=0.0):
            self.x = x
            self.y = y
            self.z = z

    def __init__(self, face_landmarks):
        # face_landmarks is a list of NormalizedLandmark objects
        self.landmark = [self._NLM(lm.x, lm.y, lm.z) for lm in face_landmarks]


class _ResultWrapper:
    """Mimics  results.multi_face_landmarks  from the old API."""

    def __init__(self, face_landmarks_list):
        if face_landmarks_list:
            self.multi_face_landmarks = [_LandmarkCompat(fl) for fl in face_landmarks_list]
        else:
            self.multi_face_landmarks = None


class GazeTracker:
    def __init__(self):
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(
                f"FaceLandmarker model not found at: {_MODEL_PATH}\n"
                "Please download it:\n"
                "  python -c \"import urllib.request; urllib.request.urlretrieve("
                "'https://storage.googleapis.com/mediapipe-models/face_landmarker/"
                "face_landmarker/float16/1/face_landmarker.task', 'face_landmarker.task')\""
            )

        options = FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=_MODEL_PATH),
            running_mode=RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
        self.face_landmarker = FaceLandmarker.create_from_options(options)

        # Iris / pupil landmark indices (same as old FaceMesh refined model)
        self.LEFT_IRIS  = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        self.LEFT_PUPIL  = 468
        self.RIGHT_PUPIL = 473

        # Eye corner landmarks
        self.LEFT_EYE_OUTER  = 362
        self.LEFT_EYE_INNER  = 263
        self.LEFT_EYE_TOP    = 386
        self.LEFT_EYE_BOTTOM = 374
        self.RIGHT_EYE_INNER  = 33
        self.RIGHT_EYE_OUTER  = 133
        self.RIGHT_EYE_TOP    = 159
        self.RIGHT_EYE_BOTTOM = 145

        self.prev_gaze = (0, 0)

    def cleanup(self):
        """Release FaceLandmarker resources."""
        if hasattr(self, 'face_landmarker') and self.face_landmarker:
            self.face_landmarker.close()

    def _get_iris_ratio(self, mesh_points):
        """Calculate iris position as a ratio within the eye (0–1).
        Head-movement independent because both iris and corners move together."""
        ratios = []
        for pupil, corner_a, corner_b, top, bottom in [
            (self.LEFT_PUPIL,  self.LEFT_EYE_OUTER,  self.LEFT_EYE_INNER,
             self.LEFT_EYE_TOP,    self.LEFT_EYE_BOTTOM),
            (self.RIGHT_PUPIL, self.RIGHT_EYE_INNER, self.RIGHT_EYE_OUTER,
             self.RIGHT_EYE_TOP,   self.RIGHT_EYE_BOTTOM),
        ]:
            iris = mesh_points[pupil]
            ca   = mesh_points[corner_a]
            cb   = mesh_points[corner_b]
            tp   = mesh_points[top]
            bt   = mesh_points[bottom]

            left_x  = min(ca[0], cb[0])
            right_x = max(ca[0], cb[0])
            eye_w   = right_x - left_x
            ratio_x = (iris[0] - left_x) / eye_w if eye_w > 0 else 0.5

            top_y   = min(tp[1], bt[1])
            bot_y   = max(tp[1], bt[1])
            eye_h   = bot_y - top_y
            ratio_y = (iris[1] - top_y) / eye_h if eye_h > 0 else 0.5

            ratios.append((ratio_x, ratio_y))

        avg_x = (ratios[0][0] + ratios[1][0]) / 2.0
        avg_y = (ratios[0][1] + ratios[1][1]) / 2.0
        return avg_x, avg_y

    def process_frame(self, frame):
        current_gaze = (0, 0)

        # Lighting normalisation
        img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        img_yuv[:, :, 0] = cv2.equalizeHist(img_yuv[:, :, 0])
        frame_eq = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame_eq, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        try:
            detection_result = self.face_landmarker.detect(mp_image)
        except Exception as e:
            print(f"MediaPipe processing error: {e}")
            return frame, (0, 0), None

        # Wrap result to match old API expected by blink.py / main.py
        results = _ResultWrapper(detection_result.face_landmarks)

        if results.multi_face_landmarks:
            h, w = frame.shape[:2]
            mesh_points = np.array([
                [int(lm.x * w), int(lm.y * h)]
                for lm in results.multi_face_landmarks[0].landmark
            ])

            # Draw iris dots
            cv2.circle(frame, tuple(mesh_points[self.LEFT_PUPIL]),  3, (0, 255, 0), -1)
            cv2.circle(frame, tuple(mesh_points[self.RIGHT_PUPIL]), 3, (0, 255, 0), -1)

            # Store raw iris for calibration overlay
            raw_x, raw_y = mesh_points[self.LEFT_PUPIL]
            config.CURRENT_RAW_IRIS = (raw_x, raw_y)

            ratio_x, ratio_y = self._get_iris_ratio(mesh_points)

            if config.HORIZONTAL_FLIP:
                ratio_x = 1.0 - ratio_x
            if config.VERTICAL_FLIP:
                ratio_y = 1.0 - ratio_y

            center_x = 0.5
            center_y = 0.5 + config.VERTICAL_CENTER_OFFSET

            # Normalize raw offsets relative to physiological expected max range
            norm_x = np.clip((ratio_x - center_x) / config.EYE_MAX_DEV_X, -1.0, 1.0)
            norm_y = np.clip((ratio_y - center_y) / config.EYE_MAX_DEV_Y, -1.0, 1.0)

            # Apply non-linear power-scaling (1.3 power).
            # This dampens minor movements near the center (improving click precision)
            # while progressively magnifying larger movements towards screen borders.
            sgn_x = np.sign(norm_x)
            sgn_y = np.sign(norm_y)
            mapped_x = sgn_x * (abs(norm_x) ** 1.3)
            mapped_y = sgn_y * (abs(norm_y) ** 1.3)

            # Scale to screen borders with sensitivities
            offset_x = mapped_x * 0.5 * config.SENSITIVITY_X
            offset_y = mapped_y * 0.5 * config.SENSITIVITY_Y

                        # ... (keep your existing offset_x and offset_y calculation) ...

            raw_screen_x = int(np.clip(
                config.SCREEN_WIDTH  / 2 + offset_x * config.SCREEN_WIDTH,
                0, config.SCREEN_WIDTH  - 1))
            raw_screen_y = int(np.clip(
                config.SCREEN_HEIGHT / 2 + offset_y * config.SCREEN_HEIGHT,
                0, config.SCREEN_HEIGHT - 1))

            # --- STABILIZATION LOGIC ---
            
            # Calculate pixel distance from the last known cursor position
            dist = np.hypot(raw_screen_x - self.prev_gaze[0], raw_screen_y - self.prev_gaze[1])

            # 1. Radial Deadzone (e.g., ignore movements under 8 pixels)
            # You can extract '8' to config.DEADZONE_RADIUS
            if dist < 8:  
                current_gaze = self.prev_gaze
            else:
                # 2. Dynamic Smoothing (1 Euro Filter approximation)
                # High distance = lower alpha (less smoothing, faster response)
                # Low distance = higher alpha (more smoothing, higher precision)
                base_smooth = getattr(config, 'SMOOTHING_FACTOR', 0.7)
                
                # Scale smoothing inversely with distance. Add 1e-5 to prevent division by zero.
                dynamic_alpha = max(0.1, min(0.95, base_smooth * (20.0 / (dist + 1e-5))))
                
                # Apply the dynamic exponential moving average
                smoothed_x = int(self.prev_gaze[0] * dynamic_alpha + raw_screen_x * (1.0 - dynamic_alpha))
                smoothed_y = int(self.prev_gaze[1] * dynamic_alpha + raw_screen_y * (1.0 - dynamic_alpha))
                
                current_gaze = (smoothed_x, smoothed_y)

            self.prev_gaze = current_gaze

        return frame, current_gaze, results.multi_face_landmarks
