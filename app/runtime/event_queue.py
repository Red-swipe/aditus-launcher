# event_queue.py
"""Thread‑safe event queue used by the runtime engine.

Only simple put/get operations are needed. The queue blocks with a timeout
so that the runtime loop can check for a stop signal regularly.
"""

import queue
from typing import Any, Dict

class EventQueue:
    """Wrapper around :class:`queue.Queue` providing typed put/get.
    """

    def __init__(self, maxsize: int = 0):
        self._queue = queue.Queue(maxsize=maxsize)

    def put(self, event: Dict[str, Any]) -> None:
        """Enqueue an event.
        """
        self._queue.put(event)

    def get(self, timeout: float | None = None) -> Dict[str, Any]:
        """Dequeue an event, optionally waiting up to *timeout* seconds.
        """
        return self._queue.get(timeout=timeout)

    def empty(self) -> bool:
        return self._queue.empty()
