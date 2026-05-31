# Aditus Launcher

A clap-triggered app launcher for Windows

## What it does
Aditus Launcher is a power-user dashboard that allows launching applications via clap detection, hotkeys, or manual triggers. It provides a multi-page interface for managing apps, viewing activity logs, and configuring settings.

## Features
- Clap-triggered application launching
- Hotkey-based triggering (customizable)
- Manual trigger via UI
- System tray integration
- Application management dashboard
- Activity logging
- Startup launch capability
- Minimize to system tray
- Configurable trigger sensitivity

## Installation
1. Download the latest release from GitHub
2. Run AditusSetup.exe to install
3. The launcher will be available from your desktop shortcut or start menu

## How to use
- Launch Aditus Launcher from desktop shortcut
- By default, clap twice to launch your configured applications
- Use the dashboard to manage applications and view activity
- Access settings via the gear icon to configure triggers, hotkeys, and behavior
- The application minimizes to system tray when closed (if enabled)

## Build from source
To build the launcher from source code:

1. Install dependencies:
    ```
    pip install -r requirements.txt
    ```

2. Build the application executables in this exact order:
    Step 1 — Build the main app exe:
      pyinstaller Aditus.spec --distpath app --workpath build\Aditus_app --clean --noconfirm

    Step 2 — Copy to dist:
      Copy-Item app\Aditus.exe dist\Aditus.exe -Force

    Step 3 — Build the installer:
      pyinstaller AditusSetup.spec --clean --noconfirm

3. The built executables will be available in the `dist/` folder

## Project structure
- `app/` - Main application source code
- `assets/` - Application icons and images
- `build/` - PyInstaller build artifacts
- `dist/` - Compiled executables
- `installer/` - Custom installer UI
- `dev/` - Debug and test scripts (not part of production)