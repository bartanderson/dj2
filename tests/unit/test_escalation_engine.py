import pytest
import tempfile
import yaml
from typing import Dict
from unittest.mock import Mock
from world.event_log import Event, get_event_log, reset_event_log
from world.escalation_engine import EscalationEngine, MAX_DEPTH

def _eval_condition(self, expr: str, event: Event, world: Dict) -> bool:
    # Build a safe evaluation context using only primitive + dict structures
    eval_event = {
        "type": event.type,
        "data": event.data,          # event.data is AttrDict, but simpleeval can handle dict
        "source_system": event.source_system,
        "actor_id": event.actor_id,
        "depth": event.depth,
        "timestamp": event.timestamp,
    }
    context = {
        'event': eval_event,
        'world': world,
    }
    try:
        result = simple_eval(expr, functions={}, names=context, operators={})
        return bool(result)
    except Exception as e:
        logger.warning(f"Condition evaluation failed: {expr} – {e}")
        return False

def test_rule_loading_and_matching():
    reset_event_log()
    engine = EscalationEngine(Mock())
    rules = {'rules': [{'event_pattern': 'test.event', 'actions': [{'name': 'mock_action'}], 'priority': 5}]}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        engine.load_rules(f.name)

    action_called = []
    def mock_action(event, params):
        action_called.append(True)
    engine.register_action('mock_action', mock_action)

    log = get_event_log()
    log.on_any(engine.process_event)
    log.emit('test.event', {}, 'test')
    assert action_called == [True]

def test_depth_guard():
    reset_event_log()
    engine = EscalationEngine(Mock())
    rules = {'rules': [{'event_pattern': 'test.loop', 'actions': [{'name': 'reemit'}]}]}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        engine.load_rules(f.name)

    reemit_count = 0
    def reemit(event, params):
        nonlocal reemit_count
        reemit_count += 1
        if event.depth < MAX_DEPTH:
            EscalationEngine.emit_event(event, 'test.loop', {}, 'escalation_engine')
    engine.register_action('reemit', reemit)

    log = get_event_log()
    log.on_any(engine.process_event)
    log.emit('test.loop', {}, 'test', depth=0)
    assert reemit_count == MAX_DEPTH
    # Ensure no further events beyond MAX_DEPTH
    # (The last reemit would try to send event with depth=11, which is discarded)

def test_condition_evaluation():
    reset_event_log()
    world = Mock()
    world.current_location = Mock(terrain="forest")
    world.campaign_state = Mock()
    world.campaign_state.get_faction_standing = Mock(return_value=0)

    engine = EscalationEngine(world)
    rules = {
        "rules": [
            {
                "event_pattern": "test.event",
                "conditions": ["event.data.value == 42"],
                "actions": [{"name": "hit"}],
            }
        ]
    }
    import tempfile, yaml
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        engine.load_rules(f.name)

    called = []
    def hit_action(event, params):
        called.append(True)
    engine.register_action("hit", hit_action)

    log = get_event_log()
    log.on_any(engine.process_event)
    log.emit("test.event", {"value": 42}, "sys")
    assert called == [True]

    # Test with wrong value
    called.clear()
    log.emit("test.event", {"value": 43}, "sys")
    assert called == []   # condition fails, action not called