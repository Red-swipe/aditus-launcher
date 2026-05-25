"""Debug: test worker interaction"""
import subprocess
import sys
import time
import threading
import os

worker = os.path.join(os.path.dirname(__file__), "worker.py")
print("Starting...", flush=True)
proc = subprocess.Popen(
    [sys.executable, worker],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0,
)
print(f"PID: {proc.pid}", flush=True)
time.sleep(1)
print(f"Alive: {proc.poll() is None}", flush=True)

print("Writing events...", flush=True)
for i in range(10):
    try:
        proc.stdin.write(
            '{"type":"trigger","action":"launch_app","app_path":"C:\\\\Windows\\\\System32\\\\notepad.exe"}\n'
        )
        proc.stdin.flush()
    except Exception as e:
        print(f"Write error: {e}", flush=True)
        break
    time.sleep(0.1)
print("Wrote 10 events", flush=True)

# Try reading stdout
def reader():
    for line in proc.stdout:
        print(f"STDOUT: {line.strip()}", flush=True)

t = threading.Thread(target=reader, daemon=True)
t.start()
time.sleep(2)

print("Closing stdin...", flush=True)
try:
    proc.stdin.close()
except Exception as e:
    print(f"stdin close error: {e}", flush=True)

time.sleep(2)
print(f"Poll: {proc.poll()}", flush=True)
print(f"Exit code: {proc.returncode}", flush=True)
print("Done", flush=True)
