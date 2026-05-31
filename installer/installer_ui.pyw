import customtkinter as ctk
from tkinter import filedialog
import tkinter.messagebox as messagebox
import winreg
import os
import sys
import shutil
import json
import threading
import subprocess
import time
import traceback
from datetime import datetime

# Color Palette
DARK_BG = "#212A3E"
SURFACE = "#394867"
MUTED = "#9BA4B5"
LIGHT = "#F1F6F9"
GREEN = "#4ADE80"

INSTALL_STATE_REQUIRED_KEYS = ("install_path", "exe_path", "config_path", "version", "installed_at")

def _aditus_config_dir():
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Aditus", "config")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from version import ADITUS_VERSION

DESKTOP_DEBUG_FILE = None

def _get_debug_path():
    global DESKTOP_DEBUG_FILE
    if DESKTOP_DEBUG_FILE is not None:
        return DESKTOP_DEBUG_FILE
    desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    for f in os.listdir(desktop):
        if f.endswith(".txt") and f.startswith("aditus_debug_"):
            DESKTOP_DEBUG_FILE = os.path.join(desktop, f)
            return DESKTOP_DEBUG_FILE
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    DESKTOP_DEBUG_FILE = os.path.join(desktop, f"aditus_debug_{ts}.txt")
    return DESKTOP_DEBUG_FILE

