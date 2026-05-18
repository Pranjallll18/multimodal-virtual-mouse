import threading
import time
import config

def modifier_thread():
    time.sleep(0.5)
    print(f"Thread: Changing config value. Old: {config.CURRENT_RAW_IRIS}")
    # pyrefly: ignore [bad-assignment]
    config.CURRENT_RAW_IRIS = (100, 200)
    print(f"Thread: Changed config value. New: {config.CURRENT_RAW_IRIS}")

def main_thread():
    print(f"Main: Initial value: {config.CURRENT_RAW_IRIS}")
    t = threading.Thread(target=modifier_thread)
    t.start()
    
    time.sleep(1)
    print(f"Main: Value after thread update: {config.CURRENT_RAW_IRIS}")
    
    if config.CURRENT_RAW_IRIS == (100, 200):
        print("SUCCESS: Config state is shared.")
    else:
        print("FAILURE: Config state is NOT shared.")

if __name__ == "__main__":
    main_thread()
