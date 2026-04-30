import pytest
from unittest.mock import Mock
from world.context_builder import ContextBuilder
from world.event_log import get_event_log, reset_event_log
from world.escalation_engine import EscalationEngine

def test_empty_context():
    reset_event_log()
    world = Mock()
    world._get_active_character = Mock(return_value=None)
    escal = EscalationEngine(world)
    builder = ContextBuilder(world, escal)
    ctx = builder.build("test")
    assert ctx["visible_entities"] == []
    assert "timestamp" in ctx

def test_salient_events():
    reset_event_log()
    world = Mock()
    world._get_active_character = Mock(return_value=Mock(id="player1"))
    escal = EscalationEngine(world)
    builder = ContextBuilder(world, escal)
    log = get_event_log()
    log.emit("test.event", {"value": 1}, "test", actor_id="player1")
    log.emit("other.event", {}, "other", actor_id="npc1")
    ctx = builder.build("test")
    assert len(ctx["salient_events"]) == 1
    assert ctx["salient_events"][0]["type"] == "test.event"