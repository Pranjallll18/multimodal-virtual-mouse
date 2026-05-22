import numpy as np
import pyttsx3
import queue
import threading

# Thread-safe speech queue and worker
_speech_queue = queue.Queue()

def _speaker_thread():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        while True:
            text = _speech_queue.get()
            if text is None:
                break
            engine.say(text)
            engine.runAndWait()
            _speech_queue.task_done()
    except Exception as e:
        print(f"TTS Thread Exception: {e}")

# Start the speech engine background thread
threading.Thread(target=_speaker_thread, daemon=True).start()

def speak(text):
    """Asynchronously speak a text string using TTS without blocking."""
    _speech_queue.put(text)

def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def smooth_coords(current, previous, factor):
    """
    Apply velocity-based adaptive smoothing.
    If the cursor moves a very short distance (user trying to focus/click),
    we increase the smoothing heavily to block jitter.
    If the cursor moves a large distance, we reduce smoothing for responsiveness.
    """
    if previous == (0, 0):
        return current
    
    # Calculate screen distance moved
    dx = current[0] - previous[0]
    dy = current[1] - previous[1]
    dist = (dx**2 + dy**2)**0.5
    
    # Adaptive factor selection
    if dist < 8.0:
        # High smoothing for tiny jitter/stable hovering
        adaptive_factor = 0.96
    elif dist < 30.0:
        # Balanced smoothing for precise adjustments
        adaptive_factor = 0.85
    elif dist < 120.0:
        # Standard responsive smoothing
        adaptive_factor = 0.65
    else:
        # Low smoothing for immediate travel across screen
        adaptive_factor = 0.35
        
    x = previous[0] * adaptive_factor + current[0] * (1 - adaptive_factor)
    y = previous[1] * adaptive_factor + current[1] * (1 - adaptive_factor)
    return (int(x), int(y))

