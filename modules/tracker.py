import cv2
import mediapipe as mp
# Workaround for possible import issues
try:
    if not hasattr(mp, 'solutions'):
        import mediapipe.python.solutions as solutions
        mp.solutions = solutions
except ImportError:
    pass

import numpy as np
import config
from modules import utils

class GazeTracker:
    def __init__(self):
        # Initialize MediaPipe FaceMesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        # Indices for Iris landmarks (Refined FaceMesh)
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        self.LEFT_PUPIL = 468
        self.RIGHT_PUPIL = 473

        # Eye corner landmarks for relative iris tracking
        # Left eye (person's left)
        self.LEFT_EYE_OUTER = 362
        self.LEFT_EYE_INNER = 263
        self.LEFT_EYE_TOP = 386
        self.LEFT_EYE_BOTTOM = 374
        # Right eye (person's right)
        self.RIGHT_EYE_INNER = 33
        self.RIGHT_EYE_OUTER = 133
        self.RIGHT_EYE_TOP = 159
        self.RIGHT_EYE_BOTTOM = 145

        self.prev_gaze = (0, 0)
    
    def cleanup(self):
        """Properly close MediaPipe resources"""
        if hasattr(self, 'face_mesh') and self.face_mesh:
            self.face_mesh.close()

    def _get_iris_ratio(self, mesh_points):
        """Calculate iris position relative to eye corners (0.0 to 1.0).
        
        This is HEAD-MOVEMENT INDEPENDENT because both the iris and the
        eye corners move together when the head moves, so the ratio
        stays constant. Only actual eye movement changes the ratio.
        """
        ratios = []

        for pupil, corner_a, corner_b, top, bottom in [
            (self.LEFT_PUPIL, self.LEFT_EYE_OUTER, self.LEFT_EYE_INNER,
             self.LEFT_EYE_TOP, self.LEFT_EYE_BOTTOM),
            (self.RIGHT_PUPIL, self.RIGHT_EYE_INNER, self.RIGHT_EYE_OUTER,
             self.RIGHT_EYE_TOP, self.RIGHT_EYE_BOTTOM),
        ]:
            iris = mesh_points[pupil]
            ca = mesh_points[corner_a]
            cb = mesh_points[corner_b]
            tp = mesh_points[top]
            bt = mesh_points[bottom]

            # Horizontal: where is the iris between the two corners?
            left_x = min(ca[0], cb[0])
            right_x = max(ca[0], cb[0])
            eye_w = right_x - left_x
            ratio_x = (iris[0] - left_x) / eye_w if eye_w > 0 else 0.5

            # Vertical: where is the iris between top and bottom?
            top_y = min(tp[1], bt[1])
            bot_y = max(tp[1], bt[1])
            eye_h = bot_y - top_y
            ratio_y = (iris[1] - top_y) / eye_h if eye_h > 0 else 0.5

            ratios.append((ratio_x, ratio_y))

        # Average both eyes for stability
        avg_x = (ratios[0][0] + ratios[1][0]) / 2.0
        avg_y = (ratios[0][1] + ratios[1][1]) / 2.0
        return avg_x, avg_y

    def process_frame(self, frame):
        current_gaze = (0, 0)
        
        # Image Preprocessing for Lighting Robustness
        # Convert to YUV and equalize the Y channel
        img_yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
        img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
        frame_eq = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame_eq, cv2.COLOR_BGR2RGB)
        
        try:
            results = self.face_mesh.process(rgb_frame)
        except Exception as e:
            print(f"MediaPipe processing error: {e}")
            # Return safe defaults
            return frame, (0, 0), None

        # pyrefly: ignore [missing-attribute]
        if results.multi_face_landmarks:
            # pyrefly: ignore [bad-index]
            mesh_points = np.array([np.multiply([p.x, p.y], [frame.shape[1], frame.shape[0]]).astype(int) for p in results.multi_face_landmarks[0].landmark])
            
            # Visualize Iris (Just for debugging/feedback)
            cv2.circle(frame, tuple(mesh_points[self.LEFT_PUPIL]), 3, (0, 255, 0), -1)
            cv2.circle(frame, tuple(mesh_points[self.RIGHT_PUPIL]), 3, (0, 255, 0), -1)
            
            # Store raw iris position for debug/calibration overlay
            raw_x, raw_y = mesh_points[self.LEFT_PUPIL]
            config.CURRENT_RAW_IRIS = (raw_x, raw_y)

            # --- Relative Iris Tracking (head-movement independent) ---
            # Instead of using the absolute iris pixel position (which moves
            # with the head), we compute the iris position as a ratio within
            # the eye (0.0–1.0). Head movement shifts both iris AND eye
            # corners equally, so the ratio only changes with actual eye
            # movement.
            ratio_x, ratio_y = self._get_iris_ratio(mesh_points)

            # Apply horizontal flip correction (mirror camera)
            if config.HORIZONTAL_FLIP:
                ratio_x = 1.0 - ratio_x

            # Apply vertical flip if cursor Y is inverted
            if config.VERTICAL_FLIP:
                ratio_y = 1.0 - ratio_y

            # Map ratio → screen coordinates
            # The ratio center (~0.5) maps to screen center.
            # Separate X/Y multipliers because eye vertical range is
            # anatomically much narrower than horizontal.
            center_x = 0.5
            center_y = 0.5 + config.VERTICAL_CENTER_OFFSET  # shift down to compensate for iris sitting high

            offset_x = (ratio_x - center_x) * config.SENSITIVITY_X
            offset_y = (ratio_y - center_y) * config.SENSITIVITY_Y

            screen_x = int(np.clip(
                config.SCREEN_WIDTH / 2 + offset_x * config.SCREEN_WIDTH,
                0, config.SCREEN_WIDTH - 1))
            screen_y = int(np.clip(
                config.SCREEN_HEIGHT / 2 + offset_y * config.SCREEN_HEIGHT,
                0, config.SCREEN_HEIGHT - 1))

            mapped_gaze = (screen_x, screen_y)

            # Smoothing
            current_gaze = utils.smooth_coords(mapped_gaze, self.prev_gaze, config.SMOOTHING_FACTOR)
            self.prev_gaze = current_gaze
            
        return frame, current_gaze, results.multi_face_landmarks
