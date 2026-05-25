import subprocess, sys, time, os

worker = os.path.join(os.path.dirname(__file__), "worker.py")
proc = subprocess.Popen(
    [sys.executable, worker],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0,
)
time.sleep(0.5)
proc.stdin.write(
    '{"type":"trigger","action":"launch_app","app_path":"C:\\\\Windows\\\\System32\\\\notepad.exe"}\n'
)
proc.stdin.flush()
time.sleep(0.3)
proc.stdin.close()
try:
    out, err = proc.communicate(timeout=5)
    print(f"OK: exit={proc.returncode} out={out.strip()}")
except subprocess.TimeoutExpired:
    proc.kill()
    proc.communicate(timeout=5)
    print(f"TIMEOUT: exit={proc.returncode}")
