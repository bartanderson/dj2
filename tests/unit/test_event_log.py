# tests/unit/test_event_log.py
import pytest
from world.event_log import get_event_log, reset_event_log, Event, AttrDict

@pytest.fixture
def clean_log():
    reset_event_log()
    log = get_event_log()
    log.clear()
    yield log
    reset_event_log()

def test_attrdict():
    from world.event_log import wrap_attrdict, AttrDict
    d = wrap_attrdict({"a": 1, "b": {"c": 2}})
    assert d.a == 1
    assert d.b.c == 2
    assert isinstance(d.b, AttrDict)
    with pytest.raises(AttributeError):
        _ = d.missing

def test_event_creation(clean_log):
    log = get_event_log()
    log.emit("test.event", {"value": 42}, "test_system", actor_id="player1")
    events = log.get_events(limit=10)
    assert len(events) == 1
    e = events[0]
    assert e.type == "test.event"
    assert e.data.value == 42
    assert e.source_system == "test_system"
    assert e.actor_id == "player1"
    assert e.depth == 0

def test_listener(clean_log):
    log = get_event_log()
    received = []
    def cb(e):
        received.append(e.type)
    log.on("test.event", cb)
    log.emit("test.event", {}, "test")
    assert received == ["test.event"]

def test_wildcard(clean_log):
    log = get_event_log()
    received = []
    def wild(e):
        received.append(e.type)
    log.on_any(wild)
    log.emit("a", {}, "sys")
    log.emit("b", {}, "sys")
    assert received == ["a", "b"]

def test_depth_metadata(clean_log):
    log = get_event_log()
    log.emit("test", {}, "sys", depth=3)
    events = log.get_events()
    assert events[0].depth == 3

def test_listener_exception_does_not_break_others(clean_log):
    log = get_event_log()
    calls = []
    def bad(e):
        raise RuntimeError("fail")
    def good(e):
        calls.append("ok")
    log.on("test", bad)
    log.on("test", good)
    log.emit("test", {}, "sys")
    assert calls == ["ok"]

def test_get_events_filtering(clean_log):
    log = get_event_log()
    for i in range(5):
        log.emit(f"type_{i}", {}, "sys")
    # get most recent 2 of type "type_3"
    events = log.get_events(event_type="type_3", limit=2)
    assert len(events) == 1
    assert events[0].type == "type_3"
    # test that limit does not cause empty result when later events don't match
    events2 = log.get_events(event_type="type_0", limit=1)
    assert len(events2) == 1
    assert events2[0].type == "type_0"

def test_max_size_validation():
    with pytest.raises(ValueError):
        get_event_log(max_size=0)