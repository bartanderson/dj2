# world/event_log.py
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from world.utils import truncate

class EventLog:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def emit(self, event_type: str, data: Dict[str, Any], source: Optional[str] = None):
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "source": source
        }
        self.events.append(event)
        print(f"[EVENT] {event_type}: {truncate(data)}")

    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if event_type:
            return [e for e in self.events if e["type"] == event_type]
        return self.events.copy()

    def clear(self):
        self.events.clear()

_event_log = None

def get_event_log():
    global _event_log
    if _event_log is None:
        _event_log = EventLog()
    return _event_log