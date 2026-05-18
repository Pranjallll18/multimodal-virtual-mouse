"""Test script for voice recognition to debug issues."""
import speech_recognition as sr
import time

def test_voice():
    print("=" * 50)
    print("VOICE RECOGNITION TEST")
    print("=" * 50)
    
    # List microphones
    try:
        mics = sr.Microphone.list_microphone_names()
        print(f"\n[1] Available microphones ({len(mics)}):")
        for i, mic in enumerate(mics[:5]):
            print(f"    {i}: {mic}")
        if len(mics) > 5:
            print(f"    ... and {len(mics) - 5} more")
    except Exception as e:
        print(f"[ERROR] Could not list microphones: {e}")
        return
    
    if not mics:
        print("[ERROR] No microphones found!")
        return
    
    # Initialize
    print("\n[2] Initializing recognizer and microphone...")
    recognizer = sr.Recognizer()
    try:
        microphone = sr.Microphone()
        print("    Microphone initialized successfully")
    except Exception as e:
        print(f"[ERROR] Could not initialize microphone: {e}")
        return
    
    # Test microphone access
    print("\n[3] Testing microphone access...")
    try:
        with microphone as source:
            print("    Calibrating for ambient noise (1 second)...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("    Calibration complete!")
            
            print("\n[4] Say something in the next 5 seconds...")
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                print("    Audio captured successfully!")
            except sr.WaitTimeoutError:
                print("    [TIMEOUT] No speech detected - but microphone IS working")
                print("    Voice command should work if you speak louder/closer")
                return
    except Exception as e:
        print(f"[ERROR] Microphone access failed: {e}")
        return
    
    # Test recognition
    print("\n[5] Testing Google Speech Recognition...")
    try:
        # pyrefly: ignore [missing-attribute]
        text = recognizer.recognize_google(audio)
        print(f"    SUCCESS! Recognized: '{text}'")
        print("\n[CONCLUSION] Voice recognition is working correctly!")
    except sr.UnknownValueError:
        print("    [WARNING] Could not understand audio")
        print("    But audio was captured - speak more clearly")
    except sr.RequestError as e:
        print(f"    [ERROR] Google API request failed: {e}")
        print("    Check your internet connection!")

if __name__ == "__main__":
    test_voice()
