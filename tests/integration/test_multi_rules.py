import pytest
import tempfile
import yaml
from unittest.mock import Mock
from world.event_log import get_event_log, reset_event_log
from world.escalation_engine import EscalationEngine

def test_multi_rules_priority_and_stop():
    reset_event_log()
    log = get_event_log()

    world = Mock()
    world.campaign_state = Mock()

    rules = {
        "rules": [
            {
                "name": "high_priority",
                "event_pattern": "economy.buy",
                "conditions": ["event.data.item == 'Healing Potion'"],
                "actions": [{"name": "log_high"}],
                "priority": 10,
                "stop_on_match": False
            },
            {
                "name": "low_priority",
                "event_pattern": "economy.buy",
                "conditions": ["event.data.item == 'Healing Potion'"],
                "actions": [{"name": "log_low"}],
                "priority": 5,
                "stop_on_match": False
            },
            {
                "name": "stopping",
                "event_pattern": "economy.buy",
                "conditions": ["event.data.item == 'Healing Potion'"],
                "actions": [{"name": "log_stop"}],
                "priority": 8,
                "stop_on_match": True
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        rule_path = f.name

    try:
        escalation = EscalationEngine(log, world)
        escalation.load_rules(rule_path)

        calls = []
        def log_high(event, params):
            calls.append("high")
        def log_low(event, params):
            calls.append("low")
        def log_stop(event, params):
            calls.append("stop")

        escalation.register_action("log_high", log_high)
        escalation.register_action("log_low", log_low)
        escalation.register_action("log_stop", log_stop)

        log.on_any(escalation.process_event)

        log.emit(
            "economy.buy",
            {"item": "Healing Potion", "entity_id": "char1", "target_id": "grom"},
            source_system="test",
            actor_id="char1"
        )

        # Priority order: high (10), then stop (8) stops further rules, so low (5) never runs
        assert calls == ["high", "stop"]

    finally:
        import os
        os.unlink(rule_path)