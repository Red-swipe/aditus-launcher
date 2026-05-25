# runtime_engine.py
"""Core Runtime Engine for Aditus.

Implements an event‑driven state machine that consumes trigger events from a
thread‑safe queue, integrates with the :class:`ConfigManager`, and launches
applications via :class:`AppLauncher`.

This module has **no UI dependencies** and runs in its own background thread.
"""

import threading
import queue
import logging
from typing import Any, Dict

from app.config.config_manager import ConfigManager
from .event_queue import EventQueue
from .app_launcher import AppLauncher

logger = logging.getLogger(__name__)


class RuntimeEngine:
    """Runtime Engine handling the main event loop.

    States:
        STOPPED – engine is idle.
        RUNNING – consumes events and processes them.
    """

    class State:
        STOPPED = "stopped"
        RUNNING = "running"

    def __init__(self, event_queue: EventQueue | None = None, launcher: AppLauncher | None = None):
        # singletons / shared resources
        self._config = ConfigManager()
        self._event_queue = event_queue or EventQueue()
        self._launcher = launcher or AppLauncher()
        self._state = self.State.STOPPED
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        logger.debug("RuntimeEngine instantiated – state=%s", self._state)

    # ---------------------------------------------------------------------
    # Lifecycle control
    # ---------------------------------------------------------------------
    def start(self) -> None:
        """Start the engine in a background daemon thread.

        The call is idempotent – invoking ``start`` when already running does
        nothing.
        """
        if self._state == self.State.RUNNING:
            logger.info("RuntimeEngine already running.")
            return
        logger.info("Starting RuntimeEngine thread.")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="RuntimeEngineThread", daemon=True)
        self._thread.start()
        self._state = self.State.RUNNING
        logger.debug("RuntimeEngine state transitioned to RUNNING.")

    def stop(self) -> None:
        """Signal the engine to stop and wait for the thread to finish.

        Idempotent – calling ``stop`` when already stopped is a no‑op.
        """
        if self._state == self.State.STOPPED:
            logger.info("RuntimeEngine already stopped.")
            return
        logger.info("Stopping RuntimeEngine.")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._state = self.State.STOPPED
        logger.debug("RuntimeEngine state transitioned to STOPPED.")

    # ---------------------------------------------------------------------
    # Core loop
    # ---------------------------------------------------------------------
    def _run(self) -> None:
        """Background loop that pulls events until a stop is requested.

        A short timeout on ``queue.get`` allows the loop to check the stop flag
        regularly, ensuring a responsive shutdown.
        """
        logger.debug("RuntimeEngine thread entered run loop.")
        while not self._stop_event.is_set():
            try:
                # ``timeout`` keeps the thread responsive to stop requests.
                event = self._event_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._handle_event(event)
            except Exception as exc:
                logger.exception("Unhandled exception while processing event: %s", exc)
        logger.debug("RuntimeEngine thread exiting run loop.")

    # ---------------------------------------------------------------------
    # Event handling
    # ---------------------------------------------------------------------
    def _handle_event(self, event: Dict[str, Any]) -> None:
        """Dispatch an incoming event based on its ``type``.

        Supported event schema (minimum)::

            {
                "type": "trigger",
                "action": "launch_app",
                "app_path": "C:/Program Files/MyApp/app.exe"
            }
        """
        event_type = event.get("type")
        if event_type == "trigger":
            self._process_trigger(event)
        else:
            logger.warning("Received unknown event type: %s", event_type)

    def _process_trigger(self, trigger_event: Dict[str, Any]) -> None:
        """Handle a trigger‑related event.

        Currently the only supported action is ``launch_app`` which delegates to
        :class:`AppLauncher`.  If ``app_path`` is omitted the engine falls back to
        a default path stored in the config under ``launch_app_path``.
        """
        action = trigger_event.get("action")
        if action != "launch_app":
            logger.warning("Unsupported trigger action: %s", action)
            return

        app_path = trigger_event.get("app_path")
        if not app_path:
            # Config fallback – ``launch_app_path`` is optional; if missing we log.
            app_path = self._config.get(["launch_app_path"])  # type: ignore[arg-type]
        if not app_path:
            logger.error("No application path provided for launch_app event.")
            return

        self._launcher.launch(app_path)

    # ---------------------------------------------------------------------
    # Public API helpers
    # ---------------------------------------------------------------------
    def submit_event(self, event: Dict[str, Any]) -> None:
        """Convenient wrapper for external code to push an event.
        """
        self._event_queue.put(event)

    # ---------------------------------------------------------------------
    # Properties – expose internal components for testing / integration
    # ---------------------------------------------------------------------
    @property
    def state(self) -> str:
        return self._state

    @property
    def config(self) -> ConfigManager:
        return self._config

    @property
    def event_queue(self) -> EventQueue:
        return self._event_queue

    @property
    def launcher(self) -> AppLauncher:
        return self._launcher

# End of runtime_engine.py
