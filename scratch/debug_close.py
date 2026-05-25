"""Test stdin.close() behavior when child is killed by os.kill"""
import subprocess, sys, time, signal, os, threading

worker_code = """
import sys
for line in sys.stdin:
    print("ACK", flush=True)
print("STOPPING", flush=True)
sys.exit(0)
"""

worker_file = os.path.join(os.path.dirname(__file__), "_test_echo2.py")
with open(worker_file, "w") as f:
    f.write(worker_code)

# Start worker
proc = subprocess.Popen(
    [sys.executable, worker_file],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    stderr=subprocess.PIPE, text=True, bufsize=0,
)
print(f"PID={proc.pid}", flush=True)

# Write events in threads (like stress test does)
def writer(s):
    while True:
        try:
            s.write("data\n"); s.flush()
        except: return

for _ in range(5):
    t = threading.Thread(target=writer, args=(proc.stdin,), daemon=True)
    t.start()

time.sleep(0.5)

# Kill worker
print("Killing worker...", flush=True)
os.kill(proc.pid, signal.SIGTERM)
time.sleep(0.3)

p = proc.poll()
print(f"poll={p}", flush=True)

# Now try to close stdin
print("Closing stdin...", flush=True)
try:
    proc.stdin.close()
    print("stdin closed OK", flush=True)
except Exception as e:
    print(f"stdin close error: {type(e).__name__}: {e}", flush=True)

print("Calling communicate...", flush=True)
try:
    out, err = proc.communicate(timeout=5)
    print(f"communicate OK: exit={proc.returncode}", flush=True)
except Exception as e:
    print(f"communicate error: {e}", flush=True)

os.remove(worker_file)
print("Done", flush=True)
