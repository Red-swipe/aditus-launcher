#!/usr/bin/env python
"""Comprehensive path trace: simulate install → launch cycle, log every step."""
import json, os, sys, shutil, subprocess, traceback
from datetime import datetime

DESKTOP_DEBUG = None

def get_debug_path():
    global DESKTOP_DEBUG
    if DESKTOP_DEBUG:
        return DESKTOP_DEBUG
    desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
    if not os.path.isdir(desktop):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    for f in os.listdir(desktop):
        if f.endswith(".txt") and f.startswith("aditus_debug_"):
            DESKTOP_DEBUG = os.path.join(desktop, f)
            return DESKTOP_DEBUG
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    DESKTOP_DEBUG = os.path.join(desktop, f"aditus_debug_{ts}.txt")
    return DESKTOP_DEBUG

def log(msg):
    p = get_debug_path()
    with open(p, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    print(msg)

def section(title):
    log(f"\n{'='*60}")
    log(f"  {title}")
    log(f"{'='*60}")

section("1. FILE SYSTEM STATE BEFORE INSTALL")

project = r"E:\A.G\aditus-launcher"
install_root = os.path.join(os.path.expanduser("~"), "Desktop", "AditusTest")

log(f"Project root: {project}")
log(f"Install root: {install_root}")

# Check source files
for fname, desc in [
    (os.path.join(project, "app", "Aditus.exe"), "Source Aditus.exe"),
    (os.path.join(project, "app", "main.pyw"), "Source main.pyw"),
    (os.path.join(project, "app", "config", "config_manager.py"), "Source config_manager.py"),
    (os.path.join(project, "app", "config", "aditus_config.json"), "Source aditus_config.json"),
    (os.path.join(project, "app", "runtime", "trigger_integration.py"), "Source trigger_integration.py"),
    (os.path.join(project, "dist", "AditusSetup.exe"), "Installer EXE"),
]:
    exists = os.path.isfile(fname)
    sz = os.path.getsize(fname) if exists else 0
    log(f"  {desc}: exists={exists} size={sz}")

section("2. SIMULATE INSTALLER PATH RESOLUTION")

# What the installer does:
install_path = os.path.join(install_root, "Aditus")
log(f"install_path (self.install_path): {install_path}")

# Simulate resource_path("app") as if frozen
log(f"(simulated) resource_path('app') -> sys._MEIPASS/app/")
log(f"(simulated) files at sys._MEIPASS/app/: main.pyw, config/, runtime/, utils/, Aditus.exe")
log(f"(simulated) files at sys._MEIPASS/: Aditus.exe (from explicit datas entry)")

# State file path
state_file = os.path.join(install_path, "install_state.json")
log(f"install_state.json path: {state_file}")

# Install state content (simulated)
exe_path = os.path.join(install_path, "Aditus.exe")
config_path = os.path.join(install_path, "aditus_config.json")
log(f"State would contain:")
log(f"  install_path: {install_path}")
log(f"  exe_path: {exe_path}")
log(f"  config_path: {config_path}")

section("3. SIMULATE LAUNCH DIALOG PATH RESOLUTION")

# The launch dialog reads:
state_path = os.path.join(install_path, "install_state.json")
log(f"Launch dialog reads state from: {state_path}")

if os.path.isfile(state_path):
    with open(state_path) as f:
        state = json.load(f)
    launch_exe = state.get("exe_path")
    log(f"State found! exe_path from state: {launch_exe}")
else:
    launch_exe = None
    log(f"State NOT found at {state_path}")
    fallback = os.path.join(install_path, "Aditus.exe")
    log(f"Would fallback to: {fallback}")
    launch_exe = fallback

launch_exists = os.path.isfile(launch_exe) if launch_exe else False
launch_size = os.path.getsize(launch_exe) if launch_exists else 0
log(f"Launch exe: {launch_exe}")
log(f"  exists={launch_exists}")
log(f"  size={launch_size}")
log(f"  launchable={launch_exists and launch_size > 0}")

section("4. SIMULATE ADITUS.EXE STARTUP PATH RESOLUTION")

exe_dir = os.path.dirname(launch_exe) if launch_exe and launch_exists else install_path
log(f"Aditus.exe directory (sys.executable dir): {exe_dir}")

state_candidates = [
    os.path.join(exe_dir, "install_state.json"),
]
log(f"State search candidates:")
for c in state_candidates:
    log(f"  {c} -> exists={os.path.isfile(c)}")

if os.path.isfile(state_candidates[0]):
    with open(state_candidates[0]) as f:
        found_state = json.load(f)
    log(f"State FOUND:")
    log(f"  install_path: {found_state.get('install_path')}")
    log(f"  exe_path: {found_state.get('exe_path')}")
    log(f"  config_path: {found_state.get('config_path')}")
    
    cfg = found_state.get("config_path", "")
    if cfg and os.path.isfile(cfg):
        resolved_config = cfg
        log(f"Config path (from state, exists): {resolved_config}")
    else:
        frozen_fallback = os.path.join(exe_dir, "aditus_config.json")
        log(f"Config path (frozen fallback): {frozen_fallback} -> exists={os.path.isfile(frozen_fallback)}")
        resolved_config = frozen_fallback
else:
    log(f"State NOT found")
    frozen_fallback = os.path.join(exe_dir, "aditus_config.json")
    log(f"Config path (frozen fallback, no state): {frozen_fallback} -> exists={os.path.isfile(frozen_fallback)}")
    resolved_config = frozen_fallback

log(f"FINAL CONFIG_PATH: {resolved_config}")
log(f"Config file exists: {os.path.isfile(resolved_config)}")
if os.path.isfile(resolved_config):
    try:
        with open(resolved_config) as f:
            cfg_data = json.load(f)
        log(f"Config content: trigger={cfg_data.get('trigger',{}).get('type','?')}")
    except Exception as e:
        log(f"Config read error: {e}")

section("5. VERIFY DESKTOP DEBUG FILE")
debug_path = get_debug_path()
log(f"Desktop debug file: {debug_path}")
log(f"Debug file exists: {os.path.isfile(debug_path)}")
if os.path.isfile(debug_path):
    log("--- DEBUG FILE CONTENT ---")
    with open(debug_path) as f:
        log(f.read())

section("6. SUMMARY")
log(f"Install path: {install_path}")
log(f"State file: {state_file} {'EXISTS' if os.path.isfile(state_file) else 'MISSING'}")
log(f"Exe path: {launch_exe}")
log(f"Exe ready: {launch_exists and launch_size > 0}")
log(f"Config resolved: {resolved_config}")
log(f"Config exists: {os.path.isfile(resolved_config)}")
log(f"\nROOT CAUSE IDENTIFIED: (no install performed yet)")
