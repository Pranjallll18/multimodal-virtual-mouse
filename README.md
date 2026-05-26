# Multimodal Virtual Mouse

A hands-free computing interface that lets you control your cursor with **eye gaze**, perform clicks via **eye winks**, and issue commands through **voice**. Built on MediaPipe's FaceLandmarker, it runs entirely on a standard webcam and microphone — no special hardware required.

---

## Features

### 👁️ Gaze Tracking
- Cursor follows your iris position in real-time using MediaPipe FaceLandmarker (upgraded from the deprecated FaceMesh API).
- **Non-linear power-curve mapping** (exponent 1.1) — near-linear at centre for fine control, full reach at the edges.
- **Conditional lighting normalisation** — histogram equalisation is only applied when the frame is dark, preventing flicker under good lighting.
- Dynamic smoothing + radial dead-zone + per-frame speed clamp to eliminate jitter without adding lag.
- Supports independent horizontal/vertical flip (`HORIZONTAL_FLIP`, `VERTICAL_FLIP`) and a configurable vertical centre offset.

### 😉 Blink / Wink Detection
- **Left wink → Left Click**, **Right wink → Right Click**.
- Cursor freezes during any blink so the click lands exactly where you were looking.
- EAR (Eye Aspect Ratio) is **smoothed over a 3-frame rolling buffer** — single-frame noise can no longer fire accidental clicks.
- Separate thresholds for natural blinks (`EAR_NATURAL_BLINK_THRESHOLD`) and intentional winks (`EAR_THRESHOLD_CLICK`).
- Minimum and maximum wink-frame guards: a wink must be held for ≥ 2 frames (intentional) but ≤ 12 frames (squint / sideways glance is ignored).
- Per-click cooldown prevents double-fires on slow blinkers.
- Debug overlay shows smoothed EAR values and per-eye state labels when `DEBUG = True`.

### 🎙️ Voice Control
All commands are recognised continuously in the background.

| Say this… | Action |
|---|---|
| `"open <app>"` | Launch an application |
| `"go to <url>"` / `"goto <url>"` | Open a website |
| `"search <query>"` / `"google <query>"` | Google search |
| `"scroll up/down/left/right"` | Scroll the page |
| `"left click"` / `"right click"` / `"double click"` | Mouse clicks |
| `"drag"` / `"drop"` / `"release"` | Drag and drop |
| `"type <text>"` | Type text via keyboard |
| `"press <key>"` | Press a keyboard key |
| **`"enter"` / `"press enter"` / `"submit"` / `"confirm"` / `"search"`** | **Press the Enter key (submit forms, search, log in)** |
| `"volume up/down"` / `"mute"` | Media volume |
| `"play"` / `"pause"` / `"next"` / `"previous"` | Media playback |
| `"start dictation"` / `"start typing"` | Enter dictation mode — spoken words are typed |
| `"stop dictation"` / `"stop typing"` | Exit dictation mode |

### ⚙️ Settings GUI
Real-time sliders for sensitivity, smoothing, dead-zone, speed limit, EAR thresholds, flip toggles, and eye-bounds calibration — no restart needed.

---

## Prerequisites

- Python 3.11 (the bundled PyAudio wheel targets cp311)
- Webcam
- Microphone
- Internet connection (Google Speech Recognition)

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/Pranjallll18/multimodal-virtual-mouse.git
cd multimodal-virtual-mouse
```

### 2. Download the FaceLandmarker model
```bash
python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task', 'face_landmarker.task')"
```

### 3. Create and activate a virtual environment
```powershell
# Create
python -m venv venv

# Activate (Windows PowerShell)
venv\Scripts\activate
```

### 4. Install dependencies
```powershell
# Install all packages
pip install opencv-python mediapipe pyautogui numpy protobuf SpeechRecognition screeninfo pyttsx3

# Install PyAudio from the bundled pre-built wheel (avoids build errors on Windows)
pip install PyAudio-0.2.14-cp311-cp311-win_amd64.whl
```

> **Tip:** The repository ships `PyAudio-0.2.14-cp311-cp311-win_amd64.whl` to avoid the usual C++ build requirement on Windows. If you are on a different Python version, download the matching wheel from https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio.

---

## Usage

```powershell
# With venv active:
python main.py

# Or directly without activating:
venv\Scripts\python.exe main.py
```

> **VS Code:** Press `Ctrl+Shift+P` → **Python: Select Interpreter** → choose `.\venv\Scripts\python.exe` so the editor uses the project environment.

### Tips for best results
- Sit in a well-lit environment facing the webcam directly.
- Position your face so both eyes are fully visible.
- Run a short calibration session via the Settings GUI before use.
- Enable `DEBUG = True` in `config.py` to see EAR values and eye-state overlays on the video feed while tuning thresholds.

---

## Configuration (`config.py`)

| Variable | Default | Description |
|---|---|---|
| `EAR_THRESHOLD_CLICK` | `0.18` | EAR below which a wink registers as intentional |
| `EAR_NATURAL_BLINK_THRESHOLD` | `EAR_THRESHOLD_CLICK + 0.04` | EAR threshold for detecting a natural blink (both eyes) |
| `BLINK_FRAMES` | `2` | Minimum frames a wink must be held |
| `BLINK_MAX_FRAMES` | `12` | Maximum frames before wink is treated as a squint |
| `CLICK_COOLDOWN` | `0.6` | Seconds between consecutive clicks |
| `SMOOTHING_FACTOR` | `0.72` | Base cursor smoothing (0 = raw, 1 = frozen) |
| `SENSITIVITY_X / Y` | `0.5 / 0.7` | Horizontal / vertical cursor sensitivity |
| `DEADZONE_RADIUS` | `8` | Pixel radius of jitter deadzone |
| `MAX_CURSOR_SPEED` | `160` | Max pixels cursor can jump per frame |
| `HORIZONTAL_FLIP` | `True` | Flip horizontal axis (corrects mirrored camera) |
| `VERTICAL_FLIP` | `False` | Flip vertical axis |
| `VERTICAL_CENTER_OFFSET` | `-0.10` | Shifts gaze centre to match natural forward iris position |
| `DEBUG` | `False` | Show EAR values and state labels on video feed |

---

## Project Structure

```
multimodal-virtual-mouse/
├── main.py                        # Application entry point
├── config.py                      # All tuneable constants & calibration state
├── face_landmarker.task           # MediaPipe FaceLandmarker model (download separately)
├── requirements.txt               # Python dependencies
├── PyAudio-0.2.14-cp311-...whl    # Pre-built PyAudio wheel for Windows / Python 3.11
├── calibration.json               # Saved eye-bound calibration (auto-generated)
└── modules/
    ├── tracker.py                 # Gaze tracking — FaceLandmarker API, iris ratio, smoothing
    ├── blink.py                   # Blink/wink detection — EAR smoothing, click firing
    ├── voice.py                   # Voice command recognition & dictation mode
    ├── gui.py                     # Tkinter settings panel (real-time sliders)
    └── utils.py                   # Shared helpers (TTS speak(), etc.)
```

---

## License

This project is open-source and available for educational and accessibility purposes.
