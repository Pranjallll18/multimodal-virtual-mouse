import speech_recognition as sr
import threading
import pyautogui
import subprocess
import os
import time
import webbrowser

class VoiceController:
    """
    Voice-controlled command system for the Multimodal Virtual Mouse.
    
    Supports:
    - App launching (Chrome, Notepad, Calculator, etc.)
    - System controls (volume, screenshot, lock, shutdown, restart)
    - Mouse actions (click, double-click, right-click, drag/drop)
    - Scrolling and typing
    - Window management (minimize, maximize, close, switch)
    - Browser navigation
    - File Explorer
    """

    # ── App registry: maps spoken names → executable paths / shell commands ──
    APP_REGISTRY = {
        # Browsers
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
        "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "microsoft edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",

        # Productivity
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "wordpad": "wordpad.exe",
        "snipping tool": "SnippingTool.exe",
        "task manager": "taskmgr.exe",
        "command prompt": "cmd.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",            # Windows Terminal
        "powershell": "powershell.exe",

        # Microsoft Office (common paths)
        "word": r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        "excel": r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
        "powerpoint": r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",

        # Media
        "vlc": r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        "spotify": os.path.join(os.environ.get("APPDATA", ""), "Spotify", "Spotify.exe"),

        # Development
        "vs code": os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe"),
        "vscode": os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe"),
        "visual studio code": os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe"),

        # System
        "settings": "ms-settings:",     # Opens Windows Settings via URI
        "control panel": "control.exe",
        "file explorer": "explorer.exe",
        "explorer": "explorer.exe",
    }

    # ── Website shortcuts ──
    WEBSITE_REGISTRY = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
        "chatgpt": "https://chat.openai.com",
        "whatsapp": "https://web.whatsapp.com",
        "instagram": "https://www.instagram.com",
        "twitter": "https://twitter.com",
        "linkedin": "https://www.linkedin.com",
        "reddit": "https://www.reddit.com",
        "amazon": "https://www.amazon.in",
        "facebook": "https://www.facebook.com",
        "netflix": "https://www.netflix.com",
        "stackoverflow": "https://stackoverflow.com",
        "stack overflow": "https://stackoverflow.com",
    }

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_listening = False
        self.thread = None

        # Check if any microphone is available
        try:
            mic_list = sr.Microphone.list_microphone_names()
            print(f"Available microphones: {mic_list}")
            
            working_index = None
            if mic_list:
                print("Testing available microphones...")
                for i, name in enumerate(mic_list):
                    try:
                        # Test if we can open the stream without error
                        test_mic = sr.Microphone(device_index=i)
                        with test_mic as source:
                            pass
                        working_index = i
                        print(f"Successfully connected to microphone [{i}]: {name}")
                        break
                    except Exception:
                        continue

            if working_index is not None:
                self.microphone = sr.Microphone(device_index=working_index)
                print("Microphone initialized successfully with working device.")
            else:
                if mic_list:
                    print("Warning: All individual tests failed. Falling back to default microphone.")
                    self.microphone = sr.Microphone()
                else:
                    print("Warning: No microphone found. Voice control disabled.")
        except Exception as e:
            print(f"Warning: Could not initialize microphone: {e}. Voice control disabled.")

    def start(self):
        if self.microphone is None:
            print("Voice control skipped: No microphone available.")
            return
        if not self.is_listening:
            self.is_listening = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            print("Voice Control Started. Listening for commands...")
            print("Say 'help' to hear available commands.")

    def stop(self):
        self.is_listening = False

    def _listen_loop(self):
        if self.microphone is None:
            print("Voice control disabled: Microphone is not available.")
            return
        
        while self.is_listening:
            try:
                with self.microphone as source:
                    # First time setup: adjust for ambient noise
                    print("Calibrating microphone for ambient noise (listening for 1 second)...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    print("Microphone calibration complete. Ready to recognize voice commands.")

                    while self.is_listening:
                        try:
                            # Listen with a short timeout to check for is_listening flag regularly
                            try:
                                audio = self.recognizer.listen(source, timeout=2.0, phrase_time_limit=5.0)
                            except sr.WaitTimeoutError:
                                # No speech detected, continue listening
                                continue

                            print("Processing audio...")

                            try:
                                # Try Google Speech Recognition
                                # pyrefly: ignore [missing-attribute]
                                command = self.recognizer.recognize_google(audio).lower()
                                print(f"Voice Command Recognized: '{command}'")
                                self._process_command(command)
                            except sr.UnknownValueError:
                                print("Could not understand audio. Please speak clearly.")
                            except sr.RequestError as e:
                                print(f"Speech Service Error: {e}. Check your internet connection.")
                                time.sleep(2)  # Wait before retrying

                        except Exception as e:
                            print(f"Voice Error: {e}")
                            time.sleep(1)
                            # Break to recreate stream if there are underlying audio issues
                            break

            except Exception as e:
                if self.is_listening:
                    print(f"Microphone Stream Error: {e}. Retrying in 3 seconds...")
                    time.sleep(3)

    # ──────────────────────────────────────────────────────────────────────
    #  Command Processing
    # ──────────────────────────────────────────────────────────────────────

    def _process_command(self, command):
        """Route voice command to the correct handler."""

        # ── 1. App launching ──
        if command.startswith("open "):
            self._handle_open(command)

        # ── 2. Website navigation ──
        elif command.startswith("go to ") or command.startswith("goto "):
            self._handle_goto(command)

        elif command.startswith("search ") or command.startswith("google "):
            self._handle_search(command)

        # ── 3. Scrolling ──
        elif "scroll up" in command:
            pyautogui.scroll(300)
            print("↑ Scrolling up...")
        elif "scroll down" in command:
            pyautogui.scroll(-300)
            print("↓ Scrolling down...")
        elif "scroll left" in command:
            pyautogui.hscroll(-300)
            print("← Scrolling left...")
        elif "scroll right" in command:
            pyautogui.hscroll(300)
            print("→ Scrolling right...")

        # ── 4. Mouse clicks ──
        elif "double click" in command:
            pyautogui.click(clicks=2)
            print("Double click executed")
        elif "right click" in command:
            pyautogui.click(button='right')
            print("Right click executed")
        elif "left click" in command or command == "click":
            pyautogui.click()
            print("Left click executed")
        elif "middle click" in command:
            pyautogui.click(button='middle')
            print("Middle click executed")

        # ── 5. Drag & Drop ──
        elif "drag" in command:
            pyautogui.mouseDown()
            print("🖱 Dragging... (say 'drop' or 'release' to stop)")
        elif "drop" in command or "release" in command:
            pyautogui.mouseUp()
            print("🖱 Released / Dropped")

        # ── 6. Typing ──
        elif command.startswith("type "):
            text = command[5:].strip()
            if text:
                pyautogui.write(text, interval=0.03)
                print(f"⌨ Typed: {text}")
        elif command.startswith("press "):
            self._handle_press(command)

        # ── 7. Volume controls ──
        elif "volume up" in command or "increase volume" in command:
            pyautogui.press('volumeup', presses=5)
            print("🔊 Volume Up")
        elif "volume down" in command or "decrease volume" in command:
            pyautogui.press('volumedown', presses=5)
            print("🔉 Volume Down")
        elif "mute" in command or "unmute" in command:
            pyautogui.press('volumemute')
            print("🔇 Mute/Unmute toggled")

        # ── 8. Media controls ──
        elif "play" in command or "pause" in command:
            pyautogui.press('playpause')
            print("⏯ Play/Pause toggled")
        elif "next track" in command or "next song" in command:
            pyautogui.press('nexttrack')
            print("⏭ Next track")
        elif "previous track" in command or "previous song" in command:
            pyautogui.press('prevtrack')
            print("⏮ Previous track")

        # ── 9. Screenshot ──
        elif "screenshot" in command or "take screenshot" in command:
            self._handle_screenshot()

        # ── 10. Window management ──
        elif "minimize" in command or "minimise" in command:
            pyautogui.hotkey('win', 'down')
            print("⬇ Window minimized")
        elif "maximize" in command or "maximise" in command:
            pyautogui.hotkey('win', 'up')
            print("⬆ Window maximized")
        elif "close window" in command or "close tab" in command:
            pyautogui.hotkey('alt', 'F4')
            print("✖ Window closed")
        elif "close" in command and "tab" not in command:
            pyautogui.hotkey('alt', 'F4')
            print("✖ Window closed")
        elif "switch window" in command or "alt tab" in command:
            pyautogui.hotkey('alt', 'tab')
            print("🔄 Switched window")
        elif "new tab" in command:
            pyautogui.hotkey('ctrl', 't')
            print("New tab opened")
        elif "close tab" in command:
            pyautogui.hotkey('ctrl', 'w')
            print("Tab closed")

        # ── 11. System commands ──
        elif "lock" in command and ("screen" in command or "computer" in command or "pc" in command or command.strip() == "lock"):
            self._handle_lock()
        elif "shutdown" in command or "shut down" in command:
            self._handle_shutdown()
        elif "restart" in command or "reboot" in command:
            self._handle_restart()
        elif "sleep" in command and ("computer" in command or "pc" in command or "system" in command):
            self._handle_sleep()

        # ── 12. Clipboard shortcuts ──
        elif "copy" in command and "that" not in command:
            pyautogui.hotkey('ctrl', 'c')
            print("📋 Copied")
        elif "paste" in command:
            pyautogui.hotkey('ctrl', 'v')
            print("📋 Pasted")
        elif "cut" in command:
            pyautogui.hotkey('ctrl', 'x')
            print("✂ Cut")
        elif "undo" in command:
            pyautogui.hotkey('ctrl', 'z')
            print("↩ Undo")
        elif "redo" in command:
            pyautogui.hotkey('ctrl', 'y')
            print("↪ Redo")
        elif "select all" in command:
            pyautogui.hotkey('ctrl', 'a')
            print("Selected all")
        elif "save" in command:
            pyautogui.hotkey('ctrl', 's')
            print("💾 Saved")

        # ── 13. Navigation shortcuts ──
        elif "go back" in command or "back" == command.strip():
            pyautogui.hotkey('alt', 'left')
            print("◀ Back")
        elif "go forward" in command or "forward" == command.strip():
            pyautogui.hotkey('alt', 'right')
            print("▶ Forward")
        elif "refresh" in command or "reload" in command:
            pyautogui.press('f5')
            print("🔄 Refreshed")
        elif "home" == command.strip():
            pyautogui.press('home')
            print("Home")
        elif "end" == command.strip():
            pyautogui.press('end')
            print("End")

        # ── 14. Show desktop ──
        elif "show desktop" in command or "desktop" == command.strip():
            pyautogui.hotkey('win', 'd')
            print("🖥 Showing desktop")

        # ── 15. Keyboard escape ──
        elif "escape" in command or "cancel" in command:
            pyautogui.press('escape')
            print("⎋ Escape pressed")
        elif "enter" == command.strip():
            pyautogui.press('enter')
            print("↵ Enter pressed")
        elif "tab" == command.strip():
            pyautogui.press('tab')
            print("⇥ Tab pressed")

        # ── 16. Stop / Exit (voice controller) ──
        elif "stop" in command or "exit" in command or "quit" in command:
            print("🛑 Stop command received.")

        # ── 17. Help ──
        elif "help" in command:
            self._print_help()

        else:
            print(f"❓ Unknown command: '{command}'")
            print("   Say 'help' to see available commands.")

    # ──────────────────────────────────────────────────────────────────────
    #  Handlers
    # ──────────────────────────────────────────────────────────────────────

    def _handle_open(self, command):
        """Open an application or website by name."""
        app_name = command.replace("open", "", 1).strip()
        if not app_name:
            print("Please specify what to open. Example: 'open chrome'")
            return

        # Check website registry first (e.g., "open youtube")
        if app_name in self.WEBSITE_REGISTRY:
            url = self.WEBSITE_REGISTRY[app_name]
            print(f"🌐 Opening {app_name} → {url}")
            webbrowser.open(url)
            return

        # Check app registry
        if app_name in self.APP_REGISTRY:
            exe_path = self.APP_REGISTRY[app_name]
            print(f"🚀 Opening {app_name}...")
            try:
                # Handle Windows URI schemes (e.g., ms-settings:)
                if exe_path.endswith(":"):
                    os.startfile(exe_path)
                elif os.path.exists(exe_path):
                    subprocess.Popen(exe_path, shell=False)
                else:
                    # Try running it as a system command (for executables on PATH)
                    subprocess.Popen(exe_path, shell=True)
                print(f"✅ {app_name} opened successfully!")
            except FileNotFoundError:
                print(f"❌ Could not find {app_name} at: {exe_path}")
                print("   Falling back to Start Menu search...")
                self._fallback_open(app_name)
            except Exception as e:
                print(f"❌ Error opening {app_name}: {e}")
                self._fallback_open(app_name)
            return

        # Fallback: use Windows Start Menu search
        print(f"🔍 '{app_name}' not in registry. Searching via Start Menu...")
        self._fallback_open(app_name)

    def _fallback_open(self, app_name):
        """Fallback: open an app by searching in Windows Start Menu."""
        try:
            pyautogui.press('win')
            time.sleep(0.5)
            pyautogui.write(app_name, interval=0.05)
            time.sleep(1.0)  # Wait for search results
            pyautogui.press('enter')
            print(f"✅ Launched '{app_name}' via Start Menu search.")
        except Exception as e:
            print(f"❌ Fallback launch also failed: {e}")

    def _handle_goto(self, command):
        """Open a website URL in the browser."""
        site = command.replace("go to", "").replace("goto", "").strip()
        if not site:
            print("Please specify a website. Example: 'go to youtube'")
            return

        # Check website registry
        if site in self.WEBSITE_REGISTRY:
            url = self.WEBSITE_REGISTRY[site]
        elif "." in site:
            # Looks like a domain
            url = f"https://{site}" if not site.startswith("http") else site
        else:
            url = f"https://www.{site}.com"

        print(f"🌐 Navigating to: {url}")
        webbrowser.open(url)

    def _handle_search(self, command):
        """Search Google for a query."""
        query = command.replace("search", "").replace("google", "").strip()
        if query:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            print(f"🔍 Searching Google for: '{query}'")
            webbrowser.open(url)
        else:
            print("Please specify what to search. Example: 'search python tutorials'")

    def _handle_press(self, command):
        """Handle 'press <key>' commands."""
        key = command.replace("press", "").strip()
        key_map = {
            "enter": "enter",
            "space": "space",
            "backspace": "backspace",
            "delete": "delete",
            "escape": "escape",
            "tab": "tab",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
            "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
            "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
        }
        if key in key_map:
            pyautogui.press(key_map[key])
            print(f"⌨ Pressed: {key}")
        else:
            print(f"❓ Unknown key: '{key}'")

    def _handle_screenshot(self):
        """Take a screenshot and save it to the Desktop."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = f"screenshot_{int(time.time())}.png"
            filepath = os.path.join(desktop, filename)
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            print(f"📸 Screenshot saved to: {filepath}")
        except Exception as e:
            print(f"❌ Screenshot failed: {e}")

    def _handle_lock(self):
        """Lock the computer."""
        print("🔒 Locking computer...")
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        except Exception as e:
            print(f"❌ Could not lock: {e}")

    def _handle_shutdown(self):
        """Shutdown the computer (with 30-second delay for safety)."""
        print("⚠ Shutting down in 30 seconds... Say 'cancel' to abort.")
        print("   To cancel: run 'shutdown /a' in command prompt.")
        try:
            subprocess.Popen("shutdown /s /t 30", shell=True)
        except Exception as e:
            print(f"❌ Shutdown failed: {e}")

    def _handle_restart(self):
        """Restart the computer (with 30-second delay for safety)."""
        print("⚠ Restarting in 30 seconds... Say 'cancel' to abort.")
        print("   To cancel: run 'shutdown /a' in command prompt.")
        try:
            subprocess.Popen("shutdown /r /t 30", shell=True)
        except Exception as e:
            print(f"❌ Restart failed: {e}")

    def _handle_sleep(self):
        """Put the computer to sleep."""
        print("💤 Putting computer to sleep...")
        try:
            subprocess.Popen("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
        except Exception as e:
            print(f"❌ Sleep failed: {e}")

    def _print_help(self):
        """Print all available voice commands."""
        help_text = """
╔══════════════════════════════════════════════════════════════╗
║                  🎙 VOICE COMMANDS HELP                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  📂 APP LAUNCHING                                            ║
║    "open chrome"        - Open Google Chrome                 ║
║    "open notepad"       - Open Notepad                       ║
║    "open calculator"    - Open Calculator                    ║
║    "open file explorer" - Open File Explorer                 ║
║    "open vs code"       - Open VS Code                       ║
║    "open settings"      - Open Windows Settings              ║
║    "open task manager"  - Open Task Manager                  ║
║    "open [app name]"    - Search & open any app              ║
║                                                              ║
║  🌐 WEBSITES                                                 ║
║    "open youtube"       - Open YouTube                       ║
║    "open google"        - Open Google                        ║
║    "open gmail"         - Open Gmail                         ║
║    "open github"        - Open GitHub                        ║
║    "go to [website]"    - Navigate to any website            ║
║    "search [query]"     - Google search                      ║
║                                                              ║
║  🖱 MOUSE CONTROLS                                           ║
║    "click" / "left click"   - Left click                     ║
║    "right click"            - Right click                     ║
║    "double click"           - Double click                    ║
║    "middle click"           - Middle click                    ║
║    "drag" / "drop"          - Drag and drop                  ║
║                                                              ║
║  📜 SCROLLING                                                ║
║    "scroll up" / "scroll down"                               ║
║    "scroll left" / "scroll right"                            ║
║                                                              ║
║  ⌨ TYPING & KEYS                                             ║
║    "type [text]"        - Type text                          ║
║    "press enter"        - Press Enter key                    ║
║    "press [key]"        - Press any key                      ║
║                                                              ║
║  🔊 VOLUME & MEDIA                                           ║
║    "volume up" / "volume down"                               ║
║    "mute" / "unmute"                                         ║
║    "play" / "pause"                                          ║
║    "next track" / "previous track"                           ║
║                                                              ║
║  🪟 WINDOW MANAGEMENT                                        ║
║    "minimize" / "maximize"                                   ║
║    "close window"       - Close current window               ║
║    "switch window"      - Alt+Tab                            ║
║    "new tab" / "close tab"                                   ║
║    "show desktop"                                            ║
║                                                              ║
║  📋 CLIPBOARD                                                ║
║    "copy" / "paste" / "cut"                                  ║
║    "undo" / "redo"                                           ║
║    "select all" / "save"                                     ║
║                                                              ║
║  🔄 NAVIGATION                                               ║
║    "go back" / "go forward"                                  ║
║    "refresh" / "reload"                                      ║
║                                                              ║
║  📸 SYSTEM                                                   ║
║    "screenshot"         - Save screenshot to Desktop         ║
║    "lock"               - Lock computer                      ║
║    "shutdown"           - Shutdown (30s delay)               ║
║    "restart"            - Restart (30s delay)                ║
║    "sleep computer"     - Put PC to sleep                    ║
║                                                              ║
║  🛑 CONTROL                                                  ║
║    "stop" / "exit"      - Stop voice controller              ║
║    "help"               - Show this help                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(help_text)
