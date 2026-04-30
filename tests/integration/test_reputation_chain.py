import pytest
import tempfile
import yaml
from unittest.mock import Mock
from world.event_log import get_event_log, reset_event_log
from world.escalation_engine import EscalationEngine

def test_reputation_chain():
    reset_event_log()
    log = get_event_log()

    # 1. Mock world controller
    world = Mock()
    world.campaign_state = Mock()
    world.campaign_state.update_merchant_relationship = Mock()

    # 2. Create a temporary rule file for this test (no external dependencies)
    rules = {
        "rules": [
            {
                "event_pattern": "economy.buy",
                "conditions": ["event.data.item == 'Healing Potion'"],
                "actions": [{"name": "request_reputation_change", "params": {"delta": 1}}]
            }
        ]
    }
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(rules, f)
        f.flush()
        temp_rule_path = f.name

    try:
        # 3. Create escalation engine (with log and world)
        escalation = EscalationEngine(log, world)
        escalation.load_rules(temp_rule_path)

        action_called = []
        def request_reputation_change(event, params):
            # Emit intent event
            escalation.emit_event(
                event,
                "reputation.modify_requested",
                {
                    "merchant_id": event.data.target_id,
                    "character_id": event.actor_id,
                    "delta": params.get("delta", 0),
                    "entity_id": event.actor_id,
                    "target_id": event.data.target_id
                },
                source_system="escalation_engine",
                actor_id=event.actor_id
            )
            action_called.append(True)
        escalation.register_action("request_reputation_change", request_reputation_change)

        # 4. Register adjudication handler
        def handle_reputation_modify(event):
            data = event.data
            world.campaign_state.update_merchant_relationship(
                data.merchant_id,
                data.character_id,
                affinity_delta=data.delta
            )
            log.emit(
                "reputation.changed",
                {
                    "merchant_id": data.merchant_id,
                    "character_id": data.character_id,
                    "delta": data.delta,
                    "entity_id": data.character_id,
                    "target_id": data.merchant_id
                },
                source_system="adjudication_engine",
                actor_id=data.character_id
            )
        log.on("reputation.modify_requested", handle_reputation_modify)

        # 5. Subscribe escalation to all events
        log.on_any(escalation.process_event)

        # 6. Emit the initial event
        log.emit(
            "economy.buy",
            {
                "item": "Healing Potion",
                "character": "char1",
                "merchant": "grom",
                "entity_id": "char1",
                "target_id": "grom"
            },
            source_system="adjudication_engine",
            actor_id="char1"
        )

        # 7. Verify events and depths
        events = log.get_events(limit=10)
        types = [e.type for e in events]
        assert types == ["economy.buy", "reputation.modify_requested", "reputation.changed"]

        depths = [e.depth for e in events]
        # Adjudication resets depth to 0, escalation propagates +1
        assert depths == [0, 1, 0]

        # 8. Verify world mutation called correctly
        world.campaign_state.update_merchant_relationship.assert_called_once_with(
            "grom", "char1", affinity_delta=1
        )

        # 9. Verify escalation action was executed
        assert action_called == [True]

    finally:
        # Clean up temporary rule file
        import os
        os.unlink(temp_rule_path)