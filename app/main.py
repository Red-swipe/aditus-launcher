#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Aditus — Main Dashboard UI (CustomTkinter)

Window  : 900 × 560, non-resizable
Palette : #212A3E  #394867  #9BA4B5  #F1F6F9
Features:
  • Emoji sidebar (🏠 ☰ ⚙️) on dark background with left accent border
  • Subtle dot-grid canvas background (same technique as installer)
  • Pill-shaped trigger selector (top-right of main area)
  • App cards with icon emoji, bold name, ✕ remove button, subtle border
  • "Launch Now" button — wide, rounded, light on dark
  • Stats section: last triggered timestamp + session count
  • Bottom status bar: green dot + "Listening" (left), version (right)
  • --startup flag hides window to system tray

Reads layout from aditus_config.json if it exists, otherwise uses defaults.
"""

import os
import sys
import json
import threading
import tkinter as tk
import customtkinter as ctk

# ────────────────────────────────────────────────────────────────────────────
# Color palette
# ────────────────────────────────────────────────────────────────────────────
DARK_BG  = "#212A3E"
SURFACE  = "#394867"
MUTED    = "#9BA4B5"
LIGHT    = "#F1F6F9"
GREEN    = "#4ADE80"
VERSION  = "v0.1.0"

# ────────────────────────────────────────────────────────────────────────────
# Config loader
# ────────────────────────────────────────────────────────────────────────────
def load_config():
    """Load aditus_config.json from app/config/ or the same dir as this file."""
    # Try app/config/ first (installed layout), then same dir as main.py
    candidates = [
        os.path.join(os.path.dirname(__file__), "config", "aditus_config.json"),
        os.path.join(os.path.dirname(__file__), "aditus_config.json"),
    ]
    for cfg_path in candidates:
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

    return {
        "trigger": {"type": "clap", "hotkey": "ctrl+shift+j"},
        "apps": [],
    }

CONFIG = load_config()

# Derive trigger options list
_trigger_section = CONFIG.get("trigger", {})
TRIGGER_OPTIONS = _trigger_section.get("options", ["clap", "hotkey", "timer"])
ACTIVE_TRIGGER  = _trigger_section.get("type", TRIGGER_OPTIONS[0])
APP_LIST        = CONFIG.get("apps", [])

# Default demo apps when the config list is empty
DEFAULT_APPS = [
    {"name": "Spotify",   "icon": "🎵"},
    {"name": "Discord",   "icon": "💬"},
    {"name": "Notepad++", "icon": "📝"},
]
if not APP_LIST:
    APP_LIST = DEFAULT_APPS


# ────────────────────────────────────────────────────────────────────────────
# System-tray placeholder
# ────────────────────────────────────────────────────────────────────────────
def hide_to_tray(root):
    """Withdraw the window; restore on taskbar click."""
    root.withdraw()
    try:
        import pathlib, tempfile
        ico = pathlib.Path(tempfile.gettempdir()) / "aditus_tray.ico"
        if not ico.is_file():
            from PIL import Image
            Image.new("RGBA", (16, 16), (33, 42, 62, 255)).save(ico, format="ICO")
        root.iconbitmap(str(ico))
    except Exception:
        pass
    root.bind("<Map>", lambda e: root.deiconify())


# ────────────────────────────────────────────────────────────────────────────
# UI Construction
# ────────────────────────────────────────────────────────────────────────────
class AditusApp(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=DARK_BG)
        self.title("Aditus")
        self.geometry("900x560")
        self.resizable(False, False)

        # ── dot-grid background canvas ──────────────────────────────────
        self.bg_canvas = ctk.CTkCanvas(self, bg=DARK_BG, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._draw_dot_grid()

        # ── sidebar ─────────────────────────────────────────────────────
        self._build_sidebar()

        # ── main content (floated over canvas) ──────────────────────────
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(side="right", fill="both", expand=True)

        self._build_header()
        self._build_cards()
        self._build_launch_button()
        self._build_stats()
        self._build_status_bar()

        # ── --startup handling ──────────────────────────────────────────
        if "--startup" in sys.argv:
            self.after(50, lambda: hide_to_tray(self))

    # ────────────────────────────────────────────────────────────────────
    # Dot grid (same technique as installer)
    # ────────────────────────────────────────────────────────────────────
    def _draw_dot_grid(self):
        for x in range(0, 920, 28):
            for y in range(0, 580, 28):
                self.bg_canvas.create_oval(x, y, x + 2, y + 2,
                                           fill=SURFACE, outline="")

    # ────────────────────────────────────────────────────────────────────
    # Sidebar
    # ────────────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        # Outer container: thin accent border on the right edge
        # Outer container: thin accent border on the right edge
        sidebar_border = ctk.CTkFrame(self, width=72, fg_color=SURFACE, corner_radius=0)
        sidebar_border.pack(side="left", fill="y")

        sidebar = ctk.CTkFrame(sidebar_border, width=69, fg_color=DARK_BG, corner_radius=0)
        sidebar.pack(side="left", fill="y")

        icons = [("🏠", "Home"), ("☰", "List"), ("⚙️", "Settings")]
        self._sidebar_buttons = []

        for idx, (emoji, tooltip) in enumerate(icons):
            btn = ctk.CTkButton(
                sidebar,
                text=emoji,
                width=50, height=50,
                fg_color="transparent",
                hover_color=SURFACE,
                text_color=MUTED,
                font=("Segoe UI Emoji", 22),
                corner_radius=12,
                command=lambda i=idx: self._on_sidebar(i),
            )
            btn.pack(pady=(20 if idx == 0 else 8, 0))
            self._sidebar_buttons.append(btn)

        # Highlight the first button by default
        self._sidebar_buttons[0].configure(fg_color=SURFACE, text_color=LIGHT)

    def _on_sidebar(self, index):
        for i, btn in enumerate(self._sidebar_buttons):
            if i == index:
                btn.configure(fg_color=SURFACE, text_color=LIGHT)
            else:
                btn.configure(fg_color="transparent", text_color=MUTED)

    # ────────────────────────────────────────────────────────────────────
    # Header row (title left, pill trigger selector right)
    # ────────────────────────────────────────────────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=56)
        header.pack(fill="x", padx=24, pady=(20, 0))
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="Dashboard",
            font=("Segoe UI", 22, "bold"), text_color=LIGHT,
        ).pack(side="left", pady=8)

        # Pill-shaped trigger selector
        pill_frame = ctk.CTkFrame(header, fg_color=SURFACE, corner_radius=20,
                                  height=38)
        pill_frame.pack(side="right", pady=9)
        pill_frame.pack_propagate(False)

        self._trigger_buttons = []
        for opt in TRIGGER_OPTIONS:
            is_active = (opt == ACTIVE_TRIGGER)
            tb = ctk.CTkButton(
                pill_frame,
                text=opt.title(),
                width=72, height=30,
                corner_radius=15,
                fg_color=LIGHT if is_active else "transparent",
                text_color=DARK_BG if is_active else MUTED,
                hover_color=MUTED,
                font=("Segoe UI", 12, "bold"),
                command=lambda o=opt: self._select_trigger(o),
            )
            tb.pack(side="left", padx=3, pady=4)
            self._trigger_buttons.append((opt, tb))

    def _select_trigger(self, selected):
        for opt, tb in self._trigger_buttons:
            if opt == selected:
                tb.configure(fg_color=LIGHT, text_color=DARK_BG)
            else:
                tb.configure(fg_color="transparent", text_color=MUTED)

    # ────────────────────────────────────────────────────────────────────
    # App cards
    # ────────────────────────────────────────────────────────────────────
    def _build_cards(self):
        self.cards_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.cards_frame.pack(fill="both", expand=True, padx=24, pady=(16, 0))

        for i in range(3):
            self.cards_frame.grid_columnconfigure(i, weight=1)
        self.cards_frame.grid_rowconfigure(0, weight=1)

        self._cards = []
        for idx, app in enumerate(APP_LIST[:3]):
            self._create_card(idx, app)

    def _create_card(self, col, app_info):
        name = app_info.get("name", f"App {col + 1}")
        icon = app_info.get("icon", "📦")

        card = ctk.CTkFrame(
            self.cards_frame,
            corner_radius=14,
            fg_color=SURFACE,
            border_width=1,
            border_color=SURFACE,
        )
        card.grid(row=0, column=col, padx=8, pady=8, sticky="nsew")

        # Top row: emoji icon (left) + ✕ remove button (right)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(14, 0))

        ctk.CTkLabel(
            top, text=icon,
            font=("Segoe UI Emoji", 26),
            text_color=LIGHT,
        ).pack(side="left")

        remove_btn = ctk.CTkButton(
            top, text="✕",
            width=28, height=28,
            fg_color="transparent",
            hover_color="#4a556b",
            text_color=MUTED,
            font=("Segoe UI", 14),
            corner_radius=8,
            command=lambda c=col: self._remove_card(c),
        )
        remove_btn.pack(side="right")

        # App name
        ctk.CTkLabel(
            card, text=name,
            font=("Segoe UI", 15, "bold"),
            text_color=LIGHT,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(10, 4))

        # Subtitle
        ctk.CTkLabel(
            card, text="Ready to launch",
            font=("Segoe UI", 11),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 14))

        self._cards.append(card)

    def _remove_card(self, index):
        if index < len(self._cards):
            self._cards[index].destroy()

    # ────────────────────────────────────────────────────────────────────
    # Launch button
    # ────────────────────────────────────────────────────────────────────
    def _build_launch_button(self):
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent",
                                 height=56)
        btn_frame.pack(fill="x", padx=24, pady=(4, 0))

        ctk.CTkButton(
            btn_frame,
            text="Launch Now",
            width=320, height=44,
            corner_radius=22,
            fg_color=LIGHT,
            text_color=DARK_BG,
            hover_color=MUTED,
            font=("Segoe UI", 15, "bold"),
        ).pack(pady=6)

    # ────────────────────────────────────────────────────────────────────
    # Stats row (last triggered + session count)
    # ────────────────────────────────────────────────────────────────────
    def _build_stats(self):
        stats = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=40)
        stats.pack(fill="x", padx=24, pady=(6, 0))
        stats.pack_propagate(False)

        ctk.CTkLabel(
            stats, text="Last triggered:  –",
            font=("Segoe UI", 11), text_color=MUTED,
        ).pack(side="left")

        ctk.CTkLabel(
            stats, text="Launched 0 times today",
            font=("Segoe UI", 11), text_color=MUTED,
        ).pack(side="right")

    # ────────────────────────────────────────────────────────────────────
    # Bottom status bar
    # ────────────────────────────────────────────────────────────────────
    def _build_status_bar(self):
        bar = ctk.CTkFrame(self, height=32, fg_color=SURFACE, corner_radius=0)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)

        # Left: green dot + Listening
        ctk.CTkLabel(
            bar, text="●",
            text_color=GREEN,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left", padx=(12, 4))

        ctk.CTkLabel(
            bar, text="Listening",
            text_color=LIGHT,
            font=("Segoe UI", 11),
        ).pack(side="left")

        # Right: version
        ctk.CTkLabel(
            bar, text=VERSION,
            text_color=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="right", padx=14)


# ────────────────────────────────────────────────────────────────────────────
# Entry point
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = AditusApp()
    app.mainloop()
