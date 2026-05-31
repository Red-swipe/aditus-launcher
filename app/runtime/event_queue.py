import queue
import threading


class EventQueue:
    def __init__(self, maxsize: int = 100):
        self._queue = queue.Queue(maxsize=maxsize)

    def put(self, event: dict) -> None:
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass

    def put_nowait(self, event: dict) -> None:
        self._queue.put_nowait(event)

    def get_nowait(self):
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def qsize(self) -> int:
        return self._queue.qsize()


_global_queue = EventQueue()


def get_event_queue() -> EventQueue:
    return _global_queue