def debug_log(message):
    path = _get_debug_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class InstallerLogger:
    def __init__(self, log_path):
        self.log_path = log_path
        self.start_time = time.time()
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"--- Aditus Install Log Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            
    def log(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {message}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)
        try:
            print(line, end="")
        except:
            pass
        
    def error(self, message, exc=None):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] ERROR: {message}\n"
        if exc:
            line += traceback.format_exc() + "\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)
        try:
            print(line, end="")
        except:
            pass

    def close(self):
        duration = time.time() - self.start_time
        self.log(f"--- Install Log Finished at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        self.log(f"Total Duration: {duration:.2f} seconds")


class AditusInstaller(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=DARK_BG)
        
        self.title("Aditus Setup")
        self.geometry("1397x712")
        self.resizable(False, False)
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'aditus.ico')
        if getattr(sys, 'frozen', False):
            ico_path = os.path.join(sys._MEIPASS, 'assets', 'aditus.ico')
        if os.path.isfile(ico_path):
            self.iconbitmap(ico_path)
        self.eval('tk::PlaceWindow . center')
        
        self.bg_canvas = ctk.CTkCanvas(self, bg=DARK_BG, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.draw_dotted_background()
        
        self.card = ctk.CTkFrame(self, fg_color=DARK_BG, corner_radius=14, border_width=1, border_color=SURFACE, width=700, height=550)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.pack_propagate(False)
        
        self.current_screen = 0
        self.screens = []
        self.logger = None
        
        self.nav_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.nav_frame.pack(side="top", fill="x", pady=24)
        
        self.dots = []
        dots_container = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        dots_container.pack(expand=True)
        
        for i in range(5):
            dot = ctk.CTkLabel(dots_container, text="\u25CF", text_color=MUTED if i > 0 else LIGHT, font=("Segoe UI", 14))
            dot.pack(side="left", padx=4)
            self.dots.append(dot)
            
        self.content_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.content_frame.pack(expand=True, fill="both", padx=60, pady=10)
        
        self.build_screens()
        
        self.bottom_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.bottom_frame.pack(side="bottom", fill="x", padx=50, pady=24)
        
        self.btn_back = ctk.CTkButton(self.bottom_frame, text="\u2190", font=("Segoe UI", 16, "bold"), fg_color=SURFACE, text_color=LIGHT,
                                      hover_color=MUTED, width=44, height=36, corner_radius=8, command=self.go_back)
        self.btn_back.pack(side="left")
        
        self.btn_next = ctk.CTkButton(self.bottom_frame, text="Next", font=("Segoe UI", 14, "bold"), fg_color=LIGHT, text_color=DARK_BG,
                                      hover_color=MUTED, width=120, height=36, corner_radius=8, command=self.go_next)
        self.btn_next.pack(side="right")
        
        self.show_screen(0)

    def draw_dotted_background(self):
        for x in range(0, 1400, 28):
            for y in range(0, 750, 28):
                self.bg_canvas.create_oval(x, y, x+2, y+2, fill=SURFACE, outline="")

    def build_screens(self):
        # Frame 0: Welcome
        f0 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f0, text="ADITUS", font=("Segoe UI", 30, "bold"), text_color=LIGHT).pack(pady=(40, 5))
        ctk.CTkLabel(f0, text="Your system, on command", font=("Segoe UI", 15), text_color=MUTED).pack()
        self.screens.append(f0)
        
        # Frame 1: Choose Directory
        f1 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f1, text="Install Location", font=("Segoe UI", 22, "bold"), text_color=LIGHT).pack(anchor="w", pady=(10, 10))
        
        path_frame = ctk.CTkFrame(f1, fg_color="transparent")
        path_frame.pack(fill="x", pady=20)
        
        self.path_entry = ctk.CTkEntry(path_frame, fg_color=SURFACE, text_color=LIGHT, border_width=1, border_color=SURFACE, height=40, font=("Segoe UI", 13))
        self.path_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.path_entry.insert(0, r"C:\Program Files\Aditus")
        
        ctk.CTkButton(path_frame, text="Browse", font=("Segoe UI", 13, "bold"), fg_color=LIGHT, text_color=DARK_BG, hover_color=MUTED, width=90, height=40, corner_radius=8, command=self.browse_directory).pack(side="right")
        self.screens.append(f1)
        
        # Frame 2: Permissions
        f2 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f2, text="Permissions", font=("Segoe UI", 22, "bold"), text_color=LIGHT).pack(anchor="w", pady=(10, 20))
        
        self.mic_cb = ctk.CTkCheckBox(f2, text="Microphone Access \u2014 required for clap detection", font=("Segoe UI", 13), text_color=LIGHT, fg_color=SURFACE, border_color=MUTED, hover_color=MUTED)
        self.mic_cb.pack(anchor="w", pady=(10, 0))
        self.mic_cb.select()
        ctk.CTkLabel(f2, text="Needed to listen for audio triggers in the background.", font=("Segoe UI", 11), text_color=MUTED).pack(anchor="w", padx=30, pady=(0, 20))
        
        self.startup_cb = ctk.CTkCheckBox(f2, text="Launch on system startup \u2014 optional", font=("Segoe UI", 13), text_color=LIGHT, fg_color=SURFACE, border_color=MUTED, hover_color=MUTED)
        self.startup_cb.pack(anchor="w", pady=(10, 0))
        self.startup_cb.select()
        ctk.CTkLabel(f2, text="Automatically starts Aditus when you log into Windows.", font=("Segoe UI", 11), text_color=MUTED).pack(anchor="w", padx=30)
        
        self.shortcut_cb = ctk.CTkCheckBox(f2, text="Create desktop shortcut \u2014 optional", font=("Segoe UI", 13), text_color=LIGHT, fg_color=SURFACE, border_color=MUTED, hover_color=MUTED)
        self.shortcut_cb.pack(anchor="w", pady=(10, 0))
        self.shortcut_cb.select()
        ctk.CTkLabel(f2, text="Adds an Aditus shortcut to your desktop for quick access.", font=("Segoe UI", 11), text_color=MUTED).pack(anchor="w", padx=30)
        self.screens.append(f2)
        
        # Frame 3: Installing
        f3 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f3, text="Installing...", font=("Segoe UI", 22, "bold"), text_color=LIGHT).pack(anchor="w", pady=(20, 30))
        
        self.progress_bar = ctk.CTkProgressBar(f3, fg_color=SURFACE, progress_color=LIGHT, height=10, corner_radius=5)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(f3, text="Preparing to install...", font=("Segoe UI", 13), text_color=MUTED)
        self.status_label.pack(anchor="w", pady=10)
        self.screens.append(f3)
        
        # Frame 4: Finish
        f4 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f4, text="Aditus is Ready.", font=("Segoe UI", 30, "bold"), text_color=LIGHT).pack(pady=(40, 30))
        
        self.launch_cb = ctk.CTkCheckBox(f4, text="Launch Aditus now", font=("Segoe UI", 14), text_color=LIGHT, fg_color=SURFACE, border_color=MUTED, hover_color=MUTED)
        self.launch_cb.pack(pady=10)
        self.launch_cb.select()
        self.screens.append(f4)

    def browse_directory(self):
        selected_dir = filedialog.askdirectory(initialdir=self.path_entry.get())
        if selected_dir:
            self.path_entry.delete(0, 'end')
            self.path_entry.insert(0, selected_dir)

    def show_screen(self, index):
        if 0 <= index < len(self.screens):
            self.screens[self.current_screen].pack_forget()
            
            self.current_screen = index
            self.screens[self.current_screen].pack(expand=True, fill="both")
            
            for i, dot in enumerate(self.dots):
                dot.configure(text_color=LIGHT if i <= index else MUTED)
                
            self.btn_back.configure(state="normal" if index > 0 else "disabled")
            
            if index == 0:
                self.btn_next.configure(text="Install")
            elif index == len(self.screens) - 1:
                self.btn_next.configure(text="Finish")
                self.btn_back.pack_forget()
            else:
                self.btn_next.configure(text="Next")
                self.btn_back.pack(side="left")
                
            if index == 3:
                self.btn_back.pack_forget()
                self.btn_next.pack_forget()

    def go_back(self):
        self.show_screen(self.current_screen - 1)

    def go_next(self):
        if self.current_screen == 1:
            path = self.path_entry.get().strip()
            if not path:
                messagebox.showerror("Error", "Please select an install location.")
                return
            if not os.path.basename(path).lower() == "aditus":
                path = os.path.join(path, "Aditus")
            self.install_path = os.path.normpath(path)

        if self.current_screen == 2:
            self.mic_enabled = bool(self.mic_cb.get())
            self.startup_enabled = bool(self.startup_cb.get())
            self.shortcut_enabled = bool(self.shortcut_cb.get())
            
            self.show_screen(3)
            threading.Thread(target=self.run_install, daemon=True).start()
            
        elif self.current_screen == 4:
            self._show_launch_dialog()
        elif self.current_screen < len(self.screens) - 1:
            self.show_screen(self.current_screen + 1)

    def update_progress(self, value, status_text):
        """Thread-safe progress update via after()."""
        self.progress_bar.set(value)
        self.status_label.configure(text=status_text)

    def install_failed(self, error_msg):
        """Handle installation failure gracefully on the main thread."""
        messagebox.showerror("Installation Failed", f"An error occurred during installation:\n\n{error_msg}\n\nPlease check install.log for details.")
        self.destroy()

    def run_install(self):
        """Master installation orchestration thread."""
        try:
            self._install_create_directory()
            self._install_copy_files()
            self._install_generate_config()
            self._install_write_state()
            if self.startup_enabled:
                self._install_setup_registry()
            else:
                self._install_remove_registry()
            self._install_create_shortcut()
            self._install_validate()
            
            # Log paths to desktop debug file
            appdata_state = os.path.join(
                os.environ.get("APPDATA", ""), "Aditus", "config",
                "install_state.json"
            )
            if os.path.isfile(appdata_state):
                try:
                    with open(appdata_state) as f:
                        state = json.load(f)
                    debug_log(f"INSTALL SUCCESS: install_path={state.get('install_path')} exe_path={state.get('exe_path')} exists={os.path.isfile(state.get('exe_path',''))}")
                except Exception as e:
                    debug_log(f"INSTALL SUCCESS but failed to read state: {e}")
            else:
                debug_log("INSTALL WARNING: install_state.json not found at AppData")

            # Installation succeeded
            self.logger.close()
            self.after(0, lambda: self.update_progress(1.0, "Installation complete!"))
            time.sleep(0.4)
            self.after(0, self.install_complete)
            
        except Exception as e:
            error_msg = str(e)
            if self.logger:
                self.logger.error(f"Installation failed: {error_msg}", exc=e)
                self.logger.close()
            # Pass to main thread
            self.after(0, lambda: self.install_failed(error_msg))

    # --- Modular Installation Steps ---

    def _install_create_directory(self):
        self.after(0, lambda: self.update_progress(0.0, "Creating install directory..."))
        os.makedirs(self.install_path, exist_ok=True)
        
        # Initialize logger now that dir exists
        log_file = os.path.join(self.install_path, "install.log")
        self.logger = InstallerLogger(log_file)
        self.logger.log(f"Created install directory: {self.install_path}")
        time.sleep(0.3)

    def _install_copy_files(self):
        self.after(0, lambda: self.update_progress(0.2, "Copying application files..."))
        src_app_dir = resource_path("app")
        
        if not os.path.exists(src_app_dir):
            raise FileNotFoundError(f"Source app directory not found at: {src_app_dir}")
            
        self.logger.log(f"Recursively copying files from '{src_app_dir}' to '{self.install_path}'")
        shutil.copytree(src_app_dir, self.install_path, dirs_exist_ok=True)

        # --- Aditus.exe: try every possible source location in the bundle ---
        dest_exe = os.path.join(self.install_path, "Aditus.exe")
        src_candidates = []

        if getattr(sys, 'frozen', False):
            # Explicit datas dest='.'  →  sys._MEIPASS/Aditus.exe
            src_candidates.append(os.path.join(sys._MEIPASS, "Aditus.exe"))
            # Tree datas prefix='app'  →  sys._MEIPASS/app/Aditus.exe
            src_candidates.append(os.path.join(sys._MEIPASS, "app", "Aditus.exe"))
        else:
            src_candidates.append(os.path.join(resource_path("app"), "Aditus.exe"))

        self.logger.log("Searching for Aditus.exe in bundle:")
        chosen_src = None
        for p in src_candidates:
            exists = os.path.isfile(p)
            sz = os.path.getsize(p) if exists else 0
            self.logger.log(f"  candidate='{p}'  exists={exists}  size={sz}")
            if exists and sz > 0 and chosen_src is None:
                chosen_src = p

        if chosen_src:
            shutil.copy2(chosen_src, dest_exe)
            actual = os.path.getsize(dest_exe)
            if actual == 0:
                self.logger.log(f"copy2 produced 0 bytes — retrying with copyfile")
                os.makedirs(os.path.dirname(dest_exe), exist_ok=True)
                shutil.copyfile(chosen_src, dest_exe)
                actual = os.path.getsize(dest_exe)
            self.logger.log(f"Aditus.exe COPIED — size={actual} bytes  src='{chosen_src}' → dst='{dest_exe}'")
        else:
            if os.path.isfile(dest_exe) and os.path.getsize(dest_exe) > 0:
                self.logger.log(f"Aditus.exe already valid at dest — size={os.path.getsize(dest_exe)} bytes")
            else:
                self.logger.log("WARNING: No valid Aditus.exe found in bundle — will skip launching")

        self.logger.log("File copying completed successfully.")
        time.sleep(0.3)

    def _install_generate_config(self):
        self.after(0, lambda: self.update_progress(0.4, "Writing configuration..."))
        config = {
            "trigger": {
                "type": "clap",
                "hotkey": "ctrl+shift+j"
            },
            "clap": {
                "threshold": 15.0,
                "interval": 0.4,
                "cooldown": 5.0,
                "debounce": 0.08
            },
            "permissions": {
                "mic_enabled": self.mic_enabled,
                "startup_enabled": self.startup_enabled
            },
            "preferences": {
                "desktop_shortcut": self.shortcut_enabled
            },
            "apps": [],
            "startup": self.startup_enabled,
            "minimize_to_tray": True
        }
        config_dir = _aditus_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "aditus_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        self.logger.log(f"Configuration written to: {config_path}")
        time.sleep(0.3)

    def _install_write_state(self):
        self.after(0, lambda: self.update_progress(0.5, "Writing install state..."))
        config_dir = _aditus_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        exe_path = os.path.normpath(os.path.join(self.install_path, "Aditus.exe"))
        config_path = os.path.normpath(os.path.join(config_dir, "aditus_config.json"))
        state = {
            "install_path": self.install_path,
            "exe_path": exe_path,
            "config_path": config_path,
            "version": ADITUS_VERSION,
            "installed_at": datetime.now().isoformat(),
        }
        state_file = os.path.join(config_dir, "install_state.json")
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        self.logger.log(f"Install state written to: {state_file}")
        self.logger.log(f"  install_path={self.install_path}")
        self.logger.log(f"  exe_path={exe_path}")
        self.logger.log(f"  config_path={config_path}")
        self.logger.log(f"  version={ADITUS_VERSION}")
        debug_log(f"install_state.json written: exe_path={exe_path} version={ADITUS_VERSION} exists={os.path.isfile(exe_path)}")
        time.sleep(0.3)

    def _install_setup_registry(self):
        self.after(0, lambda: self.update_progress(0.6, "Setting up startup registry..."))
        exe_path = os.path.join(self.install_path, "Aditus.exe")

        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
        )
        winreg.SetValueEx(key, "AditusLauncher", 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        self.logger.log(f"Registry startup key set: AditusLauncher -> {exe_path}")
        time.sleep(0.3)

    def _install_remove_registry(self):
        self.after(0, lambda: self.update_progress(0.6, "Removing startup registry..."))
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
            )
            winreg.DeleteValue(key, "AditusLauncher")
            winreg.CloseKey(key)
            self.logger.log("Registry startup key removed: AditusLauncher")
        except FileNotFoundError:
            self.logger.log("No existing startup registry key to remove.")
        except Exception as e:
            self.logger.log(f"Failed to remove registry key: {e}")
        time.sleep(0.3)

    def _install_create_shortcut(self):
        if not self.shortcut_enabled:
            self.logger.log("Desktop shortcut creation skipped (disabled by user).")
            return
        self.after(0, lambda: self.update_progress(0.8, "Creating desktop shortcut..."))
        desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.isdir(desktop):
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            
        shortcut_path = os.path.join(desktop, "Aditus.lnk")
        target = os.path.normpath(os.path.join(self.install_path, "Aditus.exe"))
        working_dir = self.install_path

        ps_cmd = f'''$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('{shortcut_path}'); $s.TargetPath = '{target}'; $s.IconLocation = '{target}'; $s.WorkingDirectory = '{working_dir}'; $s.Save()'''
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"PowerShell shortcut creation failed: {result.stderr}")
            
        self.logger.log(f"Desktop shortcut created at: {shortcut_path} pointing to {target}")
        time.sleep(0.3)

    def _install_validate(self):
        self.after(0, lambda: self.update_progress(0.9, "Validating installation..."))

        # Aditus.exe in install dir
        exe_fpath = os.path.join(self.install_path, "Aditus.exe")
        if not os.path.exists(exe_fpath):
            raise FileNotFoundError(f"Validation failed: 'Aditus.exe' is missing from '{exe_fpath}'.")
        if os.path.getsize(exe_fpath) == 0:
            raise FileNotFoundError(f"Validation failed: 'Aditus.exe' is 0 bytes at '{exe_fpath}'.")

        # Config in AppData
        aditus_dir = _aditus_config_dir()
        config_fpath = os.path.join(aditus_dir, "aditus_config.json")
        if not os.path.exists(config_fpath):
            raise FileNotFoundError(f"Validation failed: 'aditus_config.json' is missing from AppData at '{config_fpath}'.")

        # State in AppData
        state_path = os.path.join(aditus_dir, "install_state.json")
        if not os.path.isfile(state_path):
            raise FileNotFoundError(f"Validation failed: install_state.json is missing at '{state_path}'.")
        try:
            with open(state_path) as f:
                state = json.load(f)
            for key in INSTALL_STATE_REQUIRED_KEYS:
                if key not in state:
                    raise ValueError(f"Validation failed: install_state.json missing required key '{key}'.")
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Validation failed: install_state.json is invalid: {e}")

        self.logger.log("Installation validation passed successfully.")
        time.sleep(0.3)

    def install_complete(self):
        """Called on the main thread when install finishes."""
        self.show_screen(4)
        self.btn_next.pack(side="right")

    def _show_launch_dialog(self):
        dialog = ctk.CTkToplevel(self, fg_color=DARK_BG)
        dialog.title("Installation Complete")
        dialog.geometry("420x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        self.update_idletasks()
        px, py = self.winfo_x(), self.winfo_y()
        pw, ph = self.winfo_width(), self.winfo_height()
        dw, dh = 420, 200
        dialog.geometry(f"{dw}x{dh}+{px + (pw - dw) // 2}+{py + (ph - dh) // 2}")

        ctk.CTkLabel(dialog, text="Installation Complete",
                     font=("Segoe UI", 18, "bold"), text_color=LIGHT
                     ).pack(pady=(30, 10))
        ctk.CTkLabel(dialog, text="Aditus has been installed successfully.",
                     font=("Segoe UI", 13), text_color=MUTED
                     ).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))

        def on_launch():
            state_path = os.path.join(_aditus_config_dir(), "install_state.json")
            exe_path = None
            version = "?"
            try:
                with open(state_path) as f:
                    state = json.load(f)
                exe_path = state.get("exe_path")
                version = state.get("version", "?")
            except Exception as e:
                debug_log(f"LAUNCH DIALOG: failed to read {state_path}: {e}")

            if not exe_path:
                debug_log("LAUNCH DIALOG: install_state.json missing 'exe_path' — cannot launch")
                dialog.destroy()
                self.destroy()
                return

            exists = os.path.isfile(exe_path)
            fsize = os.path.getsize(exe_path) if exists else 0
            debug_log(f"LAUNCH DIALOG: exe_path={exe_path} version={version} exists={exists} size={fsize}")

            try:
                with open(os.path.join(self.install_path, "install.log"), "a", encoding="utf-8") as f:
                    f.write(f"Launch check — exe_path={exe_path} version={version} exists={exists} size={fsize}\n")
            except Exception:
                pass

            if exists and fsize > 0:
                try:
                    subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
                except Exception as e:
                    debug_log(f"LAUNCH DIALOG: Popen failed: {e}")
            else:
                debug_log(f"LAUNCH DIALOG: FAILED — exe not ready")
                messagebox.showwarning("Executable Not Ready",
                                       "Aditus.exe is not ready yet.\nPlease rebuild the application binary.")
            dialog.destroy()
            self.destroy()

        def on_close():
            debug_log("LAUNCH DIALOG: user clicked Close")
            dialog.destroy()
            self.destroy()

        ctk.CTkButton(btn_frame, text="Launch Aditus", font=("Segoe UI", 13, "bold"),
                      fg_color=LIGHT, text_color=DARK_BG, hover_color=MUTED,
                      width=140, height=36, corner_radius=8, command=on_launch
                      ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Close", font=("Segoe UI", 13, "bold"),
                      fg_color=SURFACE, text_color=LIGHT, hover_color=MUTED,
                      width=140, height=36, corner_radius=8, command=on_close
                      ).pack(side="left", padx=(10, 0))

if __name__ == "__main__":
    app = AditusInstaller()
    app.mainloop()
