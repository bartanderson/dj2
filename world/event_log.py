# world/event_log.py
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# AttrDict – recursive dict wrapper with safe attribute access
# ----------------------------------------------------------------------
class AttrDict(dict):
    """
    Recursive dict wrapper that allows dot‑access.
    Raises AttributeError when a key is missing (consistent with normal attribute lookup).
    """
    def __getattr__(self, item: str) -> Any:
        try:
            value = self[item]
        except KeyError:
            raise AttributeError(item)
        # No need to re‑wrap because wrap_attrdict already did recursively.
        return value

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __deepcopy__(self, memo: Dict) -> 'AttrDict':
        import copy
        return AttrDict({k: copy.deepcopy(v, memo) for k, v in self.items()})


def wrap_attrdict(obj: Any) -> Any:
    """
    Recursively convert dict and list structures to AttrDict.
    Applied once at event creation.
    """
    if isinstance(obj, AttrDict):
        return obj
    if isinstance(obj, dict):
        return AttrDict({k: wrap_attrdict(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [wrap_attrdict(v) for v in obj]
    return obj


# ----------------------------------------------------------------------
# Event Dataclass
# ----------------------------------------------------------------------
@dataclass
class Event:
    type: str                         # domain.entity.phase, e.g., "economy.buy"
    data: dict                        # raw data (will be wrapped)
    source_system: str                # "combat", "economy", "movement", etc.
    actor_id: Optional[str] = None    # player or NPC ID if applicable
    depth: int = 0                    # escalation depth guard (not user data)
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        # Normalize data to AttrDict once, recursively.
        self.data = wrap_attrdict(self.data)


# ----------------------------------------------------------------------
# Event Log (Singleton)
# ----------------------------------------------------------------------
class EventLog:
    def __init__(self, max_size: int = 10000):
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        self._events: List[Event] = []
        self._listeners: Dict[str, List[Callable[[Event], None]]] = defaultdict(list)
        self._wildcard: List[Callable[[Event], None]] = []
        self._max_size = max_size

    def emit(self, event_type: str, data: dict, source_system: str,
             actor_id: Optional[str] = None, depth: int = 0) -> None:
        """Create an Event, store it, and notify matching listeners."""
        
        if "session_id" not in data:
            print(f"[WARN] {event_type} missing session_id:", data)

        event = Event(event_type, data, source_system, actor_id, depth)
        self._events.append(event)
        if len(self._events) > self._max_size:
            self._events.pop(0)

        # Notify type-specific listeners
        for callback in self._listeners.get(event_type, []):
            self._safe_callback(callback, event)

        # Notify wildcard listeners
        for callback in self._wildcard:
            self._safe_callback(callback, event)

    def on(self, event_type: str, callback: Callable[[Event], None]) -> None:
        """Register a callback for a specific event type."""
        self._listeners[event_type].append(callback)

    def on_any(self, callback: Callable[[Event], None]) -> Callable:
        """Register a callback for all events, returning the callback as a handle."""
        self._wildcard.append(callback)
        return callback

    def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]:
        """Return the most recent events (up to limit), optionally filtered by type."""
        if limit < 1:
            raise ValueError("limit must be at least 1")
        # Scan from newest to oldest, collect matches, then reverse.
        matches = []
        for e in reversed(self._events):
            if event_type is None or e.type == event_type:
                matches.append(e)
                if len(matches) >= limit:
                    break
        # Return in chronological order (oldest first)
        return list(reversed(matches))

    def get_all_events(self) -> List[Event]:
        """Return the entire event list (for backward scanning in ContextBuilder)."""
        return self._events[:]   # shallow copy

    def clear(self) -> None:
        """Remove all events and listeners (primarily for testing; resets system state)."""
        self._events.clear()
        self._listeners.clear()
        self._wildcard.clear()

    def _safe_callback(self, callback: Callable[[Event], None], event: Event) -> None:
        """Invoke a callback safely; log and swallow exceptions."""
        try:
            callback(event)
        except Exception as e:
            logger.error(f"Error in event listener for {event.type}: {e}", exc_info=True)


# ----------------------------------------------------------------------
# Singleton Access
# ----------------------------------------------------------------------
_event_log_instance = None

def get_event_log(max_size: int = 10000) -> EventLog:
    global _event_log_instance
    if _event_log_instance is None:
        _event_log_instance = EventLog(max_size)
    elif _event_log_instance._max_size != max_size:
        logger.warning("EventLog already initialized with max_size=%d, ignoring new max_size=%d",
                       _event_log_instance._max_size, max_size)
    return _event_log_instance

def reset_event_log() -> None:
    """Reset the singleton for test isolation."""
    global _event_log_instance
    _event_log_instance = None