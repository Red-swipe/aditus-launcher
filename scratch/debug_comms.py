"""Test subprocess.communicate behavior when child is killed"""
import subprocess, sys, time, signal, os

# Simple worker that just reads stdin and echoes to stdout
worker_code = """
import sys
for line in sys.stdin:
    print("ACK", flush=True)
print("STOPPING", flush=True)
sys.exit(0)
"""

worker_file = os.path.join(os.path.dirname(__file__), "_test_echo_worker.py")
with open(worker_file, "w") as f:
    f.write(worker_code)

print("1. Test graceful shutdown", flush=True)
proc = subprocess.Popen(
    [sys.executable, worker_file],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0,
)
time.sleep(0.3)
proc.stdin.write("hello\n"); proc.stdin.flush()
time.sleep(0.2)
proc.stdin.close()
out, err = proc.communicate(timeout=5)
print(f"   Graceful: exit={proc.returncode} out={out.strip()}", flush=True)

print("\n2. Test kill then communicate", flush=True)
proc = subprocess.Popen(
    [sys.executable, worker_file],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0,
)
time.sleep(0.3)
os.kill(proc.pid, signal.SIGTERM)
time.sleep(0.5)
print(f"   After kill: poll={proc.poll()}", flush=True)
try:
    out, err = proc.communicate(timeout=5)
    print(f"   communicate OK: exit={proc.returncode} out={out.strip()}", flush=True)
except Exception as e:
    print(f"   communicate FAILED: {e}", flush=True)

print("\n3. Test terminate then communicate", flush=True)
proc = subprocess.Popen(
    [sys.executable, worker_file],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0,
)
time.sleep(0.3)
proc.terminate()
time.sleep(0.5)
print(f"   After terminate: poll={proc.poll()}", flush=True)
try:
    out, err = proc.communicate(timeout=5)
    print(f"   communicate OK: exit={proc.returncode} out={out.strip()}", flush=True)
except Exception as e:
    print(f"   communicate FAILED: {e}", flush=True)

print(f"\n4. Test killing then reading stdout manually", flush=True)
proc = subprocess.Popen(
    [sys.executable, worker_file],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0,
)
time.sleep(0.3)
os.kill(proc.pid, signal.SIGTERM)
time.sleep(0.5)
proc.stdin.close()
try:
    stdout_data = proc.stdout.read()
    stderr_data = proc.stderr.read()
    print(f"   Manual read OK: stdout={stdout_data.strip()}", flush=True)
except Exception as e:
    print(f"   Manual read FAILED: {e}", flush=True)
proc.wait(timeout=5)
print(f"   Exit code: {proc.returncode}", flush=True)

os.remove(worker_file)
print("\nDone", flush=True)
