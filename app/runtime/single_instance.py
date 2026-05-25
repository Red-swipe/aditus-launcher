# single_instance.py
"""Single-instance enforcement for Aditus runtime.

Provides a context manager that attempts to acquire a Windows named mutex.
If that fails (e.g., on non‑Windows platforms or missing pywin32), it falls back to a lock‑file
implementation stored under the user's local app data directory.

The class is deliberately lightweight – it only needs to be instantiated once at
runtime startup before any triggers are initialised.
"""

import os
import sys
import errno
import json
import ctypes
import ctypes.wintypes
import threading
import atexit
from pathlib import Path

# ---------------------------------------------------------------------------
# Windows named mutex implementation (preferred)
# ---------------------------------------------------------------------------

if os.name == "nt":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _CreateMutexW = _kernel32.CreateMutexW
    _CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.wintypes.BOOL, ctypes.wintypes.LPCWSTR]
    _CreateMutexW.restype = ctypes.wintypes.HANDLE
    _ReleaseMutex = _kernel32.ReleaseMutex
    _ReleaseMutex.argtypes = [ctypes.wintypes.HANDLE]
    _ReleaseMutex.restype = ctypes.wintypes.BOOL
    _CloseHandle = _kernel32.CloseHandle
    _CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    _CloseHandle.restype = ctypes.wintypes.BOOL
    _GetLastError = _kernel32.GetLastError
    _GetLastError.restype = ctypes.wintypes.DWORD

    ERROR_ALREADY_EXISTS = 183

    class WindowsMutex:
        """Acquire a named mutex. If it already exists, raise ``RuntimeError``.

        The mutex is released automatically on process exit via ``atexit``.
        """

        def __init__(self, name: str):
            self.name = name
            self.handle = None
            self.acquired = False
            self._acquire()

        def _acquire(self):
            # CreateMutexW returns a handle; if it already exists, GetLastError == ERROR_ALREADY_EXISTS
            self.handle = _CreateMutexW(None, ctypes.wintypes.BOOL(True), self.name)
            if not self.handle:
                raise RuntimeError(f"Failed to create mutex {self.name}: {ctypes.get_last_error()}")
            err = _GetLastError()
            if err == ERROR_ALREADY_EXISTS:
                # Another instance already holds the mutex
                _CloseHandle(self.handle)
                self.handle = None
                raise RuntimeError("Another Aditus runtime instance is already running.")
            self.acquired = True
            # Ensure release on exit
            atexit.register(self.release)

        def release(self):
            if self.handle and self.acquired:
                _ReleaseMutex(self.handle)
                _CloseHandle(self.handle)
                self.handle = None
                self.acquired = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.release()
            return False
else:
    WindowsMutex = None

# ---------------------------------------------------------------------------
# Lock‑file fallback implementation (cross‑platform)
# ---------------------------------------------------------------------------

class LockFile:
    """Create an exclusive lock file containing the current PID.

    If the lock file already exists, we read the stored PID and check whether the
    process is still alive. If it is, we raise ``RuntimeError``. If the PID does
    not correspond to a running process (stale lock), we remove the file and try
    again.
    """

    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()
        self._fd = None
        self._acquire()
        atexit.register(self.release)

    def _acquire(self):
        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                # O_EXCL + O_CREAT fails if file exists – atomic on Windows and POSIX
                self._fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self._fd, str(os.getpid()).encode())
                return
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                # File exists – inspect it
                try:
                    with open(self.path, "r", encoding="utf-8") as f:
                        pid_str = f.read().strip()
                        pid = int(pid_str)
                except Exception:
                    # Corrupt file – remove it and retry
                    os.remove(self.path)
                    continue
                # Check if the process is still alive
                if pid == os.getpid():
                    # Same process – shouldn't happen, but treat as our lock
                    return
                if self._pid_is_running(pid):
                    raise RuntimeError("Another Aditus runtime instance is already running (PID {})".format(pid))
                else:
                    # Stale lock – remove and retry
                    try:
                        os.remove(self.path)
                    except Exception:
                        pass
                    continue

    @staticmethod
    def _pid_is_running(pid: int) -> bool:
        """Cross‑platform check whether *pid* is a live process.

        On Windows we use ``OpenProcess`` with ``PROCESS_QUERY_LIMITED_INFORMATION``.
        On POSIX we simply try ``os.kill(pid, 0)``.
        """
        if os.name == "nt":
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            PROCESS_VM_READ = 0x0010
            PROCESS_TERMINATE = 0x0001
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, 0, pid
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        else:
            try:
                os.kill(pid, 0)
            except OSError:
                return False
            else:
                return True

    def release(self):
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None
        try:
            if self.path.exists():
                self.path.unlink()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False

# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def enforce_single_instance(app_name: str = "AditusRuntime"):
    """Enforce that only one instance of the Aditus runtime runs.

    The function tries the Windows named mutex first. If that fails (e.g., on
    non‑Windows platforms or if the mutex creation raised ``RuntimeError``), it
    falls back to a lock‑file located in the user's local app‑data directory.

    Usage::

        from app.runtime.single_instance import enforce_single_instance
        enforce_single_instance()

    The returned context manager should be kept alive for the lifetime of the
    process (normally by assigning it to a module‑level variable).
    """
    if os.name == "nt" and WindowsMutex is not None:
        try:
            return WindowsMutex(f"Global\\{app_name}_SingleInstanceMutex")
        except RuntimeError as e:
            # Propagate the error – we already know another instance exists
            raise
    else:
        # Use a lock file in the user's local app data folder. This works for
        # both Windows (fallback) and other OSes.
        lock_path = Path(os.getenv("LOCALAPPDATA", "~/.local")) / app_name / "runtime.lock"
        return LockFile(lock_path)
