import pytest
import tempfile
import yaml
from unittest.mock import Mock
from world.event_log import get_event_log, reset_event_log
from world.escalation_engine import EscalationEngine

# ----------------------------------------------------------------------
# 1. Branching cascade test
# ----------------------------------------------------------------------
def test_branching_cascade():
    """
    One event triggers two independent escalation events.
    Each of those may trigger further rules.
    Verify ordering and depth propagation.
    """
    reset_event_log()
    log = get_event_log()
    world = Mock()
    world.campaign_state = Mock()

    rules = {
        "rules": [
            {
                "event_pattern": "root.event",
                "actions": [
                    {"name": "emit_branch_a"},
                    {"name": "emit_branch_b"}
                ],
                "priority": 10
            },
            {
                "event_pattern": "branch.a",
                "actions": [{"name": "record_a"}]
            },
            {
                "event_pattern": "branch.b",
                "actions": [{"name": "record_b"}]
            }
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
        def emit_branch_a(event, params):
            engine.emit_event(event, "branch.a", {}, "escalation_engine")
        def emit_branch_b(event, params):
            engine.emit_event(event, "branch.b", {}, "escalation_engine")
        def record_a(event, params):
            calls.append("a")
        def record_b(event, params):
            calls.append("b")

        engine.register_action("emit_branch_a", emit_branch_a)
        engine.register_action("emit_branch_b", emit_branch_b)
        engine.register_action("record_a", record_a)
        engine.register_action("record_b", record_b)

        log.on_any(engine.process_event)
        log.emit("root.event", {}, "test")

        # Both branches should fire, order may depend on dispatch order
        assert set(calls) == {"a", "b"}
        # Check depths: root depth 0, branch events depth 1
        events = log.get_events(limit=10)
        depths = {e.type: e.depth for e in events}
        assert depths["root.event"] == 0
        assert depths["branch.a"] == 1
        assert depths["branch.b"] == 1
    finally:
        import os; os.unlink(path)

# ----------------------------------------------------------------------
# 2. Condition failure safety
# ----------------------------------------------------------------------
def test_condition_failure_safety():
    reset_event_log()
    log = get_event_log()
    world = Mock()
    world.current_location = Mock(terrain="forest")

    rules = {
        "rules": [
            {
                "event_pattern": "test.event",
                "conditions": [
                    "event.data.missing == 1",  # missing field
                    "event.data.value > 'abc'", # type mismatch
                    "world.nonexistent.attribute == 'x'", # bad world access
                    "world.current_location.terrain == 'forest'" # valid condition
                ],
                "actions": [{"name": "should_not_run"}]
            }
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        path = f.name
    try:
        engine = EscalationEngine(log, world)
        engine.load_rules(path)

        action_called = False
        def bad_action(event, params):
            nonlocal action_called
            action_called = True
        engine.register_action("should_not_run", bad_action)

        log.on_any(engine.process_event)
        log.emit("test.event", {"value": 42}, "test")

        # No action should execute because conditions fail
        assert action_called is False
    finally:
        import os; os.unlink(path)

# ----------------------------------------------------------------------
# 3. Mixed listener failure (event log level)
# ----------------------------------------------------------------------
def test_mixed_listener_failure():
    reset_event_log()
    log = get_event_log()
    world = Mock()
    world.campaign_state = Mock()

    # This test subscribes directly to the event log to verify listener isolation
    order = []
    def bad_listener(event):
        order.append("bad_start")
        raise RuntimeError("listener failure")
        order.append("bad_end")  # never reached

    def good_listener1(event):
        order.append("good1")

    def good_listener2(event):
        order.append("good2")

    log.on("test.event", bad_listener)
    log.on("test.event", good_listener1)
    log.on("test.event", good_listener2)

    log.emit("test.event", {}, "test")

    # Bad listener raises, but good listeners still run
    assert order == ["bad_start", "good1", "good2"]