# Aditus Launcher

> Your system, on command.

Aditus is a power-user app launcher for Windows. Clap twice, press a hotkey, or click a button — and your configured apps launch instantly.

---

## What It Does

- Double-clap detection using your microphone
- Custom hotkey trigger (fully remappable)
- Manual launch from the dashboard
- System tray integration — always running, never in the way
- Configurable sensitivity for clap detection
- Add, edit, and remove apps from a clean UI
- Activity log for every trigger and launch event

---

## Project Structure

aditus-launcher/
├── app/                    # Main application source
│   ├── main.pyw            # Entry point (multi-page UI)
│   ├── version.py          # Version constant
│   ├── config/
│   │   ├── config_manager.py
│   │   └── aditus_config.json
│   └── runtime/
│       ├── runtime_engine.py
│       ├── app_launcher.py
│       ├── clap_detector.py
│       ├── event_queue.py
│       ├── trigger_integration.py
│       ├── single_instance.py
│       └── system_tray.py
├── assets/
│   └── aditus.ico          # App icon
├── installer/
│   └── installer_ui.pyw    # Installer wizard UI
├── Aditus.spec             # PyInstaller spec — main app
├── AditusSetup.spec        # PyInstaller spec — installer
├── requirements.txt
└── README.md

---

## How to Run (Installed)

1. Download and run AditusSetup.exe
2. Follow the installer wizard
3. Launch Aditus from the desktop shortcut
4. Configure your apps in the Apps tab
5. Set your trigger in Settings (Clap / Hotkey / Manual)
6. Double-clap or press your hotkey to launch

---

## How to Build from Source

Install dependencies:

pip install -r requirements.txt

Build in this exact order:

Step 1 — Build the main app:

pyinstaller Aditus.spec --distpath app --workpath build\Aditus_app --clean --noconfirm

Step 2 — Copy to dist:

Copy-Item app\Aditus.exe dist\Aditus.exe -Force

Step 3 — Build the installer:

pyinstaller AditusSetup.spec --clean --noconfirm

The installer will be at dist\AditusSetup.exe

---

## Requirements

- Windows 10/11
- Microphone (for clap detection)
- No Python installation needed for end users

---

## Notes

- Config is stored at: %APPDATA%\Aditus\config\aditus_config.json
- Debug log is written to your Desktop as aditus_debug_*.txt
- The app runs as a single instance — launching twice brings the existing window to focus
