import logging
import threading

from app.runtime.event_queue import get_event_queue as _get_event_queue

logger = logging.getLogger("aditus.trigger")


def get_event_queue():
    return _get_event_queue()


def emit_event(event: dict):
    get_event_queue().put(event)


class HotkeyTrigger:
    def __init__(self, hotkey: str, callback):
        self.hotkey = hotkey
        self.callback = callback
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self):
        pass

    def _listen(self):
        try:
            import keyboard
        except ImportError:
            logger.warning("keyboard module not available, hotkey disabled")
            return

        def _on_hotkey():
            logger.info("aditus.trigger: %s fired", self.hotkey)
            self.callback()

        try:
            keyboard.add_hotkey(self.hotkey, _on_hotkey, suppress=False)
            logger.info("Hotkey '%s' registered", self.hotkey)
            keyboard.wait()
        except Exception as e:
            logger.warning("Hotkey registration failed: %s", e)


from app.runtime.clap_detector import ClapDetector  # noqa: E402
