import sys
import os

# Add project root to sys.path to ensure modules can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import cv2
import config
from modules import tracker, blink, voice, gui

def main():
    print("Initializing Multimodal Virtual Mouse...")
    
    # improved camera setup
    cap = cv2.VideoCapture(config.CAMERA_ID)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    # Initialize Gaze Tracker
    gaze_tracker = tracker.GazeTracker()
    blink_detector = blink.BlinkDetector()
    voice_controller = voice.VoiceController()
    voice_controller.start()
    
    # Settings GUI
    settings_window = gui.SettingsWindow()
    settings_window.start()
    
    # PyAutoGUI Setup
    import pyautogui
    pyautogui.FAILSAFE = False # Disable fail-safe to prevent crashes in corners if needed, or keep True for safety
    screen_w, screen_h = pyautogui.size()
    print(f"Detected Screen Size: {screen_w}x{screen_h}")


    try:
        while True:
            success, frame = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            try:
                # Process frame for gaze tracking
                frame, gaze_point, landmarks = gaze_tracker.process_frame(frame)
            except Exception as e:
                print(f"Error processing frame: {e}")
                continue
            
            # Process blink detection FIRST (before moving cursor)
            # so we can freeze cursor position during blinks
            try:
                blink_action = blink_detector.detect_blink(frame, landmarks)

                if blink_action == "left_click":
                    print(f"Action Triggered: {blink_action}")
                    pyautogui.click()
                elif blink_action == "right_click":
                    print(f"Action Triggered: {blink_action}")
                    pyautogui.click(button='right')
            except Exception as e:
                print(f"Error in blink detection: {e}")

            # Move Mouse — but FREEZE during blinks so cursor doesn't
            # drift away from the target when the user winks to click
            if gaze_point != (0, 0) and not blink_detector.is_eyes_closing:
                # Clamp coordinates to screen size
                x = max(0, min(gaze_point[0], screen_w - 1))
                y = max(0, min(gaze_point[1], screen_h - 1))
                pyautogui.moveTo(x, y)

            # Show output with diagnostics
            if gaze_point != (0, 0):
                cv2.putText(frame, f"Gaze: {gaze_point}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Diagnostic information
            raw_iris = config.CURRENT_RAW_IRIS
            cv2.putText(frame, f"Raw Iris: ({raw_iris[0]:.0f}, {raw_iris[1]:.0f})", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            # Calibration bounds info
            cal_info = f"Cal: X[{config.EYE_LEFT_BOUND:.0f}-{config.EYE_RIGHT_BOUND:.0f}] Y[{config.EYE_TOP_BOUND:.0f}-{config.EYE_BOTTOM_BOUND:.0f}]"
            cv2.putText(frame, cal_info, (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Warning if out of calibrated range
            x_in_range = min(config.EYE_LEFT_BOUND, config.EYE_RIGHT_BOUND) <= raw_iris[0] <= max(config.EYE_LEFT_BOUND, config.EYE_RIGHT_BOUND)
            y_in_range = min(config.EYE_TOP_BOUND, config.EYE_BOTTOM_BOUND) <= raw_iris[1] <= max(config.EYE_TOP_BOUND, config.EYE_BOTTOM_BOUND)
            
            if not (x_in_range and y_in_range):
                cv2.putText(frame, "OUT OF CALIBRATED RANGE - Recalibrate!", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            cv2.imshow('Multimodal Virtual Mouse', frame)
            
            # Exit on 'q'
            if cv2.waitKey(5) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Fatal error in main loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("Cleaning up resources...")
        voice_controller.stop()
        gaze_tracker.cleanup()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
