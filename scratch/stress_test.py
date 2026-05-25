"""Aditus Concurrency Stress Test.

Launches the Aditus worker as a real subprocess, bombards it with events
from 5 concurrent trigger threads, force-kills and restarts for 10 iterations.
"""
import sys, os, json, time, random, threading, subprocess, signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
WORKER = os.path.join(os.path.dirname(__file__), "worker.py")
ITERS = 10
DURATION = 12
TIMEOUT = 4

all_ok = True
failures = []

def evt():
    return json.dumps({"type":"trigger","action":"launch_app","app_path":"C:\\Windows\\System32\\notepad.exe"})+"\n"

def spam(s, stop):
    d=evt()
    while not stop.is_set():
        e=time.time()+0.1
        while time.time()<e and not stop.is_set():
            try: s.write(d);s.flush()
            except: return

def slow(s, stop):
    d=evt()
    while not stop.is_set():
        try: s.write(d);s.flush()
        except: return
        stop.wait(1)

def burst(s, stop):
    d=evt()
    while not stop.is_set():
        e=time.time()+1
        while time.time()<e and not stop.is_set():
            try: s.write(d);s.flush()
            except: return
        if stop.is_set(): return
        stop.wait(4)

def jitter(s, stop):
    d=evt()
    while not stop.is_set():
        if stop.wait(random.uniform(0,2)): return
        try: s.write(d);s.flush()
        except: return

def killer(p, stop):
    while not stop.is_set():
        if stop.wait(random.uniform(1,5)): return
        try: os.kill(p.pid, signal.SIGTERM)
        except: pass

def run(n):
    global all_ok
    def ts(): return f"[{time.time():.1f}]"
    print(f"\n{ts()} === ITER {n+1}/{ITERS} ===", flush=True)

    proc = subprocess.Popen(
        [sys.executable, WORKER],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=0,
    )
    print(f"{ts()}  PID={proc.pid} alive={proc.poll() is None}", flush=True)

    stop = threading.Event()

    threads = [
        threading.Thread(target=spam, args=(proc.stdin, stop), daemon=True),
        threading.Thread(target=slow, args=(proc.stdin, stop), daemon=True),
        threading.Thread(target=burst, args=(proc.stdin, stop), daemon=True),
        threading.Thread(target=jitter, args=(proc.stdin, stop), daemon=True),
        threading.Thread(target=killer, args=(proc, stop), daemon=True),
    ]
    for t in threads: t.start()

    # Wait for DURATION sec or early death
    for _ in range(DURATION):
        time.sleep(1)
        if proc.poll() is not None:
            print(f"{ts()}  Worker died early (exit={proc.returncode})", flush=True)
            break

    # Signal ALL threads to stop BEFORE closing stdin
    print(f"{ts()}  Signaling stop...", flush=True)
    stop.set()
    time.sleep(0.3)

    # Close stdin (threads have stopped)
    print(f"{ts()}  Closing stdin...", flush=True)
    try: proc.stdin.close()
    except Exception as e: print(f"{ts()}  stdin close: {e}", flush=True)

    time.sleep(1)
    p = proc.poll()
    print(f"{ts()}  poll={p}", flush=True)
    if p is None:
        print(f"{ts()}  Sending SIGTERM...", flush=True)
        try: proc.terminate()
        except Exception as e: print(f"{ts()}  term: {e}", flush=True)
        try: proc.wait(timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            print(f"{ts()}  HANG! Killing...", flush=True)
            proc.kill()
            proc.wait(timeout=5)

    print(f"{ts()}  Reading output...", flush=True)
    try:
        out, err = proc.communicate(timeout=5)
        print(f"{ts()}  communicate OK", flush=True)
    except Exception as e:
        print(f"{ts()}  communicate error: {e}", flush=True)
        out, err = "", ""

    acks = out.count("ACK\n")
    alive = proc.poll() is None
    ec = proc.returncode
    print(f"{ts()}  ACKs={acks} exit={ec} alive={alive}", flush=True)
    if err:
        print(f"{ts()}  stderr(last): {err.rsplit(chr(10),1)[-1][:200]}", flush=True)

    ok = True; reason = ""
    if alive: ok=False; reason="still alive"
    elif ec is not None and ec>0: ok=False; reason=f"exit {ec}"
    elif ec is None: ok=False; reason="no exit"

    if ok: print(f"{ts()}  -> PASS ({reason or 'clean'})", flush=True)
    else:
        print(f"{ts()}  -> FAIL: {reason}", flush=True)
        all_ok=False; failures.append(f"Iter {n+1}: {reason}")

print("ADITUS STRESS TEST", flush=True)
print(f"ITERS={ITERS} DUR={DURATION}s", flush=True)

for i in range(ITERS):
    run(i)
    time.sleep(0.5)

passed = ITERS - len(failures)
print(f"\nPassed {passed}/{ITERS}", flush=True)
if all_ok:
    print("\nTRUE", flush=True)
else:
    print("\nFALSE", flush=True)
    for f in failures: print(f"  {f}", flush=True)
