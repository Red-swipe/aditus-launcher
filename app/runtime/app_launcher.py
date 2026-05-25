# app_launcher.py
"""Application launcher used by the runtime engine.

Provides a single responsibility: safely start external executables.
It tracks launched processes to avoid duplicate launches of the same binary
(if desired) and handles subprocess errors gracefully, logging any issues.
"""

import subprocess
import threading
import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AppLauncher:
    """Launch external applications with basic duplicate‑run protection.

    The launcher maintains a thread‑safe registry of currently running processes
    keyed by the absolute executable path.  When ``launch`` is called, it checks
    whether the target is already running; if so, the request is ignored and a
    debug message is logged.  This behaviour can be altered by passing
    ``allow_duplicate=True``.
    """

    def __init__(self):
        # Mapping of absolute executable path -> subprocess.Popen instance
        self._processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def launch(self, executable_path: str, *, allow_duplicate: bool = False) -> None:
        """Launch *executable_path* if it exists.

        Parameters
        ----------
        executable_path: str
            Path to the executable or script to run.
        allow_duplicate: bool, optional
            If False (default) a second launch of the same absolute path is ignored
            while the previous instance is still alive.
        """
        abs_path = os.path.abspath(executable_path)
        if not os.path.isfile(abs_path):
            logger.error("Attempted to launch non‑existent file: %s", abs_path)
            return

        with self._lock:
            existing_proc = self._processes.get(abs_path)
            if existing_proc and existing_proc.poll() is None:
                if not allow_duplicate:
                    logger.debug(
                        "Duplicate launch prevented for %s (already running)",
                        abs_path,
                    )
                    return
                else:
                    logger.debug(
                        "Allowing duplicate launch for %s (previous still running)",
                        abs_path,
                    )

            try:
                # ``creationflags`` on Windows prevents a new console window.
                proc = subprocess.Popen(
                    [abs_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                self._processes[abs_path] = proc
                logger.info("Launched application: %s (pid=%s)", abs_path, proc.pid)
            except Exception as exc:
                logger.exception("Failed to launch %s: %s", abs_path, exc)

    def terminate(self, executable_path: str) -> None:
        """Terminate a previously launched process, if still alive.
        """
        abs_path = os.path.abspath(executable_path)
        with self._lock:
            proc = self._processes.get(abs_path)
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    logger.info("Terminated application: %s (pid=%s)", abs_path, proc.pid)
                except Exception as exc:
                    logger.exception("Error terminating %s: %s", abs_path, exc)
                finally:
                    del self._processes[abs_path]
            else:
                logger.debug("No running process found for %s to terminate", abs_path)

    def cleanup_finished(self) -> None:
        """Remove entries for processes that have already exited.
        """
        with self._lock:
            finished = [path for path, proc in self._processes.items() if proc.poll() is not None]
            for path in finished:
                logger.debug("Cleaning up finished process entry for %s", path)
                del self._processes[path]

# End of app_launcher.py
