# Multimodal Virtual Mouse

A Multimodal Virtual Mouse application that allows users to control their computer cursor using gaze tracking, perform clicks via blink detection, and execute commands using voice control. This project aims to provide an accessible and hands-free computing experience.

## Features

- **Gaze Tracking:** Control your mouse cursor simply by looking at the screen. Uses MediaPipe for robust facial landmark and iris detection.
- **Blink Detection:** 
  - Wink left eye to trigger a Left Click.
  - Wink right eye to trigger a Right Click.
  - Automatically freezes cursor during blinks to prevent drift.
- **Voice Control:** Issue voice commands to control actions or launch applications.
- **Settings GUI:** Easily adjust sensitivity, smoothing factors, and calibrate eye-tracking bounds in real-time.

## Prerequisites

- Python 3.8+
- Webcam
- Microphone

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Pranjallll18/multimodal-virtual-mouse.git
   cd multimodal-virtual-mouse
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *Note: For Windows users, `pyaudio` might require additional setup or can be installed via pre-built wheels if you face compilation issues.*

## Usage

Run the main application script:

```bash
python main.py
```

### Calibration and Usage Tips

- Make sure your face is well-lit and clearly visible to the webcam.
- **Settings Window:** Use the Settings GUI to calibrate your `EYE_LEFT_BOUND`, `EYE_RIGHT_BOUND`, `EYE_TOP_BOUND`, and `EYE_BOTTOM_BOUND` for accurate mapping of your eye movements to your screen size.
- **To click:** Perform an exaggerated wink with your left or right eye. The cursor will freeze temporarily while blinking to ensure the click happens exactly where you were looking.
- **To exit:** Press `q` while focused on the webcam feed window, or use the Settings GUI.

## Project Structure

- `main.py`: Entry point of the application.
- `config.py`: Central configuration for thresholds, sensitivities, and calibration settings.
- `modules/tracker.py`: Gaze tracking implementation using MediaPipe.
- `modules/blink.py`: Blink detection logic based on Eye Aspect Ratio (EAR).
- `modules/voice.py`: Voice command recognition.
- `modules/gui.py`: Tkinter-based settings interface for real-time adjustments.

## License

This project is open-source and available for educational and accessibility purposes.
