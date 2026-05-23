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

        # EAR landmark indices for wink detection inside tracker
        # (same as blink.py so we stay consistent)
        self.LEFT_EYE_EAR_IDXS  = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE_EAR_IDXS = [33,  160, 158, 133, 153, 144]
        self.EAR_WINK_THRESHOLD  = 0.20   # If one eye EAR < this it is considered winking

    def cleanup(self):
        """Release FaceLandmarker resources."""
        if hasattr(self, 'face_landmarker') and self.face_landmarker:
            self.face_landmarker.close()

    def _get_eye_ear(self, mesh_points, indices, h, w):
        """Calculate Eye Aspect Ratio for one eye from pixel mesh_points."""
        coords = [mesh_points[i] for i in indices]  # already pixel coords
        p1, p2, p3, p4, p5, p6 = coords
        v1 = np.linalg.norm(p2 - p6)
        v2 = np.linalg.norm(p3 - p5)
        hz = np.linalg.norm(p1 - p4)
        return (v1 + v2) / (2.0 * hz) if hz > 0 else 0.3

    def _get_iris_ratio(self, mesh_points,
                        left_winking=False, right_winking=False):
        """Calculate iris position ratio within the eye (0–1).
        If one eye is winking, only the open eye is used to avoid
        landmark distortion causing a cursor jump."""
        results = []

        eye_configs = [
            # (pupil, outer_corner, inner_corner, top, bottom, is_winking)
            (self.LEFT_PUPIL,  self.LEFT_EYE_OUTER,  self.LEFT_EYE_INNER,
             self.LEFT_EYE_TOP,  self.LEFT_EYE_BOTTOM,  left_winking),
            (self.RIGHT_PUPIL, self.RIGHT_EYE_INNER, self.RIGHT_EYE_OUTER,
             self.RIGHT_EYE_TOP, self.RIGHT_EYE_BOTTOM, right_winking),
        ]

        for pupil, corner_a, corner_b, top, bottom, winking in eye_configs:
            if winking:
                continue   # skip distorted winking eye entirely

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

            results.append((ratio_x, ratio_y))

        if not results:
            # Both eyes winking (shouldn't happen) — hold last position
            return None, None

        avg_x = sum(r[0] for r in results) / len(results)
        avg_y = sum(r[1] for r in results) / len(results)
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

            # --- Wink detection: compute EAR per eye ---
            # If one eye is closed (winking), skip that eye's iris data entirely
            # so the distorted landmark doesn't cause a cursor jump.
            left_ear  = self._get_eye_ear(mesh_points, self.LEFT_EYE_EAR_IDXS,  h, w)
            right_ear = self._get_eye_ear(mesh_points, self.RIGHT_EYE_EAR_IDXS, h, w)
            left_winking  = left_ear  < self.EAR_WINK_THRESHOLD
            right_winking = right_ear < self.EAR_WINK_THRESHOLD

            ratio_x, ratio_y = self._get_iris_ratio(
                mesh_points,
                left_winking=left_winking,
                right_winking=right_winking,
            )

            # If both eyes closed (natural blink) hold the last position
            if ratio_x is None:
                current_gaze = self.prev_gaze
                return frame, current_gaze, results.multi_face_landmarks

            if config.HORIZONTAL_FLIP:
                ratio_x = 1.0 - ratio_x
            if config.VERTICAL_FLIP:
                ratio_y = 1.0 - ratio_y

            center_x = 0.5
            center_y = 0.5 + config.VERTICAL_CENTER_OFFSET

            # Normalize raw offsets relative to physiological expected max range
            norm_x = np.clip((ratio_x - center_x) / config.EYE_MAX_DEV_X, -1.0, 1.0)
            norm_y = np.clip((ratio_y - center_y) / config.EYE_MAX_DEV_Y, -1.0, 1.0)

            # Apply non-linear power-scaling (1.5 power = steeper dead-center suppression).
            # Movements very close to center stay near-zero (great for click precision),
            # while large eye movements are still mapped to screen edges.
            sgn_x = np.sign(norm_x)
            sgn_y = np.sign(norm_y)
            mapped_x = sgn_x * (abs(norm_x) ** 1.5)
            mapped_y = sgn_y * (abs(norm_y) ** 1.5)

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

            deadzone  = getattr(config, 'DEADZONE_RADIUS', 12)
            max_speed = getattr(config, 'MAX_CURSOR_SPEED', 60)

            # Calculate pixel distance from the last known cursor position
            dist = np.hypot(raw_screen_x - self.prev_gaze[0], raw_screen_y - self.prev_gaze[1])

            # 1. Radial Deadzone — ignore tiny jitter movements
            if dist < deadzone:
                current_gaze = self.prev_gaze
            else:
                # 2. Dynamic Smoothing (1-Euro approximation)
                # High distance = lower alpha (more responsive)
                # Low distance  = higher alpha (more stable)
                base_smooth  = getattr(config, 'SMOOTHING_FACTOR', 0.92)
                dynamic_alpha = max(0.15, min(0.97,
                    base_smooth * (30.0 / (dist + 1e-5))))

                smoothed_x = int(self.prev_gaze[0] * dynamic_alpha
                                 + raw_screen_x * (1.0 - dynamic_alpha))
                smoothed_y = int(self.prev_gaze[1] * dynamic_alpha
                                 + raw_screen_y * (1.0 - dynamic_alpha))

                # 3. Per-frame speed clamp — prevents sudden large jumps
                move_dist = np.hypot(smoothed_x - self.prev_gaze[0],
                                     smoothed_y - self.prev_gaze[1])
                if move_dist > max_speed:
                    scale = max_speed / (move_dist + 1e-5)
                    smoothed_x = int(self.prev_gaze[0]
                                     + (smoothed_x - self.prev_gaze[0]) * scale)
                    smoothed_y = int(self.prev_gaze[1]
                                     + (smoothed_y - self.prev_gaze[1]) * scale)

                current_gaze = (smoothed_x, smoothed_y)

            self.prev_gaze = current_gaze

        return frame, current_gaze, results.multi_face_landmarks
