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

# Color Palette
DARK_BG = "#212A3E"
SURFACE = "#394867"
MUTED = "#9BA4B5"
LIGHT = "#F1F6F9"

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller frozen exe """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Development mode: assume we are in installer/ and root is one level up
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class InstallerLogger:
    def __init__(self, log_path):
        self.log_path = log_path
        self.start_time = time.time()
        # Initialize log file
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(f"--- Aditus Install Log Started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            
    def log(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] {message}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)
        print(line, end="")
        
    def error(self, message, exc=None):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{timestamp}] ERROR: {message}\n"
        if exc:
            line += traceback.format_exc() + "\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)
        print(line, end="")

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
        self.eval('tk::PlaceWindow . center')
        
        self.bg_canvas = ctk.CTkCanvas(self, bg=DARK_BG, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.draw_dotted_background()
        
        self.card = ctk.CTkFrame(self, fg_color=DARK_BG, corner_radius=20, border_width=2, border_color=SURFACE, width=700, height=550)
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.pack_propagate(False)
        
        self.current_screen = 0
        self.screens = []
        self.logger = None
        
        self.nav_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.nav_frame.pack(side="top", fill="x", pady=30)
        
        self.dots = []
        dots_container = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        dots_container.pack(expand=True)
        
        for i in range(5):
            dot = ctk.CTkLabel(dots_container, text="●", text_color=MUTED if i > 0 else LIGHT, font=("Arial", 20))
            dot.pack(side="left", padx=5)
            self.dots.append(dot)
            
        self.content_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.content_frame.pack(expand=True, fill="both", padx=60, pady=10)
        
        self.build_screens()
        
        self.bottom_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        self.bottom_frame.pack(side="bottom", fill="x", padx=60, pady=30)
        
        self.btn_back = ctk.CTkButton(self.bottom_frame, text="←", font=("Arial", 20, "bold"), fg_color=SURFACE, text_color=LIGHT, 
                                     hover_color=MUTED, width=50, command=self.go_back)
        self.btn_back.pack(side="left")
        
        self.btn_next = ctk.CTkButton(self.bottom_frame, text="Next", font=("Arial", 14, "bold"), fg_color=LIGHT, text_color=DARK_BG, 
                                     hover_color=MUTED, width=120, height=35, command=self.go_next)
        self.btn_next.pack(side="right")
        
        self.show_screen(0)

    def draw_dotted_background(self):
        for x in range(0, 1400, 30):
            for y in range(0, 750, 30):
                self.bg_canvas.create_oval(x, y, x+3, y+3, fill=SURFACE, outline="")

    def build_screens(self):
        # Frame 0: Welcome
        f0 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f0, text="ADITUS", font=("Arial", 54, "bold"), text_color=LIGHT).pack(pady=(20, 5))
        ctk.CTkLabel(f0, text="Your system, on command", font=("Arial", 18), text_color=MUTED).pack()
        self.screens.append(f0)
        
        # Frame 1: Choose Directory
        f1 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f1, text="Install Location", font=("Arial", 28, "bold"), text_color=LIGHT).pack(anchor="w", pady=(10, 10))
        
        path_frame = ctk.CTkFrame(f1, fg_color="transparent")
        path_frame.pack(fill="x", pady=20)
        
        self.path_entry = ctk.CTkEntry(path_frame, fg_color=SURFACE, text_color=LIGHT, border_width=0, height=40, font=("Arial", 14))
        self.path_entry.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.path_entry.insert(0, r"C:\Program Files\Aditus")
        
        ctk.CTkButton(path_frame, text="Browse", font=("Arial", 14), fg_color=SURFACE, text_color=LIGHT, hover_color=MUTED, width=90, height=40, command=self.browse_directory).pack(side="right")
        self.screens.append(f1)
        
        # Frame 2: Permissions
        f2 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f2, text="Permissions", font=("Arial", 28, "bold"), text_color=LIGHT).pack(anchor="w", pady=(10, 20))
        
        self.mic_cb = ctk.CTkCheckBox(f2, text="Microphone Access — required for clap detection", font=("Arial", 14), text_color=LIGHT, fg_color=SURFACE, border_color=MUTED)
        self.mic_cb.pack(anchor="w", pady=(10, 0))
        self.mic_cb.select()
        ctk.CTkLabel(f2, text="Needed to listen for audio triggers in the background.", font=("Arial", 12), text_color=MUTED).pack(anchor="w", padx=30, pady=(0, 20))
        
        self.startup_cb = ctk.CTkCheckBox(f2, text="Launch on system startup — optional", font=("Arial", 14), text_color=LIGHT, fg_color=SURFACE, border_color=MUTED)
        self.startup_cb.pack(anchor="w", pady=(10, 0))
        self.startup_cb.select()
        ctk.CTkLabel(f2, text="Automatically starts Aditus when you log into Windows.", font=("Arial", 12), text_color=MUTED).pack(anchor="w", padx=30)
        self.screens.append(f2)
        
        # Frame 3: Installing
        f3 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f3, text="Installing...", font=("Arial", 28, "bold"), text_color=LIGHT).pack(anchor="w", pady=(20, 30))
        
        self.progress_bar = ctk.CTkProgressBar(f3, fg_color=SURFACE, progress_color=LIGHT, height=18)
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(f3, text="Preparing to install...", font=("Arial", 14), text_color=MUTED)
        self.status_label.pack(anchor="w", pady=10)
        self.screens.append(f3)
        
        # Frame 4: Finish
        f4 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctk.CTkLabel(f4, text="Aditus is Ready.", font=("Arial", 42, "bold"), text_color=LIGHT).pack(pady=(30, 30))
        
        self.launch_cb = ctk.CTkCheckBox(f4, text="Launch Aditus now", font=("Arial", 16), text_color=LIGHT, fg_color=SURFACE, border_color=MUTED)
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
            self.install_path = path

        if self.current_screen == 2:
            self.mic_enabled = bool(self.mic_cb.get())
            self.startup_enabled = bool(self.startup_cb.get())
            
            self.show_screen(3)
            threading.Thread(target=self.run_install, daemon=True).start()
            
        elif self.current_screen == 4:
            if self.launch_cb.get():
                exe_path = os.path.join(self.install_path, "Aditus.exe")
                if os.path.exists(exe_path):
                    try:
                        subprocess.Popen([exe_path])
                    except Exception as e:
                        messagebox.showwarning("Launch Error", f"Failed to launch Aditus:\n{e}")
                else:
                    messagebox.showwarning("Warning", "Aditus.exe not found in install directory. Cannot launch.")
            self.destroy()
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
            if self.startup_enabled:
                self._install_setup_registry()
            self._install_create_shortcut()
            self._install_validate()
            
            # Installation succeeded
            self.logger.close()
            self.after(0, lambda: self.update_progress(1.0, "Installation complete!"))
            time.sleep(0.4)
            self.after(0, self.install_complete)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Installation failed: {e}", exc=e)
                self.logger.close()
            # Pass to main thread
            self.after(0, lambda: self.install_failed(str(e)))

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
            "apps": []
        }
        config_path = os.path.join(self.install_path, "aditus_config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        self.logger.log(f"Configuration written to: {config_path}")
        time.sleep(0.3)

    def _install_setup_registry(self):
        self.after(0, lambda: self.update_progress(0.6, "Setting up startup registry..."))
        exe_path = os.path.join(self.install_path, "Aditus.exe")
        
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "AditusLauncher", 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        self.logger.log(f"Registry startup key set: AditusLauncher -> {exe_path}")
        time.sleep(0.3)

    def _install_create_shortcut(self):
        self.after(0, lambda: self.update_progress(0.8, "Creating desktop shortcut..."))
        desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
        if not os.path.isdir(desktop):
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            
        shortcut_path = os.path.join(desktop, "Aditus.lnk")
        target = os.path.join(self.install_path, "Aditus.exe")
        working_dir = self.install_path

        ps_cmd = f'''$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('{shortcut_path}'); $s.TargetPath = '{target}'; $s.WorkingDirectory = '{working_dir}'; $s.Save()'''
        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"PowerShell shortcut creation failed: {result.stderr}")
            
        self.logger.log(f"Desktop shortcut created at: {shortcut_path} pointing to {target}")
        time.sleep(0.3)

    def _install_validate(self):
        self.after(0, lambda: self.update_progress(0.9, "Validating installation..."))
        required_files = ["aditus_config.json"]
        
        for rf in required_files:
            fpath = os.path.join(self.install_path, rf)
            if not os.path.exists(fpath):
                raise FileNotFoundError(f"Validation failed: Critical file '{rf}' is missing from the installation directory.")
                
        self.logger.log("Installation validation passed successfully.")
        time.sleep(0.3)

    def install_complete(self):
        """Called on the main thread when install finishes."""
        self.show_screen(4)
        
        # If Aditus.exe is missing, gracefully disable the checkbox
        if not os.path.exists(os.path.join(self.install_path, "Aditus.exe")):
            self.launch_cb.deselect()
            self.launch_cb.configure(state="disabled", text="Launch Aditus now (Executable missing)")
            
        self.btn_next.pack(side="right")

if __name__ == "__main__":
    app = AditusInstaller()
    app.mainloop()
