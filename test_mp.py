import mediapipe as mp
try:
    print(f"MediaPipe Version: {mp.__version__}")
    print(f"Solutions: {mp.solutions}")
    print("Success")
except AttributeError as e:
    print(f"Error: {e}")
    # Try importing solutions explicitly
    try:
        import mediapipe.python.solutions as solutions
        print(f"Explicit import success: {solutions}")
    except Exception as e2:
        print(f"Explicit import failed: {e2}")
