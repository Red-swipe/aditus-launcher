import logging
import queue as _queue_module
import threading

from app.runtime.app_launcher import AppLauncher
from app.runtime.clap_detector import ClapDetector

logger = logging.getLogger("aditus.engine")


# ── Strict contract ─────────────────────────────────────────────────────
# The runtime engine:
#   • MAY ONLY read install_state.json for system location (never guess).
#   • MAY ONLY read aditus_config.json for behaviour (triggers, apps, UI).
#   • MUST NOT infer, guess, or fall back any paths.
#   • MUST stop execution and log error if required keys are missing.
#
# Validation of both files happens once at startup in main.pyw
# (_validate_runtime_contract).  The engine itself never opens either file.
# ────────────────────────────────────────────────────────────────────────


class RuntimeEngine:
    def __init__(self, enable_clap: bool = True, get_apps=None):
        self._launch_queue = _queue_module.Queue()
        self._launcher = AppLauncher()
        self._running = False
        self._thread = None
        self._get_apps = get_apps or (lambda: [])
        self._clap_detector = (
            ClapDetector(callback=self._on_clap) if enable_clap else None
        )

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        if self._clap_detector:
            self._clap_detector.start()

    def stop(self):
        self._running = False
        if self._clap_detector:
            self._clap_detector.stop()

    def submit_event(self, event: dict):
        self._launch_queue.put_nowait(event)

    def _on_clap(self):
        self._launch_queue.put_nowait({
            "type": "trigger",
            "action": "launch_app",
            "apps": self._get_apps(),
        })

    def _loop(self):
        while self._running:
            try:
                event = self._launch_queue.get(timeout=0.1)
                if (
                    event is not None
                    and event.get("type") == "trigger"
                    and event.get("action") == "launch_app"
                ):
                    self._launcher.launch_all(event.get("apps", []))
            except _queue_module.Empty:
                pass
            except Exception:
                logger.exception("Error in runtime engine loop")
