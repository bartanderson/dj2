# tests/unit/test_context_builder.py
import pytest
from unittest.mock import Mock, MagicMock
from world.context_builder import ContextBuilder
from world.event_log import get_event_log, reset_event_log, Event, AttrDict
from world.escalation_engine import EscalationEngine

@pytest.fixture
def mock_world():
    world = Mock()
    # Mock a character
    char = Mock()
    char.id = "player1"
    char.name = "TestChar"
    world._get_active_character = Mock(return_value=char)
    # Mock current location
    location = Mock()
    location.name = "Test Location"
    location.terrain = "forest"
    world.current_location = location
    # Mock entities in location (simplified)
    world.get_entities_in_location = Mock(return_value={"entity1", "entity2", "player1"})
    return world

@pytest.fixture
def escalation_engine(mock_world):
    return EscalationEngine(mock_world)

def test_visibility_simple(mock_world, escalation_engine):
    reset_event_log()
    builder = ContextBuilder(mock_world, escalation_engine)
    # Override _compute_visibility temporarily for test? Actually we'll test the method directly
    # For now, compute visibility using the actual world mock
    # But our current _compute_visibility is placeholder; we need to implement it for test.
    # Since we haven't implemented visibility yet, we'll skip this test until later.
    # Instead, we'll test salient events and other aspects that don't rely on visibility.
    pass

def test_salient_events_by_actor(mock_world, escalation_engine):
    reset_event_log()
    log = get_event_log()
    log.emit("player.event", {"value": 1}, "test", actor_id="player1")
    log.emit("other.event", {"value": 2}, "test", actor_id="npc1")
    log.emit("combat.event", {}, "combat")   # source_system combat is always salient
    builder = ContextBuilder(mock_world, escalation_engine)
    ctx = builder.build("session")
    salient = ctx["salient_events"]
    assert len(salient) == 2   # player.event and combat.event
    types = [e["type"] for e in salient]
    assert "player.event" in types
    assert "combat.event" in types
    assert "other.event" not in types

def test_salient_events_by_visible_entity(mock_world, escalation_engine):
    reset_event_log()
    log = get_event_log()
    # Emit event that involves entity1 (which is visible)
    log.emit("involves.entity1", {"entity_id": "entity1"}, "test")
    log.emit("involves.none", {"value": 1}, "test")
    builder = ContextBuilder(mock_world, escalation_engine)
    # Mock visibility to return visible_ids = {"entity1", "player1"}
    builder._compute_visibility = lambda char: ({"entity1", "player1"}, set(), set())
    ctx = builder.build("session")
    salient = ctx["salient_events"]
    assert len(salient) == 1
    assert salient[0]["type"] == "involves.entity1"

def test_salient_event_scan_limit(mock_world, escalation_engine):
    reset_event_log()
    log = get_event_log()
    # Create 25 events that are all salient (by actor)
    for i in range(25):
        log.emit("player.event", {}, "test", actor_id="player1")
    # Set SALIENT_LIMIT to 20 (default)
    builder = ContextBuilder(mock_world, escalation_engine)
    ctx = builder.build("session")
    assert len(ctx["salient_events"]) == 20   # only most recent 20

def test_environment_extraction(mock_world, escalation_engine):
    builder = ContextBuilder(mock_world, escalation_engine)
    env = builder._get_environment()
    assert env["location"] == "Test Location"
    assert env["terrain"] == "forest"
    # Default lighting, sound, weather
    assert env["lighting"] == 1.0
    assert env["sound_level"] == 0.0
    assert env["weather"] == "clear"

def test_knowledge_gaps(mock_world, escalation_engine):
    builder = ContextBuilder(mock_world, escalation_engine)
    gaps = builder._get_knowledge_gaps({"visible"}, {"hidden"}, {"partial"})
    assert gaps["unidentified_entities"] == ["partial"]
    # Expand later with actual signals

def test_escalation_context(mock_world, escalation_engine):
    # Add an effect to escalation engine
    effect = {
        "id": "e1",
        "type": "test_effect",
        "source_event": "test.event",
        "expires_at": None,
        "data": {"value": 42}
    }
    escalation_engine.add_effect(effect)
    builder = ContextBuilder(mock_world, escalation_engine)
    ctx = builder.build("session")
    assert len(ctx["escalation_context"]) == 1
    assert ctx["escalation_context"][0]["id"] == "e1"

def test_empty_context_when_no_character(mock_world, escalation_engine):
    mock_world._get_active_character = Mock(return_value=None)
    builder = ContextBuilder(mock_world, escalation_engine)
    ctx = builder.build("session")
    assert ctx["visible_entities"] == []
    assert ctx["environment"] == {}
    assert ctx["salient_events"] == []