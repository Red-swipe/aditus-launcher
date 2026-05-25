"""Isolate which thread pattern causes the hang."""
import sys, os, json, time, threading, subprocess

WORKER = os.path.join(os.path.dirname(__file__), "worker.py")

def make_event():
    return json.dumps({"type":"trigger","action":"launch_app","app_path":"C:\\Windows\\System32\\notepad.exe"})+"\n"

class Drainer:
    def __init__(self, stream):
        self._stream = stream
        self.ack_count = 0
        self._thread = threading.Thread(target=self._drain, daemon=True)
        self._thread.start()
    def _drain(self):
        for line in self._stream:
            if line.strip() == "ACK":
                self.ack_count += 1
    def count(self):
        return self.ack_count

def test_pattern(name, target, args):
    print(f"\n--- Test: {name} ---", flush=True)
    proc = subprocess.Popen(
        [sys.executable, WORKER],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,
    )
    print(f"  PID={proc.pid}", flush=True)
    d = Drainer(proc.stdout)
    
    t = threading.Thread(target=target, args=args, daemon=True)
    t.start()
    
    print(f"  Running for 3 seconds...", flush=True)
    time.sleep(3)
    
    print(f"  Closing stdin...", flush=True)
    try: proc.stdin.close()
    except Exception as e: print(f"  stdin close error: {e}", flush=True)
    
    print(f"  Waiting for exit...", flush=True)
    time.sleep(2)
    
    if proc.poll() is None:
        print(f"  Process still alive, sending SIGTERM...", flush=True)
        try: proc.terminate()
        except: pass
        try: proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            print(f"  HANG! Killing...", flush=True)
            proc.kill()
            proc.wait(timeout=5)
    
    try: out, err = proc.communicate(timeout=3)
    except: out, err = "", ""
    
    print(f"  exit={proc.returncode} acked={d.count()}", flush=True)
    if err:
        print(f"  stderr: {err[:300]}", flush=True)
    return proc.returncode

# Test each pattern individually
data = make_event()

def spam_target(stdin):
    while True:
        end = time.time() + 0.1
        while time.time() < end:
            try: stdin.write(data); stdin.flush()
            except: return

def slow_target(stdin):
    while True:
        try: stdin.write(data); stdin.flush()
        except: return
        time.sleep(1.0)

def burst_target(stdin):
    while True:
        end = time.time() + 1.0
        while time.time() < end:
            try: stdin.write(data); stdin.flush()
            except: return
        time.sleep(4.0)

def jitter_target(stdin):
    while True:
        time.sleep(random.uniform(0, 2.0))
        try: stdin.write(data); stdin.flush()
        except: return

# Only test spam for now since that produces the most load
test_pattern("SPAM FAST", spam_target, (open(os.devnull, 'w'),))  # dummy
