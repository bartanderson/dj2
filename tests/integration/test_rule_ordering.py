import pytest
import tempfile
import yaml
from unittest.mock import Mock
from world.event_log import get_event_log, reset_event_log
from world.escalation_engine import EscalationEngine

def test_priority_ordering():
    reset_event_log()
    log = get_event_log()
    world = Mock()
    world.campaign_state = Mock()

    rules = {
        "rules": [
            {"event_pattern": "test.event", "actions": [{"name": "low"}], "priority": 5},
            {"event_pattern": "test.event", "actions": [{"name": "high"}], "priority": 10},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        path = f.name
    try:
        engine = EscalationEngine(log, world)
        engine.load_rules(path)
        calls = []
        engine.register_action("high", lambda e,p: calls.append("high"))
        engine.register_action("low", lambda e,p: calls.append("low"))
        log.on_any(engine.process_event)
        log.emit("test.event", {}, "test")
        assert calls == ["high", "low"]
    finally:
        import os; os.unlink(path)

def test_stop_on_match_with_multi_action():
    reset_event_log()
    log = get_event_log()
    world = Mock()
    world.campaign_state = Mock()

    rules = {
        "rules": [
            {"event_pattern": "test.event", "actions": [{"name": "a"}, {"name": "b"}], "stop_on_match": True},
            {"event_pattern": "test.event", "actions": [{"name": "c"}]}
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        path = f.name
    try:
        engine = EscalationEngine(log, world)
        engine.load_rules(path)
        calls = []
        engine.register_action("a", lambda e,p: calls.append("a"))
        engine.register_action("b", lambda e,p: calls.append("b"))
        engine.register_action("c", lambda e,p: calls.append("c"))
        log.on_any(engine.process_event)
        log.emit("test.event", {}, "test")
        # All actions of first rule execute, then stop → second rule never runs
        assert calls == ["a", "b"]
        assert "c" not in calls
    finally:
        import os; os.unlink(path)

def test_equal_priority_stability():
    reset_event_log()
    log = get_event_log()
    world = Mock()
    world.campaign_state = Mock()

    rules = {
        "rules": [
            {"event_pattern": "test.event", "actions": [{"name": "first"}], "priority": 5},
            {"event_pattern": "test.event", "actions": [{"name": "second"}], "priority": 5},
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        path = f.name
    try:
        engine = EscalationEngine(log, world)
        engine.load_rules(path)
        calls = []
        engine.register_action("first", lambda e,p: calls.append("first"))
        engine.register_action("second", lambda e,p: calls.append("second"))
        log.on_any(engine.process_event)
        log.emit("test.event", {}, "test")
        assert calls == ["first", "second"]
    finally:
        import os; os.unlink(path)