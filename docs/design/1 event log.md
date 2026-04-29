Event Log – Final Design (v1)
1. Purpose
Record every significant occurrence in the game world with a timestamp, type, source, and data.

Allow other systems (escalation engine, AI DM, UI) to subscribe to specific event types or all events.

Provide a deterministic history that can be queried for context building and debugging.

2. Data Model
2.1 Event Structure
python
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class Event:
    type: str          # domain.entity.phase (e.g., "economy.buy")
    data: dict         # arbitrary JSON‑serializable data
    source: str        # component that emitted the event
    timestamp: str     # ISO 8601 format, UTC (e.g., "2025-04-28T12:34:56Z")
2.2 Event Log Storage
In‑memory list of Event objects.

Configurable maximum size (default 10,000). When limit reached, the oldest event is removed (FIFO).

No persistence to disk (handled by separate persistence layer).

3. API
3.1 Singleton Access
python
def get_event_log(max_size: int = 10000) -> EventLog:
    """Return the global singleton EventLog instance, creating it with given max_size if first call."""
3.2 Class EventLog
__init__(self, max_size: int = 10000)
Stores `self._max_size` and initialises empty event list and listener dicts.

emit(self, event_type: str, data: dict, source: str) -> None
Create Event with UTC timestamp.

``` pseudocode
Append; if len > self._max_size, pop first element.
```

Notify type‑specific listeners (in registration order).

Notify wildcard listeners (in registration order) after type‑specific.

Catches and logs listener exceptions; never raises.

on(self, event_type: str, callback: Callable[[Event], None]) -> None
Register callback for that exact event type.

on_any(self, callback: Callable[[Event], None]) -> None
Register callback for all events.

get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]
Return most recent events (up to limit), optionally filtered by type.

Raises ValueError if limit < 1.

clear(self) -> None
Empty the event list.

3.3 v2 Future Extensions (not in v1)
off() method to remove listeners.

Thread safety (locks) if game becomes multi‑threaded.

Asynchronous event dispatching.

Regex pattern matching for event types.

4. Implementation Details
File: world/event_log.py

Use logging.getLogger(__name__).

Single‑threaded; no locks in v1.

Example error log: logger.error(f"Event listener failed: {e}", exc_info=True)

5. Performance Constraints (v1 guidelines)
emit with no listeners: <5ms.

emit with up to 100 listeners: <20ms.

get_events(limit=100): <5ms.

6. Testing
Unit tests as previously described.

Integration test (optional) may be added later.