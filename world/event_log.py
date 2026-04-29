# world/event_log.py
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Callable, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class Event:
    type: str
    data: dict
    source: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

class EventLog:
    def __init__(self, max_size: int = 10000):
        self._events: List[Event] = []
        self._listeners: Dict[str, List[Callable]] = {}
        self._wildcard: List[Callable] = []
        self._max_size = max_size

    def emit(self, event_type: str, data: dict, source: str = "system") -> None:
        event = Event(event_type, data, source)
        self._events.append(event)
        if len(self._events) > self._max_size:
            self._events.pop(0)

        # Notify type-specific listeners
        for cb in self._listeners.get(event_type, []):
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Event listener for {event_type} failed: {e}", exc_info=True)
        # Notify wildcard listeners
        for cb in self._wildcard:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Wildcard event listener failed: {e}", exc_info=True)

    def on(self, event_type: str, callback: Callable[[Event], None]) -> None:
        self._listeners.setdefault(event_type, []).append(callback)

    def on_any(self, callback: Callable[[Event], None]) -> None:
        self._wildcard.append(callback)

    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if event_type:
            return [e for e in self._events[-limit:] if e.type == event_type]
        return self._events[-limit:]

    def clear(self) -> None:
        self._events.clear()

# Singleton
_event_log = None

def get_event_log() -> EventLog:
    global _event_log
    if _event_log is None:
        _event_log = EventLog()
    return _event_log