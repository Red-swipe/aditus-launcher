"""Quick 2-iteration stress test to verify everything works"""
import sys, os, json, time, random, threading, subprocess, signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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

def spam(stdin):
    data = make_event()
    while True:
        end = time.time() + 0.1
        while time.time() < end:
            try:
                stdin.write(data); stdin.flush()
            except: return

def slow(stdin):
    data = make_event()
    while True:
        try: stdin.write(data); stdin.flush()
        except: return
        time.sleep(1.0)

def burst(stdin):
    data = make_event()
    while True:
        end = time.time() + 1.0
        while time.time() < end:
            try: stdin.write(data); stdin.flush()
            except: return
        time.sleep(4.0)

def jitter(stdin):
    data = make_event()
    while True:
        time.sleep(random.uniform(0, 2.0))
        try: stdin.write(data); stdin.flush()
        except: return

def killer(proc):
    while True:
        time.sleep(random.uniform(1.0, 5.0))
        try: os.kill(proc.pid, signal.SIGTERM)
        except: pass
        if proc.poll() is not None: return

for it in range(2):
    print(f"\n=== QUICK ITERATION {it+1} ===")
    proc = subprocess.Popen([sys.executable, WORKER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=0)
    d = Drainer(proc.stdout)
    
    threads = [
        threading.Thread(target=spam, args=(proc.stdin,), daemon=True),
        threading.Thread(target=slow, args=(proc.stdin,), daemon=True),
        threading.Thread(target=burst, args=(proc.stdin,), daemon=True),
        threading.Thread(target=jitter, args=(proc.stdin,), daemon=True),
        threading.Thread(target=killer, args=(proc,), daemon=True),
    ]
    for t in threads: t.start()
    
    time.sleep(5)
    
    try: proc.stdin.close()
    except: pass
    
    time.sleep(1)
    if proc.poll() is None:
        try: os.kill(proc.pid, signal.SIGTERM)
        except: pass
        try: proc.wait(timeout=4)
        except:
            try: os.kill(proc.pid, signal.SIGKILL)
            except: pass
            proc.wait(timeout=5)
    
    try: _, err = proc.communicate(timeout=3)
    except: err = ""
    
    print(f"  exit={proc.returncode} acked={d.count()} alive={proc.poll() is not None}")
    if err: print(f"  stderr: {err[:200]}")
    time.sleep(0.5)

print("\n=== QUICK TEST DONE ===")
