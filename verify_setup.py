import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import speech_recognition as sr
import tkinter as tk
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

try:
    print("Testing Imports...")
    import config
    import mediapipe
    print(f"MediaPipe File: {mediapipe.__file__}")
    print(f"MediaPipe Dir: {dir(mediapipe)}")
    from modules import tracker, blink, voice, gui
    print("Imports Successful.")

    print("Testing Initialization...")
    gaze_tracker = tracker.GazeTracker()
    print("GazeTracker Initialized.")
    
    blink_detector = blink.BlinkDetector()
    print("BlinkDetector Initialized.")
    
    voice_controller = voice.VoiceController()
    print("VoiceController Initialized.")
    
    settings_window = gui.SettingsWindow()
    print("SettingsWindow Initialized.")
    
    print("All checks passed!")
    
except Exception as e:
    print(f"Verification Failed: {e}")
    import traceback
    traceback.print_exc()
