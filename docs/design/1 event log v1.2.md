Event Log – Final Design Document (v1.2)
1. Purpose
Record every significant occurrence in the game world with a timestamp, type, source system, and actor.

Provide a deterministic history and subscription mechanism for other systems (escalation, context builder, UI).

Act as the single source of truth for “what happened”.

2. Data Structures
2.1 AttrDict (recursive, safe)
```python
class AttrDict(dict):
    """Recursive dict wrapper for dot‑access. Raises AttributeError on missing key."""
    def __getattr__(self, item):
        try:
            value = self[item]
        except KeyError:
            raise AttributeError(item)
        if isinstance(value, dict):
            return AttrDict(value)
        return value
    def __setattr__(self, key, value):
        self[key] = value
```
2.2 Recursive Wrapping Helper
```python
def wrap_attrdict(obj):
    """Recursively convert dict and list structures to AttrDict."""
    if isinstance(obj, dict):
        return AttrDict({k: wrap_attrdict(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [wrap_attrdict(v) for v in obj]
    return obj
```
2.3 Event
```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

@dataclass
class Event:
    type: str                         # domain.entity.phase, e.g., "economy.buy"
    data: AttrDict                    # wrapped at creation
    source_system: str                # "combat", "economy", "movement", "adjudication_engine"
    actor_id: Optional[str] = None    # player or NPC ID if applicable
    depth: int = 0                    # escalation depth guard (not user data)
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        # Ensure data is AttrDict (if constructed without wrapper)
        if not isinstance(self.data, AttrDict):
            self.data = wrap_attrdict(self.data)
```
2.4 Entity Reference Convention (for salience)
To allow the ContextBuilder to determine if an event involves a visible entity, events must include one or more of the following fields inside data (as appropriate):

entity_id – primary subject (e.g., killed creature, buying character)

target_id – secondary object (e.g., target of attack, item bought)

involved_entities – list of IDs when many are affected (e.g., area effect)

This convention is mandatory for events that need to be considered salient based on visibility.

3. API
3.1 Singleton Access
```python
def get_event_log(max_size: int = 10000) -> EventLog
3.2 Class EventLog
__init__(self, max_size: int = 10000)

#Initialises empty event list, listener dicts, and wildcard list.

emit(self, event_type: str, data: dict, source_system: str, actor_id: Optional[str] = None, depth: int = 0) -> None

#Creates an Event with the given data (automatically wrapped in AttrDict).

#Appends to internal list; if length exceeds max_size, drops the oldest event.

#Notifies all listeners for the exact event type (in registration order).

#Notifies all wildcard listeners (in registration order) after type‑specific.

#Catches and logs any exception raised by a listener; other listeners still run.

on(self, event_type: str, callback: Callable[[Event], None]) -> None

#Registers a callback for a specific event type.

on_any(self, callback: Callable[[Event], None]) -> None

#Registers a callback for all events.

get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Event]

#Returns the most recent events (up to limit). If event_type provided, filters by type.

3Raises ValueError if limit < 1.

clear(self) -> None

#Removes all events (primarily for testing).
```

4. Performance and Error Handling
emit with no listeners: <5ms.

emit with up to 100 listeners: <20ms.

get_events (limit=100): <5ms.

Exceptions in listener callbacks are logged (using logging.getLogger(__name__)) and ignored; other listeners still run.

emit never raises an exception (errors are logged internally).

5. Integration
AdjudicationEngine will hold a reference to the singleton and call emit after any action that changes state (purchase, combat action, etc.).

Escalation Engine will subscribe via on_any.

ContextBuilder will call get_events (but will also use its own backward scanning logic for salience).

6. Testing
6.1 Unit Tests
Emit an event, verify it appears in get_events.

Register a type‑specific listener, emit matching event, verify listener called.

Register multiple listeners for same type, verify all called in registration order.

Register wildcard listener, verify called for every event.

Verify max_size drops oldest event.

Verify clear() empties the log.

Verify AttrDict nesting: event.data.a.b.c works and missing key raises AttributeError.

Verify that wrap_attrdict converts nested dicts and lists correctly.

6.2 Integration Test
(To be written after escalation engine) – emit an event and verify that a registered escalation action is triggered.

7. Future Extensions (v2)
Persistence of event log to database.

Asynchronous dispatch.

Listener removal (off method).

