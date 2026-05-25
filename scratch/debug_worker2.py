"""Debug: test worker shutdown properly"""
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

# Reader thread
acks = []

def reader():
    for line in proc.stdout:
        line = line.strip()
        acks.append(line)
        print(f"STDOUT: {line}", flush=True)

t = threading.Thread(target=reader, daemon=True)
t.start()

stderr_lines = []
def stderr_reader():
    for line in proc.stderr:
        stderr_lines.append(line)

s = threading.Thread(target=stderr_reader, daemon=True)
s.start()

time.sleep(1)

# Send just 3 events then SHUTDOWN
for i in range(3):
    proc.stdin.write(
        '{"type":"trigger","action":"launch_app","app_path":"C:\\\\Windows\\\\System32\\\\notepad.exe"}\n'
    )
    proc.stdin.flush()
    time.sleep(0.1)

print("Sending SHUTDOWN...", flush=True)
proc.stdin.write("SHUTDOWN\n")
proc.stdin.flush()
time.sleep(2)

print(f"Poll: {proc.poll()}", flush=True)
print(f"ACKs: {acks}", flush=True)

# Try communicate
try:
    out, err = proc.communicate(timeout=5)
    print(f"communicate OK: {out[:100]}", flush=True)
    print(f"Exit code: {proc.returncode}", flush=True)
except subprocess.TimeoutExpired:
    print("communicate TIMEOUT - killing", flush=True)
    proc.kill()
    out, err = proc.communicate(timeout=5)
    print(f"After kill. Exit code: {proc.returncode}", flush=True)

print("Done", flush=True)
