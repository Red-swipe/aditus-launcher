"""Worker subprocess for Aditus stress testing.

Reads JSON events from stdin (one per line) and submits them to the
RuntimeEngine.  Sends acknowledgements to stdout.
"""

import sys
import os
import json
import logging
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

from app.runtime.runtime_engine import RuntimeEngine

engine: RuntimeEngine | None = None
stop_event = threading.Event()


def stdin_reader():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        if line == "SHUTDOWN":
            stop_event.set()
            break
        try:
            event = json.loads(line)
            if engine:
                engine.submit_event(event)
                print("ACK", flush=True)
        except json.JSONDecodeError as e:
            print(f"ERR {e}", flush=True)
    # stdin EOF (pipe closed by parent) -> also shutdown
    stop_event.set()


def main():
    global engine
    engine = RuntimeEngine()
    engine.start()

    reader_thread = threading.Thread(target=stdin_reader, daemon=True)
    reader_thread.start()

    # Wait for shutdown signal
    stop_event.wait()

    print("STOPPING", flush=True)
    engine.stop()
    print("STOPPED", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
