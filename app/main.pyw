#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Aditus — Power-user Launcher Dashboard (Multi-page)

Design reference : aditus_launcher_dark_powerful.html
Pages            : Dashboard | Apps | Activity | Settings
Runtime          : RuntimeEngine + EventQueue + AppLauncher
"""

from __future__ import annotations

import ctypes
import sys as _sys

try:
    if _sys.platform == "win32":
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import atexit
import json
import os
import signal
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any, Dict, List, Optional
from datetime import datetime

import customtkinter as ctk

# ── Install state — single source of truth for ALL paths ────────────────
# NO fallback, NO guessing.  If install_state.json is missing we hard-fail.

INSTALL_STATE_PATH = None
INSTALL_STATE = {}
INSTALL_STATE_REQUIRED_KEYS = ("install_path", "exe_path", "config_path", "version", "installed_at")

# ── Desktop debug log (single file, appended every run) ─────────────────
# Defined early so _find_install_state and all downstream code can use it.

_DESKTOP_DEBUG_FILE = None

def _get_debug_path():
    global _DESKTOP_DEBUG_FILE
    if _DESKTOP_DEBUG_FILE is not None:
        return _DESKTOP_DEBUG_FILE
    desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    for f in os.listdir(desktop):
        if f.endswith(".txt") and f.startswith("aditus_debug_"):
            _DESKTOP_DEBUG_FILE = os.path.join(desktop, f)
            return _DESKTOP_DEBUG_FILE
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    _DESKTOP_DEBUG_FILE = os.path.join(desktop, f"aditus_debug_{ts}.txt")
    return _DESKTOP_DEBUG_FILE

def debug_log(message):
    path = _get_debug_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


def _setup_runtime_logging():
    """Route all aditus.* logger output to a rotating file in AppData\\Aditus\\logs."""
    import logging
    from logging.handlers import RotatingFileHandler

    log_dir = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")), "Aditus", "logs",
    )
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "aditus.log")

    try:
        handler = RotatingFileHandler(
            log_path,
            mode="a",
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("[%(asctime)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        root = logging.getLogger("aditus")
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
    except Exception:
        pass


_setup_runtime_logging()

def _find_install_state():
    global INSTALL_STATE_PATH, INSTALL_STATE
    appdata_candidate = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "Aditus", "config", "install_state.json",
    )
    candidates = [appdata_candidate]
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, "install_state.json"))
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(script_dir, "install_state.json"))
    for p in candidates:
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    INSTALL_STATE = json.load(f)
                INSTALL_STATE_PATH = p
                for key in INSTALL_STATE_REQUIRED_KEYS:
                    if key not in INSTALL_STATE:
                        raise ValueError(f"install_state.json missing required key '{key}'")
                return
            except Exception as e:
                debug_log(f"FATAL: {p} is invalid: {e}")
                print(f"FATAL: {p} is invalid: {e}", file=sys.stderr)
                sys.exit(1)
    msg = (
        "FATAL: install_state.json not found.\n"
        "Aditus must be installed via AditusSetup.exe before running.\n"
        "Searched locations:\n"
    )
    for c in candidates:
        msg += f"  {c}\n"
    debug_log(msg)
    print(msg, file=sys.stderr)
    sys.exit(1)

_find_install_state()

def _get_cfg_path():
    return INSTALL_STATE.get("config_path") or os.path.join(INSTALL_STATE.get("install_path", ""), "aditus_config.json")

CONFIG_PATH = _get_cfg_path()


debug_log(f"STARTUP: install_state_path={INSTALL_STATE_PATH} config_path={CONFIG_PATH} frozen={getattr(sys,'frozen',False)}")

# ── Runtime integration ───────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from runtime.event_queue import get_event_queue as _get_event_queue
    from runtime.runtime_engine import RuntimeEngine
    from runtime.app_launcher import AppLauncher
    from runtime.trigger_integration import HotkeyTrigger
    from runtime.system_tray import SystemTray
    from config.config_manager import ConfigManager

    _RUNTIME_AVAILABLE = True
except ImportError:
    _RUNTIME_AVAILABLE = False
    ConfigManager = dict  # type: ignore[assignment]
    SystemTray = None  # type: ignore[assignment]

debug_log(f"RUNTIME_AVAILABLE={_RUNTIME_AVAILABLE}")

# ── Single-instance enforcement ───────────────────────────────────────────
try:
    from runtime.single_instance import enforce_single_instance
    enforce_single_instance()
    debug_log("SINGLE_INSTANCE: enforcer active")
except RuntimeError as e:
    debug_log(f"SINGLE_INSTANCE: already running — exiting ({e})")
    sys.exit(0)
except ImportError as e:
    debug_log(f"SINGLE_INSTANCE: enforcer unavailable (non-fatal): {e}")
except Exception as e:
    debug_log(f"SINGLE_INSTANCE: unexpected error (non-fatal): {e}")

# ── Design tokens ─────────────────────────────────────────────────────────
ROOT_BG       = "#0A0D12"
SURFACE_BG    = "#080B0F"
CARD_BG       = "#0D1118"
CARD_ICON_BG  = "#111820"
ACTIVE_BG     = "#0D1E30"
BORDER_COLOR  = "#1A2030"
BORDER_ACTIVE = "#1A3A5C"
BORDER_HOVER  = "#2A4A6C"
ACCENT        = "#4A9EDA"
ACCENT_HOVER  = "#7AB3E0"
TEXT_BRIGHT   = "#DDEEFF"
TEXT_CARD     = "#B0C8E0"
TEXT_MUTED    = "#2A3A50"
TEXT_NAV      = "#3A4A60"
GREEN_DOT     = "#2A9A4A"
BTN_BG        = "#071525"
BTN_BORDER    = "#2A5A8A"
DASH_BORDER   = "#1A2A40"
INPUT_BG      = "#0D1118"
ERR_RED       = "#E05050"

FONT_MONO    = ("Consolas", 10)
FONT_MONO_SM = ("Consolas", 9)

SPACE       = 8
SIDEBAR_W   = 58
TITLEBAR_H  = 38
STATUSBAR_H = 32
CARD_RADIUS = 10
BTN_RADIUS  = 8

from version import ADITUS_VERSION as VERSION

if getattr(sys, 'frozen', False):
    ICO_PATH = os.path.join(sys._MEIPASS, 'assets', 'aditus.ico')
else:
    ICO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'aditus.ico')

# ── Icon map — single source of truth ─────────────────────────────────────
ICONS = {
    "dashboard": "\U0001F680",
    "apps":      "\U0001F4E6",
    "activity":  "\U0001F4CA",
    "settings":  "\u2699\uFE0F",
    "add":       "\u2795",
    "edit":      "\u270E",
    "delete":    "\u2716",
    "launch":    "\u26A1",
    "app_icon":  "\U0001F4E6",
    "trigger":   "\U0001F3AC",
    "engine":    "\U0001F9BE",
    "queue":     "\U0001F4CB",
}

# ── Config loader ─────────────────────────────────────────────────────────

def load_config() -> dict:
    global CONFIG_PATH
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                debug_log(f"CONFIG: loaded from {CONFIG_PATH}")
                return data
    except Exception as e:
        msg = f"FATAL: aditus_config.json ({CONFIG_PATH}) is invalid: {e}"
        debug_log(msg)
        print(msg, file=sys.stderr)
        sys.exit(1)
    msg = f"FATAL: aditus_config.json not found at {CONFIG_PATH}"
    debug_log(msg)
    print(msg, file=sys.stderr)
    sys.exit(1)

CONFIG = load_config()

_trigger_section = CONFIG.get("trigger", {})
TRIGGER_OPTIONS  = _trigger_section.get("options", ["clap", "hotkey", "manual"])
ACTIVE_TRIGGER   = _trigger_section.get("type", TRIGGER_OPTIONS[0])
_raw_apps        = CONFIG.get("apps", [])
if isinstance(_raw_apps, list):
    APP_DICT = {f"app{i+1}": {"label": a.get("name", f"App {i+1}"), "path": a.get("path", "")} for i, a in enumerate(_raw_apps)}
else:
    APP_DICT = _raw_apps

# ── Runtime contract validation ─────────────────────────────────────────
# After both install_state.json and aditus_config.json are loaded, verify
# every required key is present.  Any failure → sys.exit(1).

CONFIG_REQUIRED_KEYS = ("trigger", "apps", "startup", "minimize_to_tray")

def _validate_runtime_contract():
    errors = []
    for key in INSTALL_STATE_REQUIRED_KEYS:
        if key not in INSTALL_STATE:
            errors.append(f"install_state.json missing required key '{key}'")
    for key in CONFIG_REQUIRED_KEYS:
        if key not in CONFIG:
            errors.append(f"aditus_config.json missing required key '{key}'")
    if errors:
        msg = "\n".join(["FATAL: Runtime contract validation failed:"] + errors)
        debug_log(msg)
        print(msg, file=sys.stderr)
        sys.exit(1)
    debug_log("VALIDATION: runtime contract passed — all required keys present")

_validate_runtime_contract()


# ── Helpers ───────────────────────────────────────────────────────────────

def _draw_corner_accents(canvas: tk.Canvas, w: int, h: int) -> None:
    c = "#2A4A6C"
    x0, y0 = SIDEBAR_W + 1, TITLEBAR_H + 1
    x1 = w - 1
    y1 = h - STATUSBAR_H - 1
    for (sx, sy, dx, dy) in [
        (x0, y0, x0 + 10, y0), (x0, y0, x0, y0 + 10),
        (x1 - 10, y0, x1, y0), (x1, y0, x1, y0 + 10),
        (x0, y1, x0 + 10, y1), (x0, y1, x0, y1 - 10),
        (x1 - 10, y1, x1, y1), (x1, y1, x1, y1 - 10),
    ]:
        try:
            canvas.create_line(sx, sy, dx, dy, fill=c, width=1)
        except Exception:
            pass


def _make_page_header(parent: ctk.CTkFrame, title: str, accent_w: int = 28) -> ctk.CTkFrame:
    hdr = ctk.CTkFrame(parent, fg_color="transparent", height=50)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tf = ctk.CTkFrame(hdr, fg_color="transparent")
    tf.pack(side="left", fill="y")
    ctk.CTkLabel(tf, text=title, font=("Segoe UI", 22, "bold"), text_color=TEXT_BRIGHT
                 ).pack(anchor="w")
    ctk.CTkFrame(tf, width=accent_w, height=2, fg_color=ACCENT, corner_radius=0
                 ).pack(anchor="w", pady=(2, 0))
    return hdr


def _safe_filedialog_initialdir() -> str:
    install_path = INSTALL_STATE.get("install_path", "")
    if install_path and os.path.isdir(install_path):
        return install_path
    return str(Path.home())


# ── Signal handlers ─────────────────────────────────────────────────────────

def _handle_sigterm(sig, frame):
    debug_log("SIGTERM received — shutting down")
    sys.exit(0)

try:
    signal.signal(signal.SIGTERM, _handle_sigterm)
except Exception:
    pass

# ── Main App ──────────────────────────────────────────────────────────────

class AditusApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color=ROOT_BG)
        self.title("Aditus")
        self.geometry("900x580")
        self.resizable(False, False)
        if os.path.isfile(ICO_PATH):
            try:
                self.iconbitmap(ICO_PATH)
                debug_log(f"ICON: loaded from {ICO_PATH}")
            except Exception as e:
                debug_log(f"ICON: iconbitmap failed: {e}")
        else:
            debug_log(f"ICON: NOT FOUND at {ICO_PATH}")

        self._launch_count = 0
        self._scan_y = TITLEBAR_H
        self._scan_dir = 1
        self._current_page: str = ""
        self._activity_log: List[Dict[str, str]] = []
        self._settings_data: Dict = dict(CONFIG)
        self._recording_hotkey = False
        self._destroying = False
        self._alive = True

        # Runtime engine
        self._engine: Optional[RuntimeEngine] = None
        self._cfg_mgr: Optional[ConfigManager] = None
        if _RUNTIME_AVAILABLE:
            try:
                self._engine = RuntimeEngine(
                    get_apps=lambda: list(APP_DICT.values()),
                )
                self._engine.start()
                debug_log("ENGINE: started successfully")
                atexit.register(self._cleanup_children)
            except Exception as e:
                debug_log(f"ENGINE: init failed: {e}")
                self._engine = None
            try:
                self._cfg_mgr = ConfigManager(CONFIG_PATH)
                debug_log(f"CONFIG_MANAGER: init with config_path={CONFIG_PATH}")
            except Exception as e:
                debug_log(f"CONFIG_MANAGER: init failed: {e}")
                self._cfg_mgr = None

        # Hotkey trigger
        self._hotkey_trigger: Optional[HotkeyTrigger] = None
        if _RUNTIME_AVAILABLE:
            try:
                hotkey = CONFIG.get("trigger", {}).get("hotkey", "ctrl+shift+j")
                ht = HotkeyTrigger(hotkey, self._trigger_launch)
                ht.start()
                self._hotkey_trigger = ht
                debug_log(f"HOTKEY: bound '{hotkey}'")
            except Exception as e:
                debug_log(f"HOTKEY: failed to bind '{hotkey}': {e}")
                self._hotkey_trigger = None

        # System tray
        self._tray: Optional[SystemTray] = None
        if _RUNTIME_AVAILABLE and SystemTray is not None:
            try:
                self._tray = SystemTray(self, ico_path=ICO_PATH)
                self._tray.start()
                SystemTray.setup_global_cleanup()
            except Exception:
                self._tray = None

        # Close → hide to tray when minimize_to_tray is enabled
        self.protocol("WM_DELETE_WINDOW", self._on_close_window)

        # Background canvas
        self.bg_canvas = tk.Canvas(self, bg=ROOT_BG, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self._build_titlebar()

        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.pack(fill="both", expand=True)
        self._build_sidebar(body_frame)

        self._page_container = ctk.CTkFrame(body_frame, fg_color="transparent")
        self._page_container.pack(side="left", fill="both", expand=True)

        self._build_statusbar()

        self._pages: Dict[str, ctk.CTkFrame] = {}
        self._build_dashboard_page()
        self._build_apps_page()
        self._build_activity_page()
        self._build_settings_page()

        self._animate_scanline()
        self._blink_status_dot()

        if "--startup" in sys.argv:
            self.after(50, self._startup_sequence)
        self.after(100, self._refresh_overlay)
        self._navigate_to("dashboard")

        # Poll EventQueue for live updates
        self._poll_event_queue()

    # ── Title bar ─────────────────────────────────────────────────────────
    def _build_titlebar(self) -> None:
        bar = tk.Frame(self, bg=SURFACE_BG, height=TITLEBAR_H, highlightthickness=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        df = tk.Frame(bar, bg=SURFACE_BG, highlightthickness=0)
        df.pack(side="left", padx=(SPACE * 2, 0))
        for colour in ("#FF5F57", "#FEBC2E", "#28C840"):
            d = tk.Canvas(df, width=11, height=11, bg=SURFACE_BG, highlightthickness=0)
            d.pack(side="left", padx=(0, 6))
            d.create_oval(0, 0, 11, 11, fill=colour, outline="")
        tk.Label(bar, text="  A  D  I  T  U  S", fg="#3A4A60", bg=SURFACE_BG,
                 font=("Consolas", 10)).pack(side="left", fill="x", expand=True)
        tk.Label(bar, text=VERSION, fg="#1E3040", bg=SURFACE_BG,
                 font=("Consolas", 9)).pack(side="right", padx=(0, SPACE * 3))

    # ── Sidebar ───────────────────────────────────────────────────────────
    def _build_sidebar(self, parent: ctk.CTkFrame) -> None:
        side = tk.Frame(parent, bg=SURFACE_BG, width=SIDEBAR_W)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        nav_items = [
            ("dashboard", ICONS["dashboard"], "Dashboard"),
            ("apps",      ICONS["apps"],      "Apps"),
            ("activity",  ICONS["activity"],  "Activity"),
        ]
        self._side_btns: Dict[str, tk.Canvas] = {}
        self._side_active_key = "dashboard"

        for key, sym, tip in nav_items:
            c = tk.Canvas(side, width=38, height=38, bg=SURFACE_BG,
                          highlightthickness=0, cursor="hand2")
            c.pack(pady=(SPACE + 4 if key == "dashboard" else 4, 0))
            c.data = {"key": key, "symbol": sym, "active": key == "dashboard"}
            self._draw_side_icon(c, key == "dashboard")
            c.bind("<Button-1>", self._on_sidebar_click)
            c.bind("<Enter>", lambda e, k=key: self._on_sidebar_hover(k))
            c.bind("<Leave>", lambda e, k=key: self._on_sidebar_leave(k))
            self._side_btns[key] = c
            self._bind_tooltip(c, tip)

        tk.Frame(side, bg=SURFACE_BG, height=0).pack(fill="both", expand=True)

        s = tk.Canvas(side, width=38, height=38, bg=SURFACE_BG,
                      highlightthickness=0, cursor="hand2")
        s.pack(pady=(0, 8))
        s.data = {"key": "settings", "symbol": ICONS["settings"], "active": False}
        self._draw_side_icon(s, False)
        s.bind("<Button-1>", self._on_sidebar_click)
        s.bind("<Enter>", lambda e: self._on_sidebar_hover("settings"))
        s.bind("<Leave>", lambda e: self._on_sidebar_leave("settings"))
        self._side_btns["settings"] = s
        self._bind_tooltip(s, "Settings")

    def _draw_side_icon(self, canvas: tk.Canvas, active: bool) -> None:
        try:
            canvas.delete("all")
            sym = canvas.data["symbol"]
            if active:
                canvas.create_rectangle(1, 1, 37, 37, outline=BORDER_ACTIVE,
                                        fill=ACTIVE_BG, width=1)
                canvas.create_text(19, 19, text=sym, fill=ACCENT,
                                   font=("Segoe UI", 16))
            else:
                canvas.create_text(19, 19, text=sym, fill=TEXT_NAV,
                                   font=("Segoe UI", 16))
        except Exception:
            pass

    def _on_sidebar_click(self, event: tk.Event) -> None:
        try:
            key = event.widget.data["key"]
            if key != self._side_active_key:
                self._navigate_to(key)
        except Exception:
            pass

    def _on_sidebar_hover(self, key: str) -> None:
        if key != self._side_active_key:
            try:
                self._side_btns[key].create_rectangle(
                    1, 1, 37, 37, outline="", fill="#111820")
            except Exception:
                pass

    def _on_sidebar_leave(self, key: str) -> None:
        if key != self._side_active_key:
            try:
                self._draw_side_icon(self._side_btns[key], False)
            except Exception:
                pass

    def _navigate_to(self, key: str) -> None:
        if key == self._current_page or not self._alive:
            return
        for k, c in self._side_btns.items():
            active = (k == key)
            try:
                c.data["active"] = active
                self._draw_side_icon(c, active)
            except Exception:
                pass
        self._side_active_key = key

        if self._current_page and self._current_page in self._pages:
            try:
                self._pages[self._current_page].place_forget()
            except Exception:
                pass
        try:
            self._pages[key].place(x=0, y=0, relwidth=1, relheight=1)
        except Exception:
            return
        self._current_page = key

        if key == "dashboard":
            self._refresh_dash_stats()
        elif key == "apps":
            self._refresh_apps_page()
        elif key == "activity":
            self._refresh_activity_page()
        elif key == "settings":
            self._sync_settings_from_trigger()
            self._load_settings_ui()

    def _bind_tooltip(self, widget: tk.Widget, text: str) -> None:
        tip_win = None
        def show(e):
            nonlocal tip_win
            try:
                x = widget.winfo_rootx() + 50
                y = widget.winfo_rooty() + 4
                tip_win = tk.Toplevel(widget)
                tip_win.wm_overrideredirect(True)
                tip_win.wm_geometry(f"+{x}+{y}")
                tk.Label(tip_win, text=text, bg="#1A2030", fg=TEXT_BRIGHT,
                         font=("Consolas", 9), padx=6, pady=2).pack()
            except Exception:
                pass
        def hide(e):
            nonlocal tip_win
            if tip_win:
                try:
                    tip_win.destroy()
                except Exception:
                    pass
                tip_win = None
        try:
            widget.bind("<Enter>", show)
            widget.bind("<Leave>", hide)
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════
    # PAGE: Dashboard
    # ══════════════════════════════════════════════════════════════════════
    def _build_dashboard_page(self) -> None:
        page = ctk.CTkFrame(self._page_container, fg_color="transparent")
        self._pages["dashboard"] = page

        hdr = _make_page_header(page, f"{ICONS['dashboard']}  Dashboard")
        pill_frame = ctk.CTkFrame(hdr, fg_color=SURFACE_BG, corner_radius=8, height=36, width=240)
        pill_frame.pack(side="right", pady=9)
        pill_frame.pack_propagate(False)
        inner_pill = ctk.CTkFrame(pill_frame, fg_color=SURFACE_BG, corner_radius=6)
        inner_pill.pack(padx=3, pady=3, fill="both", expand=True)
        self._trigger_btns: List[Dict] = []
        for opt in TRIGGER_OPTIONS:
            is_active = (opt == ACTIVE_TRIGGER)
            tb = ctk.CTkButton(
                inner_pill, text=opt.title(), width=74, height=28,
                corner_radius=6,
                fg_color=ACTIVE_BG if is_active else "transparent",
                text_color=ACCENT if is_active else TEXT_NAV,
                hover_color=ACTIVE_BG, hover=True,
                font=("Segoe UI", 11, "bold"),
                command=lambda o=opt: self._select_trigger(o),
            )
            tb.pack(side="left", padx=2)
            self._trigger_btns.append({"opt": opt, "btn": tb})

        self._dash_stat_labels: Dict[str, ctk.CTkLabel] = {}
        sys_frame = ctk.CTkFrame(page, fg_color="transparent")
        sys_frame.pack(fill="x", padx=SPACE * 3, pady=(SPACE * 2, 0))
        stats = [
            ("engine",  f"{ICONS['engine']}  Engine",  "RUNNING" if _RUNTIME_AVAILABLE else "N/A",  GREEN_DOT),
            ("queue",   f"{ICONS['queue']}  Queue",   "0",                                    ACCENT),
            ("trigger", f"{ICONS['trigger']}  Trigger", ACTIVE_TRIGGER.upper(),               ACCENT_HOVER),
        ]
        for key, label, val, colour in stats:
            box = ctk.CTkFrame(sys_frame, fg_color=CARD_BG, corner_radius=8,
                               border_width=1, border_color=BORDER_COLOR)
            box.pack(side="left", fill="x", expand=True, padx=(0, SPACE), ipady=4)
            ctk.CTkLabel(box, text=label, font=FONT_MONO_SM,
                         text_color=TEXT_MUTED).pack(pady=(SPACE, 0))
            lbl = ctk.CTkLabel(box, text=val, font=("Segoe UI", 18, "bold"),
                               text_color=colour)
            lbl.pack(pady=(0, SPACE))
            self._dash_stat_labels[key] = lbl

        self._dash_cards_container = ctk.CTkFrame(page, fg_color="transparent")
        self._dash_cards_container.pack(fill="both", expand=True,
                                        padx=SPACE * 3, pady=(SPACE * 2, 0))
        self._rebuild_dash_cards()

        self._dash_launch_section(page)

    def _rebuild_dash_cards(self) -> None:
        for w in self._dash_cards_container.winfo_children():
            w.destroy()
        self._dash_cards_container.grid_columnconfigure((0, 1, 2), weight=1)
        self._dash_cards_container.grid_rowconfigure(0, weight=1)
        self._dash_card_frames: List[ctk.CTkFrame] = []
        items = list(APP_DICT.items())[:3]
        for col, (key, app) in enumerate(items):
            self._dash_create_card(self._dash_cards_container, col, app)
        if len(APP_DICT) < 3:
            self._dash_create_add_card(self._dash_cards_container, min(len(APP_DICT), 2))

    def _dash_create_card(self, parent: ctk.CTkFrame, col: int, app: dict) -> None:
        label = app.get("label", f"App {col + 1}")
        icon = app.get("icon") or ICONS["app_icon"]
        app_path = app.get("path", "C:\\Program Files\\...")
        card = ctk.CTkFrame(parent, corner_radius=CARD_RADIUS, fg_color=CARD_BG,
                            border_width=1, border_color=BORDER_COLOR)
        card.grid(row=0, column=col, padx=6, pady=6, sticky="nsew")
        card.bind("<Enter>", lambda e, c=card: self._dash_card_enter(c))
        card.bind("<Leave>", lambda e, c=card: self._dash_card_leave(c))
        self._dash_card_frames.append(card)
        accent_line = ctk.CTkFrame(card, height=2, fg_color=CARD_BG, corner_radius=0)
        accent_line.place(x=0, y=0, relwidth=1)
        card._accent_line = accent_line

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=SPACE * 2, pady=(SPACE * 2, 0))
        iframe = ctk.CTkFrame(top, width=40, height=40, fg_color=CARD_ICON_BG,
                              corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        iframe.pack(side="left")
        iframe.pack_propagate(False)
        ctk.CTkLabel(iframe, text=icon, font=("Segoe UI", 18),
                     text_color=TEXT_BRIGHT).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(card, text=label, font=("Segoe UI", 15, "bold"),
                     text_color=TEXT_CARD, anchor="w"
                     ).pack(fill="x", padx=SPACE * 2, pady=(SPACE + 4, 1))
        ctk.CTkLabel(card, text=app_path, font=FONT_MONO_SM,
                     text_color=TEXT_MUTED, anchor="w"
                     ).pack(fill="x", padx=SPACE * 2)
        sf = ctk.CTkFrame(card, fg_color="transparent")
        sf.pack(fill="x", padx=SPACE * 2, pady=(SPACE, SPACE * 2))
        ctk.CTkFrame(sf, width=5, height=5, fg_color=GREEN_DOT,
                     corner_radius=5).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(sf, text="Ready", font=FONT_MONO_SM,
                     text_color=GREEN_DOT).pack(side="left")

        for child in card.winfo_children():
            child.bind("<Enter>", lambda e, c=card: self._dash_card_enter(c))
            child.bind("<Leave>", lambda e, c=card: self._dash_card_leave(c))

    def _dash_card_enter(self, card: ctk.CTkFrame) -> None:
        try:
            card.configure(border_color=ACCENT, fg_color="#0F1520")
            if hasattr(card, "_accent_line"):
                card._accent_line.configure(fg_color=ACCENT)
        except Exception:
            pass

    def _dash_card_leave(self, card: ctk.CTkFrame) -> None:
        try:
            card.configure(border_color=BORDER_COLOR, fg_color=CARD_BG)
            if hasattr(card, "_accent_line"):
                card._accent_line.configure(fg_color=CARD_BG)
        except Exception:
            pass

    def _dash_create_add_card(self, parent: ctk.CTkFrame, col: int) -> None:
        card = ctk.CTkFrame(parent, corner_radius=CARD_RADIUS, fg_color="transparent",
                            border_width=1, border_color=DASH_BORDER)
        card.grid(row=0, column=col, padx=6, pady=6, sticky="nsew")
        card.bind("<Enter>",
                  lambda e: card.configure(border_color=BORDER_HOVER, fg_color="#0A0F18"))
        card.bind("<Leave>",
                  lambda e: card.configure(border_color=DASH_BORDER, fg_color="transparent"))
        card.bind("<Button-1>", lambda e: self._navigate_to("apps"))
        add_label = ctk.CTkLabel(card, text=ICONS["add"], font=("Segoe UI", 28),
                     text_color=TEXT_MUTED).pack(expand=True, pady=(SPACE * 3, 2))
        add_text = ctk.CTkLabel(card, text="Add App", font=FONT_MONO_SM,
                     text_color=TEXT_MUTED).pack(expand=True, pady=(0, SPACE * 3))
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e: self._navigate_to("apps"))

    def _dash_launch_section(self, parent: ctk.CTkFrame) -> None:
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.pack(fill="x", padx=SPACE * 3, pady=(SPACE, SPACE * 2))
        self._launch_btn = ctk.CTkButton(
            section, text=f"{ICONS['launch']}  Launch Now", height=46,
            corner_radius=BTN_RADIUS, fg_color=BTN_BG, hover_color="#0A1E35",
            text_color=ACCENT, border_width=1, border_color=BTN_BORDER,
            font=("Segoe UI", 15, "bold"), command=self._trigger_launch,
        )
        self._launch_btn.pack(side="left", fill="x", expand=True, padx=(0, SPACE * 2))
        stats = ctk.CTkFrame(section, fg_color=SURFACE_BG, corner_radius=8,
                             border_width=1, border_color=BORDER_COLOR)
        stats.pack(side="right")
        ins = ctk.CTkFrame(stats, fg_color="transparent")
        ins.pack(padx=SPACE * 2, pady=SPACE)
        self._dash_stat_widgets: Dict[str, ctk.CTkLabel] = {}
        for label, default, key, colour in [
            ("Triggered", "0", "trig_val", ACCENT),
            ("Apps", str(min(len(APP_DICT), 3)), "apps_val", GREEN_DOT),
            ("Mode", TRIGGER_OPTIONS[0].upper() if TRIGGER_OPTIONS else "MANUAL", "mode_val", ACCENT),
        ]:
            row = ctk.CTkFrame(ins, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, font=FONT_MONO_SM,
                         text_color=TEXT_MUTED).pack(side="left")
            lbl = ctk.CTkLabel(row, text=default, font=FONT_MONO_SM,
                               text_color=colour)
            lbl.pack(side="right", padx=(SPACE * 2, 0))
            self._dash_stat_widgets[key] = lbl

    def _refresh_dash_stats(self) -> None:
        self._rebuild_dash_cards()
        if "apps_val" in self._dash_stat_widgets:
            self._dash_stat_widgets["apps_val"].configure(
                text=str(min(len(APP_DICT), 99)))
        if "trig_val" in self._dash_stat_widgets:
            self._dash_stat_widgets["trig_val"].configure(
                text=str(self._launch_count))
        if "mode_val" in self._dash_stat_widgets:
            self._dash_stat_widgets["mode_val"].configure(
                text=ACTIVE_TRIGGER.upper())
        if "engine" in self._dash_stat_labels:
            self._dash_stat_labels["engine"].configure(
                text="RUNNING" if _RUNTIME_AVAILABLE else "N/A")
        if "queue" in self._dash_stat_labels:
            try:
                qsize = self._engine.event_queue._queue.qsize() if self._engine else 0
            except Exception:
                qsize = 0
            self._dash_stat_labels["queue"].configure(text=str(qsize))
        if "trigger" in self._dash_stat_labels:
            self._dash_stat_labels["trigger"].configure(text=ACTIVE_TRIGGER.upper())

    # ══════════════════════════════════════════════════════════════════════
    # PAGE: Apps  (with native file picker)
    # ══════════════════════════════════════════════════════════════════════
    def _build_apps_page(self) -> None:
        page = ctk.CTkFrame(self._page_container, fg_color="transparent")
        self._pages["apps"] = page

        hdr = _make_page_header(page, f"{ICONS['apps']}  Applications")
        add_btn = ctk.CTkButton(
            hdr, text=f"{ICONS['add']}  Add App", width=110, height=32,
            corner_radius=8, fg_color=ACTIVE_BG, hover_color="#0F2038",
            text_color=ACCENT, border_width=1, border_color=BORDER_ACTIVE,
            font=("Segoe UI", 13, "bold"), command=self._on_add_app,
        )
        add_btn.pack(side="right", padx=(0, SPACE * 3), pady=9)

        self._apps_scroll = ctk.CTkScrollableFrame(
            page, fg_color="transparent", scrollbar_button_color=TEXT_MUTED,
            scrollbar_button_hover_color=ACCENT,
        )
        self._apps_scroll.pack(fill="both", expand=True,
                               padx=SPACE * 3, pady=(SPACE, SPACE * 2))
        self._apps_inner = ctk.CTkFrame(self._apps_scroll, fg_color="transparent")
        self._apps_inner.pack(fill="x", expand=True)

    def _refresh_apps_page(self) -> None:
        if not self._alive:
            return
        for w in self._apps_inner.winfo_children():
            w.destroy()
        self._apps_inner.grid_columnconfigure(0, weight=1)

        if not APP_DICT:
            empty = ctk.CTkFrame(self._apps_inner, fg_color="transparent")
            empty.grid(row=0, column=0, pady=40)
            ctk.CTkLabel(empty, text=f"{ICONS['apps']}  No applications configured",
                         font=("Segoe UI", 15), text_color=TEXT_MUTED).pack()
            ctk.CTkLabel(empty, text=f'{ICONS["add"]}  Click "+ Add App" to get started',
                         font=FONT_MONO_SM, text_color=TEXT_MUTED).pack()
            return

        for row, (key, app) in enumerate(APP_DICT.items()):
            self._apps_create_row(key, app, row)

    def _apps_create_row(self, key: str, app: dict, row: int) -> None:
        card = ctk.CTkFrame(self._apps_inner, fg_color=CARD_BG,
                            corner_radius=CARD_RADIUS, border_width=1,
                            border_color=BORDER_COLOR)
        card.grid(row=row, column=0, padx=0, pady=4, sticky="ew")
        card.bind("<Enter>", lambda e, c=card: c.configure(border_color=BORDER_HOVER))
        card.bind("<Leave>", lambda e, c=card: c.configure(border_color=BORDER_COLOR))

        icon_frame = ctk.CTkFrame(card, width=40, height=40, fg_color=CARD_ICON_BG,
                                   corner_radius=8, border_width=1, border_color=BORDER_COLOR)
        icon_frame.pack(side="left", padx=SPACE * 2, pady=SPACE * 2)
        icon_frame.pack_propagate(False)
        icon_text = app.get("icon") or ICONS["app_icon"]
        ctk.CTkLabel(icon_frame, text=icon_text, font=("Segoe UI", 18),
                     text_color=TEXT_BRIGHT).place(relx=0.5, rely=0.5, anchor="center")

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=(SPACE, 0), pady=SPACE)
        ctk.CTkLabel(info, text=app.get("label", key),
                     font=("Segoe UI", 14, "bold"),
                     text_color=TEXT_CARD, anchor="w").pack(fill="x")
        ctk.CTkLabel(info, text=app.get("path", ""), font=FONT_MONO_SM,
                     text_color=TEXT_MUTED, anchor="w").pack(fill="x")

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(side="right", padx=SPACE * 2)
        edit_btn = ctk.CTkButton(
            btn_frame, text="\u270F", width=32, height=32,
            corner_radius=6, fg_color="transparent", hover_color=ACTIVE_BG,
            text_color=TEXT_MUTED, font=("Segoe UI", 14),
            command=lambda k=key: self._on_edit_app(k),
        )
        edit_btn.pack(side="left", padx=2)
        del_btn = ctk.CTkButton(
            btn_frame, text="\u2715", width=32, height=32,
            corner_radius=6, fg_color="transparent", hover_color="#1A1010",
            text_color=TEXT_MUTED, font=("Segoe UI", 14),
            command=lambda k=key: self._on_delete_app(k),
        )
        del_btn.pack(side="left", padx=2)
        del_btn.bind("<Enter>", lambda e: del_btn.configure(text_color=ERR_RED))
        del_btn.bind("<Leave>", lambda e: del_btn.configure(text_color=TEXT_MUTED))

    def _on_add_app(self) -> None:
        self._show_app_dialog()

    def _on_edit_app(self, key: str) -> None:
        self._show_app_dialog(key)

    def _on_delete_app(self, key: str) -> None:
        if key in APP_DICT:
            app_label = APP_DICT[key].get("label", key)
            confirm = messagebox.askyesno(
                "Remove App", f"Remove {app_label} from the launcher?",
                parent=self)
            if not confirm:
                return
            del APP_DICT[key]
            self._persist_config()
            self._refresh_apps_page()
            self._add_activity("system", f"Removed app: {app_label}")

    def _next_app_key(self) -> str:
        existing = [int(k[3:]) for k in APP_DICT if k.startswith("app") and k[3:].isdigit()]
        return f"app{max(existing) + 1 if existing else 1}"

    def _show_app_dialog(self, edit_key: str | None = None) -> None:
        dialog = ctk.CTkToplevel(self, fg_color=ROOT_BG)
        dialog.title("Edit App" if edit_key else "Add App")
        dialog.geometry("460x480")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        self._center_dialog(dialog)

        app = APP_DICT.get(edit_key, {}) if edit_key else {}
        pad = SPACE * 2

        # ── Label ────────────────────────────────────────────────────
        ctk.CTkLabel(dialog, text="App Name", font=("Segoe UI", 11),
                     text_color=TEXT_MUTED).pack(anchor="w", padx=pad, pady=(pad, 2))
        label_var = tk.StringVar(value=app.get("label", ""))
        ctk.CTkEntry(dialog, textvariable=label_var, height=36,
                     fg_color=CARD_BG, border_color=BORDER_COLOR,
                     border_width=1, corner_radius=6,
                     text_color=TEXT_BRIGHT, font=("Segoe UI", 13),
                     ).pack(fill="x", padx=pad)

        # ── Icon picker ──────────────────────────────────────────────
        ctk.CTkLabel(dialog, text="Icon", font=("Segoe UI", 11),
                     text_color=TEXT_MUTED).pack(anchor="w", padx=pad, pady=(12, 4))
        ICON_EMOJIS = ["📦", "🎮", "🌐", "🎵", "📁", "⚙️",
                       "🖥️", "📝", "🔧", "🚀", "🎨", "📊"]
        icon_var = tk.StringVar(value=app.get("icon", "📦"))
        selected_frame = [None]
        grid_outer = ctk.CTkFrame(dialog, fg_color="transparent")
        grid_outer.pack(fill="x", padx=pad)

        def _select(emoji, frame):
            icon_var.set(emoji)
            if selected_frame[0]:
                selected_frame[0].configure(fg_color=CARD_BG, border_color=BORDER_COLOR)
            frame.configure(fg_color=ACTIVE_BG, border_color=ACCENT)
            selected_frame[0] = frame

        for i, emoji in enumerate(ICON_EMOJIS):
            r, c = divmod(i, 6)
            grid_outer.grid_columnconfigure(c, weight=1, uniform="ic")
            is_sel = (emoji == icon_var.get())
            cell = ctk.CTkFrame(
                grid_outer, width=56, height=56,
                fg_color=ACTIVE_BG if is_sel else CARD_BG,
                border_width=1,
                border_color=ACCENT if is_sel else BORDER_COLOR,
                corner_radius=8,
            )
            cell.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
            cell.grid_propagate(False)
            if is_sel:
                selected_frame[0] = cell
            lbl = ctk.CTkLabel(cell, text=emoji, font=("Segoe UI Emoji", 22),
                               fg_color="transparent", text_color=TEXT_BRIGHT)
            lbl.place(relx=0.5, rely=0.5, anchor="center")
            for w in (cell, lbl):
                w.bind("<Button-1>", lambda e, em=emoji, f=cell: _select(em, f))
                w.bind("<Enter>", lambda e, f=cell: f.configure(
                    fg_color="#151F30") if f != selected_frame[0] else None)
                w.bind("<Leave>", lambda e, f=cell: f.configure(
                    fg_color=CARD_BG) if f != selected_frame[0] else None)

        # ── Path ─────────────────────────────────────────────────────
        ctk.CTkLabel(dialog, text="Application Path", font=("Segoe UI", 11),
                     text_color=TEXT_MUTED).pack(anchor="w", padx=pad, pady=(12, 4))
        path_row = ctk.CTkFrame(dialog, fg_color="transparent")
        path_row.pack(fill="x", padx=pad)
        path_var = tk.StringVar(value=app.get("path", ""))
        ctk.CTkEntry(path_row, textvariable=path_var, height=36,
                     fg_color=CARD_BG, border_color=BORDER_COLOR,
                     border_width=1, corner_radius=6,
                     text_color=TEXT_BRIGHT, font=("Consolas", 10),
                     state="readonly").pack(side="left", fill="x", expand=True)

        def browse_path():
            start_menu = os.path.expandvars(
                r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
            initial = start_menu if os.path.isdir(start_menu) else str(Path.home())
            fp = filedialog.askopenfilename(
                title="Select Application",
                initialdir=initial,
                filetypes=[("Shortcuts", "*.lnk"),
                           ("Executables", "*.exe"),
                           ("All files", "*.*")],
                parent=dialog,
            )
            if fp:
                path_var.set(fp)
                if not edit_key or not app.get("label"):
                    auto = os.path.splitext(os.path.basename(fp))[0]
                    label_var.set(auto.replace("_", " ").replace("-", " ").title())

        ctk.CTkButton(
            path_row, text="Browse", width=80, height=36,
            corner_radius=6, fg_color=ACTIVE_BG, hover_color=BORDER_HOVER,
            text_color=ACCENT, border_width=1, border_color=BORDER_ACTIVE,
            font=("Segoe UI", 12, "bold"), command=browse_path,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkLabel(dialog,
                     text="Opens your Start Menu — pick any .lnk shortcut",
                     font=("Consolas", 9), text_color=TEXT_MUTED,
                     ).pack(anchor="w", padx=pad, pady=(3, 0))

        # ── Buttons ───────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=pad, pady=(16, pad))

        def save():
            label = label_var.get().strip()
            path = path_var.get().strip()
            if not label:
                messagebox.showwarning("Required", "App name is required.", parent=dialog)
                return
            if not path:
                messagebox.showwarning("Required", "Please select an application.", parent=dialog)
                return
            if not os.path.isfile(path):
                if not messagebox.askyesno("Not Found",
                    f"File not found:\n{path}\n\nSave anyway?", parent=dialog):
                    return
            entry = {"label": label, "path": path, "icon": icon_var.get()}
            if edit_key and edit_key in APP_DICT:
                APP_DICT[edit_key] = entry
                self._add_activity("system", f"Updated app: {label}")
            else:
                APP_DICT[self._next_app_key()] = entry
                self._add_activity("system", f"Added app: {label}")
            self._persist_config()
            dialog.destroy()
            self._refresh_apps_page()

        ctk.CTkButton(btn_row, text="Cancel", width=100, height=36,
                      corner_radius=6, fg_color="transparent",
                      text_color=TEXT_MUTED, hover_color=CARD_BG,
                      font=("Segoe UI", 13),
                      command=dialog.destroy).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btn_row, text="Save App", width=110, height=36,
                      corner_radius=6, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      text_color=ROOT_BG, font=("Segoe UI", 13, "bold"),
                      command=save).pack(side="right")

        dialog.wait_window()

    def _center_dialog(self, dialog: ctk.CTkToplevel) -> None:
        try:
            self.update_idletasks()
            pw, ph = self.winfo_width(), self.winfo_height()
            px, py = self.winfo_x(), self.winfo_y()
            dw, dh = 460, 480
            x = px + (pw - dw) // 2
            y = py + (ph - dh) // 2
            dialog.geometry(f"{dw}x{dh}+{x}+{y}")
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════
    # PAGE: Activity
    # ══════════════════════════════════════════════════════════════════════
    def _build_activity_page(self) -> None:
        page = ctk.CTkFrame(self._page_container, fg_color="transparent")
        self._pages["activity"] = page

        hdr = _make_page_header(page, f"{ICONS['activity']}  Activity Log")
        auto_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        auto_frame.pack(side="right", pady=9)
        self._activity_autoscroll = tk.BooleanVar(value=True)
        ctk.CTkSwitch(
            auto_frame, text="Auto-scroll", variable=self._activity_autoscroll,
            onvalue=True, offvalue=False,
            fg_color=TEXT_MUTED, progress_color=ACCENT,
            button_color=ACCENT, text_color=TEXT_NAV,
            font=FONT_MONO_SM,
        ).pack(side="left", padx=(0, SPACE))
        ctk.CTkButton(
            auto_frame, text=f"{ICONS['delete']}  Clear", width=90, height=30,
            corner_radius=8, fg_color="transparent", hover_color="#1A1010",
            text_color=TEXT_MUTED, font=("Segoe UI", 12),
            command=self._on_clear_activity,
        ).pack(side="left")

        col_bar = ctk.CTkFrame(page, fg_color="transparent", height=28)
        col_bar.pack(fill="x", padx=SPACE * 3, pady=(SPACE, 0))
        col_bar.pack_propagate(False)
        for txt, w in [("Time", 80), ("Type", 100), ("Event", 0)]:
            lbl = ctk.CTkLabel(col_bar, text=txt, font=FONT_MONO_SM,
                               text_color=TEXT_MUTED, anchor="w", width=w)
            lbl.pack(side="left", padx=(0, SPACE))
            if w == 0:
                lbl.pack(fill="x", expand=True)

        self._activity_scroll = ctk.CTkScrollableFrame(
            page, fg_color="transparent", scrollbar_button_color=TEXT_MUTED,
            scrollbar_button_hover_color=ACCENT,
        )
        self._activity_scroll.pack(fill="both", expand=True,
                                   padx=SPACE * 3, pady=(SPACE, SPACE * 2))

    def _add_activity(self, etype: str, desc: str) -> None:
        if not self._alive:
            return
        ts = time.strftime("%H:%M:%S")
        entry = {"time": ts, "type": etype, "desc": desc}
        self._activity_log.insert(0, entry)
        if len(self._activity_log) > 500:
            self._activity_log.pop()
        if self._current_page == "activity":
            self._refresh_activity_page()

    def _refresh_activity_page(self) -> None:
        if not self._alive or not hasattr(self, "_activity_scroll"):
            return
        try:
            for w in self._activity_scroll.winfo_children():
                w.destroy()
        except Exception:
            return
        if not self._activity_log:
            try:
                ctk.CTkLabel(self._activity_scroll, text="No events yet",
                             font=("Segoe UI", 13), text_color=TEXT_MUTED
                             ).pack(pady=40)
            except Exception:
                pass
            return
        for entry in self._activity_log[:200]:
            try:
                row = ctk.CTkFrame(self._activity_scroll, fg_color="transparent", height=26)
                row.pack(fill="x", pady=1)
                row.pack_propagate(False)
                ctk.CTkLabel(row, text=entry["time"], width=80, font=FONT_MONO_SM,
                             text_color="#6A8AAA", anchor="w").pack(side="left")
                colour = (ACCENT if entry["type"] == "trigger"
                          else GREEN_DOT if entry["type"] == "launch"
                          else TEXT_NAV)
                ctk.CTkLabel(row, text=entry["type"].upper(), width=100, font=FONT_MONO_SM,
                             text_color=colour, anchor="w").pack(side="left")
                ctk.CTkLabel(row, text=self._shorten(entry["desc"], 80), font=FONT_MONO_SM,
                             text_color=TEXT_BRIGHT, anchor="w"
                             ).pack(side="left", fill="x", expand=True)
            except Exception:
                continue
        if self._activity_autoscroll.get():
            try:
                self._activity_scroll._parent_canvas.yview_moveto(0)
            except Exception:
                pass

    def _shorten(self, text: str, maxlen: int) -> str:
        return text if len(text) <= maxlen else text[:maxlen - 2] + "..."

    def _on_clear_activity(self) -> None:
        self._activity_log.clear()
        self._refresh_activity_page()

    def _poll_event_queue(self) -> None:
        if not self._alive:
            return
        try:
            eq = _get_event_queue()
            while True:
                event = eq.get_nowait()
                if event is None:
                    break
                if isinstance(event, dict):
                    etype = event.get("type", "unknown")
                    if etype == "trigger":
                        continue
                    action = event.get("action", "unknown")
                    self._add_activity(etype, f"Event: {action}")
        except Exception:
            pass
        self.after(500, self._poll_event_queue)

    # ══════════════════════════════════════════════════════════════════════
    # PAGE: Settings
    # ══════════════════════════════════════════════════════════════════════
    def _build_settings_page(self) -> None:
        page = ctk.CTkFrame(self._page_container, fg_color="transparent")
        self._pages["settings"] = page
        _make_page_header(page, f"{ICONS['settings']}  Settings")
        self._settings_scroll = ctk.CTkScrollableFrame(
            page, fg_color="transparent", scrollbar_button_color=TEXT_MUTED,
            scrollbar_button_hover_color=ACCENT,
        )
        self._settings_scroll.pack(fill="both", expand=True,
                                   padx=SPACE * 3, pady=(SPACE, SPACE * 2))
        self._load_settings_ui()

    def _sync_settings_from_trigger(self) -> None:
        current = ACTIVE_TRIGGER
        if "trigger" not in self._settings_data:
            self._settings_data["trigger"] = {}
        self._settings_data["trigger"]["type"] = current

    def _load_settings_ui(self) -> None:
        if not self._alive:
            return
        for w in self._settings_scroll.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass
        pad = SPACE * 2

        g1 = self._settings_group("Trigger Mode")
        current_mode = self._settings_data.get("trigger", {}).get("type", "clap")
        self._trigger_mode_var = tk.StringVar(value=current_mode)
        for val in ["clap", "hotkey", "manual"]:
            ctk.CTkRadioButton(
                g1, text=val.title(), variable=self._trigger_mode_var,
                value=val, fg_color=ACCENT, text_color=TEXT_CARD,
                font=("Segoe UI", 13),
            ).pack(anchor="w", padx=SPACE * 2, pady=1)
        self._settings_frame_add(g1)

        g1b = self._settings_group("Clap Sensitivity")
        ctk.CTkLabel(g1b, text="Detection sensitivity (1 = low, 10 = high)",
                     font=FONT_MONO_SM, text_color=TEXT_MUTED).pack(anchor="w", padx=SPACE * 2, pady=(0, 2))
        sens_frame = ctk.CTkFrame(g1b, fg_color="transparent")
        sens_frame.pack(fill="x", padx=SPACE * 2, pady=(2, 0))
        ctk.CTkLabel(sens_frame, text="Low", font=("Segoe UI", 11),
                     text_color=TEXT_MUTED).pack(side="left", padx=(0, 4))
        current_sens = self._settings_data.get("trigger", {}).get("sensitivity", 5)
        self._sensitivity_var = tk.IntVar(value=current_sens)
        self._sensitivity_slider = ctk.CTkSlider(
            sens_frame, from_=1, to=10, number_of_steps=9,
            variable=self._sensitivity_var, fg_color=TEXT_MUTED,
            progress_color=ACCENT, button_color=ACCENT,
            command=self._on_sensitivity_change,
        )
        self._sensitivity_slider.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkLabel(sens_frame, text="High", font=("Segoe UI", 11),
                     text_color=TEXT_MUTED).pack(side="left", padx=(4, 0))
        self._sens_val_label = ctk.CTkLabel(
            g1b, text=f"Current: {current_sens}",
            font=FONT_MONO_SM, text_color=TEXT_CARD,
        )
        self._sens_val_label.pack(anchor="w", padx=SPACE * 2, pady=(2, 0))
        self._settings_frame_add(g1b)

        g2 = self._settings_group("Hotkey Binding")
        ctk.CTkLabel(g2, text="Click the button then press a key combination",
                     font=FONT_MONO_SM, text_color=TEXT_MUTED).pack(anchor="w", padx=SPACE * 2, pady=(0, 2))
        hk = self._settings_data.get("trigger", {}).get("hotkey", "ctrl+shift+j")
        self._hotkey_var = tk.StringVar(value=hk)
        self._hotkey_recorder_btn = ctk.CTkButton(
            g2, text=hk, height=38,
            corner_radius=8, fg_color=INPUT_BG, hover_color=ACTIVE_BG,
            text_color=TEXT_BRIGHT, border_width=1, border_color=BORDER_COLOR,
            font=FONT_MONO,
            command=self._start_hotkey_recording,
        )
        self._hotkey_recorder_btn.pack(fill="x", padx=SPACE * 2, pady=(2, 0))
        self._settings_frame_add(g2)

        g3 = self._settings_group("Startup & Behavior")
        self._startup_var = tk.BooleanVar(
            value=self._settings_data.get("startup", False)
        )
        ctk.CTkSwitch(
            g3, text=f"{ICONS['launch']}  Launch on system startup",
            variable=self._startup_var, onvalue=True, offvalue=False,
            fg_color=TEXT_MUTED, progress_color=ACCENT,
            button_color=ACCENT, text_color=TEXT_CARD,
            font=("Segoe UI", 13),
        ).pack(anchor="w", padx=SPACE * 2, pady=2)

        self._minimize_var = tk.BooleanVar(
            value=self._settings_data.get("minimize_to_tray", True)
        )
        ctk.CTkSwitch(
            g3, text=f"\U0001F4E6  Minimize to system tray",
            variable=self._minimize_var, onvalue=True, offvalue=False,
            fg_color=TEXT_MUTED, progress_color=ACCENT,
            button_color=ACCENT, text_color=TEXT_CARD,
            font=("Segoe UI", 13),
        ).pack(anchor="w", padx=SPACE * 2, pady=2)
        self._settings_frame_add(g3)

        save_btn = ctk.CTkButton(
            self._settings_scroll, text=f"{ICONS['queue']}  Save Configuration", height=42,
            corner_radius=8, fg_color=BTN_BG, hover_color="#0A1E35",
            text_color=ACCENT, border_width=1, border_color=BTN_BORDER,
            font=("Segoe UI", 14, "bold"),
            command=self._on_save_settings,
        )
        save_btn.pack(fill="x", padx=0, pady=(pad, 0))

        ctk.CTkLabel(self._settings_scroll,
                     text="Changes persist to aditus_config.json",
                     font=FONT_MONO_SM, text_color=TEXT_MUTED
                     ).pack(pady=(SPACE, 0))

    def _settings_group(self, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self._settings_scroll, fg_color=CARD_BG,
                             corner_radius=CARD_RADIUS, border_width=1,
                             border_color=BORDER_COLOR)
        ctk.CTkLabel(frame, text=title, font=("Segoe UI", 14, "bold"),
                     text_color=TEXT_BRIGHT).pack(anchor="w", padx=SPACE * 2,
                                                   pady=(SPACE, 4))
        return frame

    def _settings_frame_add(self, frame: ctk.CTkFrame) -> None:
        frame.pack(fill="x", padx=0, pady=(0, 8))

    def _on_save_settings(self) -> None:
        try:
            new_mode = self._trigger_mode_var.get()
            self._settings_data["trigger"] = {
                "type": new_mode,
                "hotkey": self._hotkey_var.get(),
                "sensitivity": self._sensitivity_var.get(),
                "options": ["clap", "hotkey", "manual"],
            }
            self._settings_data["startup"] = self._startup_var.get()
            self._settings_data["minimize_to_tray"] = self._minimize_var.get()

            global ACTIVE_TRIGGER
            ACTIVE_TRIGGER = new_mode
            self._select_trigger(new_mode)

            self._persist_config()
            self._add_activity("system", f"Settings saved (trigger: {new_mode})")
            self._refresh_dash_stats()

            new_hotkey = self._hotkey_var.get()
            debug_log(f"HOTKEY_SAVE: new_hotkey='{new_hotkey}', old_trigger={self._hotkey_trigger}")
            if self._hotkey_trigger:
                try:
                    self._hotkey_trigger.stop()
                    debug_log("HOTKEY_SAVE: old trigger stopped")
                except Exception as e:
                    debug_log(f"HOTKEY_SAVE: stop failed: {e}")
                self._hotkey_trigger = None
            try:
                ht = HotkeyTrigger(new_hotkey, self._trigger_launch)
                ht.start()
                self._hotkey_trigger = ht
                self._hotkey_recorder_btn.configure(text=new_hotkey)
                debug_log(f"HOTKEY_SAVE: new trigger started with '{new_hotkey}'")
            except Exception as e:
                debug_log(f"HOTKEY: failed to bind '{new_hotkey}': {e}")
                self._hotkey_trigger = None
        except Exception as e:
            messagebox.showerror("Save Error", f"Could not save settings:\n{e}", parent=self)

    def _persist_config(self) -> None:
        if self._cfg_mgr is None:
            debug_log("PERSIST_CONFIG: skipped (ConfigManager not available)")
            return
        data = {
            "trigger": {
                "type": self._settings_data.get("trigger", {}).get("type", "clap"),
                "hotkey": self._settings_data.get("trigger", {}).get("hotkey", "ctrl+shift+j"),
                "sensitivity": self._settings_data.get("trigger", {}).get("sensitivity", 5),
                "options": ["clap", "hotkey", "manual"],
            },
            "apps": APP_DICT,
            "startup": self._settings_data.get("startup", False),
            "minimize_to_tray": self._settings_data.get("minimize_to_tray", True),
        }
        debug_log(f"PERSIST_CONFIG: data prepared — trigger={data['trigger']['type']}, sensitivity={data['trigger']['sensitivity']}, hotkey={data['trigger']['hotkey']}")
        debug_log(f"PERSIST_CONFIG: writing to {CONFIG_PATH}")
        try:
            self._cfg_mgr.save(data)
            debug_log(f"PERSIST_CONFIG: saved via ConfigManager to {CONFIG_PATH}")
        except Exception as e:
            debug_log(f"PERSIST_CONFIG: failed: {e}")

    def _start_hotkey_recording(self) -> None:
        self._recording_hotkey = True
        self._hotkey_recorder_btn.configure(
            text="\u23CE  Press a key combination...",
            fg_color=ACTIVE_BG,
            border_color=ACCENT,
        )
        self.focus_force()
        self.bind_all("<KeyPress>", self._capture_hotkey)

    def _capture_hotkey(self, event) -> None:
        debug_log(f"HOTKEY_CAPTURE: keysym={event.keysym} state={event.state}")
        if not self._recording_hotkey:
            return
        self.unbind_all("<KeyPress>")
        self._recording_hotkey = False

        key = event.keysym.lower()
        standalone = {"control_l", "control_r", "shift_l", "shift_r",
                      "alt_l", "alt_r", "win_l", "win_r", "caps_lock",
                      "num_lock", "scroll_lock"}
        if key in standalone:
            self._hotkey_recorder_btn.configure(
                text=self._hotkey_var.get(),
                fg_color=INPUT_BG, border_color=BORDER_COLOR,
            )
            return

        if key == "escape":
            self._hotkey_recorder_btn.configure(
                text=self._hotkey_var.get(),
                fg_color=INPUT_BG, border_color=BORDER_COLOR,
            )
            return

        mods = []
        if event.state & 0x0004:
            mods.append("ctrl")
        if event.state & 0x0001:
            mods.append("shift")
        if event.state & 0x0008:
            mods.append("alt")
        if event.state & 0x0040:
            mods.append("win")

        combo = "+".join(mods + [key])

        import keyboard
        try:
            keyboard.add_hotkey(combo, lambda: None)
            keyboard.remove_hotkey(combo)
        except Exception:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONHAND)
            self._hotkey_recorder_btn.configure(
                text="\u26A0 Already in use \u2014 try another",
                fg_color="#2A1010",
                border_color=ERR_RED,
                text_color=ERR_RED,
            )
            self.after(2000, lambda: self._hotkey_recorder_btn.configure(
                text=self._hotkey_var.get(),
                fg_color=INPUT_BG, border_color=BORDER_COLOR,
                text_color=TEXT_BRIGHT,
            ))
            return

        self._hotkey_var.set(combo)
        self._hotkey_recorder_btn.configure(
            text=combo,
            fg_color="#0A2A1A",
            border_color=GREEN_DOT,
            text_color=GREEN_DOT,
        )
        self.after(1000, lambda: self._hotkey_recorder_btn.configure(
            fg_color=INPUT_BG, border_color=BORDER_COLOR,
            text_color=TEXT_BRIGHT,
        ))

    def _on_sensitivity_change(self, value: float) -> None:
        self._sens_val_label.configure(text=f"Current: {int(value)}")

    # ── Shared ────────────────────────────────────────────────────────────
    def _select_trigger(self, selected: str) -> None:
        global ACTIVE_TRIGGER
        ACTIVE_TRIGGER = selected
        for entry in self._trigger_btns:
            active = entry["opt"] == selected
            try:
                entry["btn"].configure(
                    fg_color=ACTIVE_BG if active else "transparent",
                    text_color=ACCENT if active else TEXT_NAV,
                )
            except Exception:
                pass
        self._add_activity("trigger", f"Trigger mode: {selected}")
        if "mode_val" in self._dash_stat_widgets:
            self._dash_stat_widgets["mode_val"].configure(text=selected.upper())

    def _trigger_launch(self) -> None:
        try:
            self._launch_count += 1
            self._dash_stat_widgets["trig_val"].configure(text=str(self._launch_count))
            self._launch_btn.configure(border_color=ACCENT_HOVER)
            self.after(150, lambda: self._safe_btn_reset())
            now = time.strftime("%H:%M:%S")
            self._status_last.configure(text=f"Last triggered: {now}")
            self._status_launch.configure(
                text=f"Launched {self._launch_count}\u00D7 today")
            self._add_activity("launch", f"Launched {len(APP_DICT)} app(s)")
            if self._engine:
                self._engine.submit_event({
                    "type": "trigger",
                    "action": "launch_app",
                    "apps": list(APP_DICT.values()),
                })
        except Exception as e:
            self._add_activity("error", f"Launch failed: {e}")

    def _safe_btn_reset(self) -> None:
        try:
            self._launch_btn.configure(border_color=BTN_BORDER)
        except Exception:
            pass

    # ── Status bar ────────────────────────────────────────────────────────
    def _build_statusbar(self) -> None:
        bar = ctk.CTkFrame(self, height=STATUSBAR_H, fg_color=SURFACE_BG,
                           corner_radius=0, border_width=0)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)

        self._status_dot = ctk.CTkLabel(bar, text="\u25CF", text_color=GREEN_DOT,
                                        font=("Segoe UI", 11))
        self._status_dot.pack(side="left", padx=(SPACE * 2, 4))
        ctk.CTkLabel(bar, text="LISTENING", font=FONT_MONO_SM,
                     text_color=GREEN_DOT).pack(side="left")
        tk.Frame(bar, width=1, height=14, bg=BORDER_COLOR).pack(side="left", padx=SPACE)

        self._status_last = ctk.CTkLabel(bar, text="Last triggered: \u2014",
                                         font=FONT_MONO_SM, text_color=TEXT_MUTED)
        self._status_last.pack(side="left")
        tk.Frame(bar, width=0, bg=SURFACE_BG).pack(side="left", fill="x", expand=True)

        self._status_launch = ctk.CTkLabel(bar, text="Launched 0\u00D7 today",
                                           font=FONT_MONO_SM, text_color=TEXT_MUTED)
        self._status_launch.pack(side="right", padx=(0, SPACE * 3))

    # ── Animations ────────────────────────────────────────────────────────
    def _animate_scanline(self) -> None:
        if not self._alive:
            return
        try:
            self.bg_canvas.delete("scan")
            ly = int(self._scan_y)
            h = self.winfo_height()
            tb = TITLEBAR_H + 1
            bb = h - STATUSBAR_H - 1
            if tb < ly < bb:
                self.bg_canvas.create_line(
                    SIDEBAR_W, ly, self.winfo_width(), ly,
                    fill=ACCENT, width=1, tags="scan")
            self._scan_y += self._scan_dir * 1.2
            if self._scan_y > bb - 10:
                self._scan_dir = -1
            elif self._scan_y < tb + 10:
                self._scan_dir = 1
        except Exception:
            pass
        self.after(30, self._animate_scanline)

    def _blink_status_dot(self) -> None:
        if not self._alive:
            return
        try:
            cur = self._status_dot.cget("text_color")
            self._status_dot.configure(
                text_color=GREEN_DOT if cur == TEXT_MUTED else TEXT_MUTED)
        except Exception:
            pass
        self.after(1500, self._blink_status_dot)

    def _refresh_overlay(self) -> None:
        if not self._alive:
            return
        try:
            self.bg_canvas.delete("corners")
            w, h = self.winfo_width(), self.winfo_height()
            if w > 1 and h > 1:
                _draw_corner_accents(self.bg_canvas, w, h)
        except Exception:
            pass

    # ── Startup (4d) — delayed start + HKCU registry ─────────────────────
    def _startup_sequence(self) -> None:
        self._wait_for_desktop()
        self._ensure_startup_registry()
        self._hide_to_tray()

    def _wait_for_desktop(self, timeout: float = 30.0) -> None:
        import subprocess
        deadline = time.time() + timeout
        interval = 0.5
        attempts = 0
        while time.time() < deadline:
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq explorer.exe", "/NH"],
                    capture_output=True, text=True, timeout=3,
                )
                if "explorer.exe" in result.stdout:
                    elapsed = time.time() - (deadline - timeout)
                    debug_log(f"STARTUP: explorer.exe found after "
                              f"{attempts} attempts ({elapsed:.1f}s)")
                    return
            except Exception:
                pass
            attempts += 1
            interval = min(interval * 1.5, 5.0)
            time.sleep(interval)
        debug_log(f"STARTUP: explorer.exe not found after {timeout:.1f}s "
                  f"and {attempts} attempts — continuing anyway")

    def _ensure_startup_registry(self) -> None:
        if not self._settings_data.get("startup", False):
            return
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE,
            )
            startup_cmd = sys.executable
            if not getattr(sys, 'frozen', False):
                startup_cmd += f' "{os.path.abspath(__file__)}"'
            startup_cmd += ' --startup'
            winreg.SetValueEx(key, "Aditus", 0, winreg.REG_SZ, startup_cmd)
            winreg.CloseKey(key)
            debug_log("STARTUP: HKCU registry key written for Aditus")
        except Exception as e:
            debug_log(f"STARTUP: failed to write registry key: {e}")

    # ── Close / system tray ───────────────────────────────────────────────
    def _on_close_window(self) -> None:
        if self._settings_data.get("minimize_to_tray", True) and self._tray:
            self.withdraw()
        else:
            self.destroy()

    # ── System tray ───────────────────────────────────────────────────────
    def _hide_to_tray(self) -> None:
        try:
            self.withdraw()
            try:
                if os.path.isfile(ICO_PATH):
                    self.iconbitmap(ICO_PATH)
            except Exception:
                pass
            self.bind("<Map>", lambda e: self.deiconify())
        except Exception:
            pass

    def _cleanup_children(self) -> None:
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        if self._hotkey_trigger:
            try:
                self._hotkey_trigger.stop()
            except Exception:
                pass
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        debug_log("CLEANUP: all child processes stopped")

    def destroy(self) -> None:
        self._alive = False
        self._destroying = True
        self._cleanup_children()
        super().destroy()


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    debug_log(f"ADITUS STARTING: exe_dir={os.path.dirname(sys.executable) if getattr(sys,'frozen',False) else 'dev'} version={VERSION}")
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = AditusApp()
    debug_log("ADITUS RUNNING: mainloop entered")
    app.mainloop()
    debug_log("ADITUS EXIT: mainloop ended")
