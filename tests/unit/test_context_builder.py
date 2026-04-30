import pytest
from unittest.mock import Mock
from world.context_builder import ContextBuilder
from world.event_log import get_event_log, reset_event_log
from world.escalation_engine import EscalationEngine

@pytest.fixture
def mock_world():
    world = Mock()
    char = Mock()
    char.id = "player1"
    char.name = "TestChar"
    world._get_active_character = Mock(return_value=char)
    location = Mock()
    location.name = "Test Location"
    location.terrain = "forest"
    world.current_location = location
    world.get_entities_in_location = Mock(return_value={"entity1", "entity2", "player1"})
    return world

@pytest.fixture
def escalation_engine(mock_world):
    reset_event_log()
    log = get_event_log()
    return EscalationEngine(log, mock_world)

def test_salient_events_by_actor(mock_world, escalation_engine):
    reset_event_log()
    log = get_event_log()
    log.emit("player.event", {"value": 1}, "test", actor_id="player1")
    log.emit("other.event", {"value": 2}, "test", actor_id="npc1")
    log.emit("combat.event", {}, "combat")
    builder = ContextBuilder(mock_world, log, escalation_engine)
    ctx = builder.build("session")
    salient = ctx["salient_events"]
    assert len(salient) == 2
    types = [e["type"] for e in salient]
    assert "player.event" in types
    assert "combat.event" in types
    assert "other.event" not in types

def test_salient_events_by_visible_entity(mock_world, escalation_engine):
    reset_event_log()
    log = get_event_log()
    log.emit("involves.entity1", {"entity_id": "entity1"}, "test")
    log.emit("involves.none", {"value": 1}, "test")
    builder = ContextBuilder(mock_world, log, escalation_engine)
    builder._compute_visibility = lambda char: ({"entity1", "player1"}, set(), set())
    ctx = builder.build("session")
    salient = ctx["salient_events"]
    assert len(salient) == 1
    assert salient[0]["type"] == "involves.entity1"

def test_salient_event_scan_limit(mock_world, escalation_engine):
    reset_event_log()
    log = get_event_log()
    for i in range(25):
        log.emit("player.event", {}, "test", actor_id="player1")
    builder = ContextBuilder(mock_world, log, escalation_engine)
    ctx = builder.build("session")
    assert len(ctx["salient_events"]) == 20

def test_environment_extraction(mock_world, escalation_engine):
    log = get_event_log()
    builder = ContextBuilder(mock_world, log, escalation_engine)
    env = builder._get_environment()
    assert env["location"] == "Test Location"
    assert env["terrain"] == "forest"
    assert env["lighting"] == 1.0
    assert env["sound_level"] == 0.0
    assert env["weather"] == "clear"

def test_knowledge_gaps(mock_world, escalation_engine):
    log = get_event_log()
    builder = ContextBuilder(mock_world, log, escalation_engine)
    gaps = builder._get_knowledge_gaps({"visible"}, {"hidden"}, {"partial"})
    assert gaps["unidentified_entities"] == ["partial"]

def test_escalation_context(mock_world, escalation_engine):
    log = get_event_log()
    effect = {
        "id": "e1",
        "type": "test_effect",
        "source_event": "test.event",
        "expires_at": None,
        "data": {"value": 42}
    }
    escalation_engine.add_effect(effect)
    builder = ContextBuilder(mock_world, log, escalation_engine)
    ctx = builder.build("session")
    assert len(ctx["escalation_context"]) == 1
    assert ctx["escalation_context"][0]["id"] == "e1"

def test_empty_context_when_no_character(mock_world, escalation_engine):
    log = get_event_log()
    mock_world._get_active_character = Mock(return_value=None)
    builder = ContextBuilder(mock_world, log, escalation_engine)
    ctx = builder.build("session")
    assert ctx["visible_entities"] == []
    assert ctx["environment"] == {}
    assert ctx["salient_events"] == []

def test_visibility_empty_location(escalation_engine):
    reset_event_log()
    log = get_event_log()
    world = Mock()
    location = Mock()
    world.current_location = location
    world.get_entities_in_location = Mock(return_value=[])
    char = Mock(id="player1")
    world._get_active_character = Mock(return_value=char)
    builder = ContextBuilder(world, log, escalation_engine)
    visible, hidden, partial = builder._compute_visibility(char)
    assert visible == set()
    assert hidden == set()
    assert partial == set()

def test_visibility_no_location(escalation_engine):
    reset_event_log()
    log = get_event_log()
    world = Mock()
    world.current_location = None
    char = Mock(id="player1")
    world._get_active_character = Mock(return_value=char)
    builder = ContextBuilder(world, log, escalation_engine)
    visible, hidden, partial = builder._compute_visibility(char)
    assert visible == set()
    assert hidden == set()
    assert partial == set()