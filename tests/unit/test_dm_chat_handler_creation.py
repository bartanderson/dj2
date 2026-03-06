import pytest
from unittest.mock import Mock, patch
from world.dm_chat_handler import DMChatHandler
from world.session_system import SessionSystem
from world.ai_dungeon_master import Dialog
from world.authority_system import ValidatedAction

@pytest.fixture
def mock_ai():
    ai = Mock()
    ai.classify_intent.return_value = {"intent": "provide_info", "confidence": 0.9}
    ai.extract_character_data.return_value = {}
    ai.generate_text.return_value = "Welcome back! You were creating a character."
    return ai

@pytest.fixture
def session_system():
    return SessionSystem()

@pytest.fixture
def mock_world_controller(session_system, mock_ai):
    wc = Mock()
    wc.session_system = session_system
    wc.dm_chat_ai = mock_ai
    wc.character_manager = Mock()
    wc.authority_system = Mock()
    wc.consequence_engine = Mock()
    wc.players = {}
    return wc

@pytest.fixture
def handler(mock_world_controller):
    return DMChatHandler(mock_world_controller)

def test_resume_detection_returns_prompt(handler, session_system, mock_ai):
    """Test that when a session has partial character data and no active character, a resume prompt is returned."""
    session_id = "test-session"
    player_id = "player123"
    session = session_system.get_or_create_session(session_id, player_id)
    session.character_data = {"name": "Thorin", "race": "dwarf"}
    session.creation_state = "gathering_info"
    session.active_character_id = None

    mock_ai.generate_text.return_value = "Welcome back! You were creating a dwarf named Thorin. Continue?"

    result = handler.process_message(session_id, "ignore this message")

    assert "narrative" in result
    assert len(result["narrative"]) == 1
    assert result["narrative"][0].speaker == "DM"
    assert "Welcome back" in result["narrative"][0].content
    assert session_system.get_session(session_id).character_data == {"name": "Thorin", "race": "dwarf"}

def test_first_creation_message_sets_state_and_asks_question(handler, session_system, mock_ai):
    """Test that the first message in a new session transitions to gathering_info and returns a question."""
    session_id = "test-session"
    player_id = "player123"
    session = session_system.get_or_create_session(session_id, player_id)
    session.creation_state = "not_started"
    session.character_data = {}
    session.active_character_id = None

    mock_ai.classify_intent.return_value = {"intent": "provide_info", "confidence": 0.9}
    mock_ai.extract_character_data.return_value = {"name": "Thorin", "race": "dwarf"}
    mock_ai.suggest_next_question.return_value = {"question": "What class interests you?", "category": "class"}

    result = handler.process_message(session_id, "I want to be Thorin, a dwarf warrior.")

    updated_session = session_system.get_session(session_id)
    assert updated_session.creation_state == "gathering_info"
    assert updated_session.character_data == {"name": "Thorin", "race": "dwarf"}
    assert "narrative" in result
    assert len(result["narrative"]) == 1
    assert result["narrative"][0].content == "What class interests you?"

def test_invalid_attribute_rejected(handler, session_system, mock_ai, mock_world_controller):
    """Test that setting an invalid field (e.g., 'level') returns error and does not mutate."""
    session_id = "test-session"
    player_id = "player123"
    session = session_system.get_or_create_session(session_id, player_id)
    session.creation_state = "not_started"
    session.character_data = {}
    session.active_character_id = None

    mock_ai.classify_intent.return_value = {"intent": "provide_info", "confidence": 0.9}
    mock_ai.extract_character_data.return_value = {"level": 5}   # invalid field

    mock_world_controller.authority_system.validate_creation_action.return_value = ValidatedAction(
        valid=False, message="Field 'level' cannot be set during creation"
    )

    result = handler.process_message(session_id, "I want to be level 5")

    assert "narrative" in result
    assert len(result["narrative"]) == 1
    assert "cannot be set" in result["narrative"][0].content

    updated_session = session_system.get_session(session_id)
    assert updated_session.character_data == {}  # unchanged
    assert updated_session.creation_state == "not_started"  # unchanged

def test_create_character_authority_rejects(handler, session_system, mock_ai, mock_world_controller):
    """Test that if authority rejects the final character creation, an error is returned."""
    session_id = "test-session"
    player_id = "player123"
    session = session_system.get_or_create_session(session_id, player_id)
    session.creation_state = "class_confirmed"
    session.character_data = {"name": "Thorin", "race": "dwarf", "class": "fighter"}  # all fields present
    session.active_character_id = None

    mock_ai.classify_intent.return_value = {"intent": "provide_info", "confidence": 0.9}
    mock_ai.extract_character_data.return_value = {}  # no new data

    mock_world_controller.authority_system.validate_creation_action.return_value = ValidatedAction(
        valid=False, message="Invalid class: fighter"
    )

    result = handler._process_creation_step("irrelevant", session_id)

    assert "narrative" in result
    assert len(result["narrative"]) == 1
    assert "Invalid class" in result["narrative"][0].content

    mock_world_controller.character_manager.create_character.assert_not_called()