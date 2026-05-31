import atexit
import logging
import os
import subprocess
import sys
import threading

logger = logging.getLogger("aditus.tray")


class SystemTray:
    _instance = None

    def __init__(self, app, ico_path=None):
        self._app = app
        self._ico_path = ico_path
        self._icon = None
        self._thread = None
        SystemTray._instance = self

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    def _run(self) -> None:
        try:
            import pystray
            from PIL import Image
        except ImportError:
            logger.warning("pystray or PIL not available, system tray disabled")
            return
        tray_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "aditus_tray.png")
        if os.path.isfile(tray_path):
            image = Image.open(tray_path)
        elif self._ico_path and os.path.isfile(self._ico_path):
            image = Image.open(self._ico_path)
        else:
            image = Image.new("RGBA", (16, 16), (10, 13, 18, 255))
        menu = pystray.Menu(
            pystray.MenuItem("Open", self._on_open, default=True),
            pystray.MenuItem("Restart", self._on_restart),
            pystray.MenuItem("Exit", self._on_exit),
        )
        self._icon = pystray.Icon("aditus", image, "Aditus", menu)
        logger.info("SystemTray started")
        self._icon.run()

    def _on_open(self) -> None:
        self._app.after(0, self._app.deiconify)

    def _on_restart(self) -> None:
        self._app.after(0, self._exec_restart)

    def _exec_restart(self) -> None:
        try:
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable])
            else:
                subprocess.Popen([sys.executable] + sys.argv)
        except Exception as e:
            logger.error("Failed to restart: %s", e)
        self._app.destroy()

    def _on_exit(self) -> None:
        self.stop()
        self._app.after(0, self._app.destroy)

    @staticmethod
    def setup_global_cleanup() -> None:
        old_hook = sys.excepthook

        def _cleanup_hook(exc_type, exc_value, traceback):
            if SystemTray._instance:
                SystemTray._instance.stop()
            old_hook(exc_type, exc_value, traceback)

        sys.excepthook = _cleanup_hook
        atexit.register(SystemTray._cleanup_atexit)

    @staticmethod
    def _cleanup_atexit() -> None:
        if SystemTray._instance:
            SystemTray._instance.stop()
