# trigger_integration.py
"""Integration layer that connects trigger implementations to the runtime engine.

Triggers should **never** launch applications directly. Instead they emit events
through this module, which forwards them to a shared, thread‑safe
:class:`EventQueue`. The runtime engine consumes those events and performs the
required actions (e.g., launching an app).
"""

from .event_queue import EventQueue
import logging

logger = logging.getLogger(__name__)

# A singleton EventQueue shared across the process. All triggers import this
# module and use ``emit_event`` to push events.
_global_queue = EventQueue()


def get_event_queue() -> EventQueue:
    """Return the shared EventQueue instance.

    This can be useful for advanced scenarios where a component needs direct
    access to the queue (e.g., testing).
    """
    return _global_queue


def emit_event(event: dict) -> None:
    """Validate and enqueue an event produced by a trigger.

    The ``event`` dictionary must contain at least a ``type`` key. Additional
    keys are interpreted by the runtime engine.
    """
    if not isinstance(event, dict) or "type" not in event:
        raise ValueError("Trigger event must be a dict containing a 'type' key")
    logger.debug("Emitting trigger event: %s", event)
    _global_queue.put(event)
