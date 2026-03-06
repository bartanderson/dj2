import pytest
from unittest.mock import Mock, patch
from world.dm_chat_handler import DMChatHandler
from world.session_system import SessionSystem
from world.ai_dungeon_master import Dialog

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
    wc.players = {}  # ← add this so players.get returns None
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

    # Mock the resume prompt generation
    mock_ai.generate_text.return_value = "Welcome back! You were creating a dwarf named Thorin. Continue?"

    result = handler.process_message(session_id, "ignore this message")

    assert "narrative" in result
    assert len(result["narrative"]) == 1
    assert result["narrative"][0].speaker == "DM"
    assert "Welcome back" in result["narrative"][0].content
    # Ensure the user message was not processed (no state change)
    assert session_system.get_session(session_id).character_data == {"name": "Thorin", "race": "dwarf"}

def test_first_creation_message_sets_state_and_asks_question(handler, session_system, mock_ai):
    """Test that the first message in a new session transitions to gathering_info and returns a question."""
    session_id = "test-session"
    player_id = "player123"
    session = session_system.get_or_create_session(session_id, player_id)
    session.creation_state = "not_started"
    session.character_data = {}
    session.active_character_id = None

    # Mock AI responses
    mock_ai.classify_intent.return_value = {"intent": "provide_info", "confidence": 0.9}
    mock_ai.extract_character_data.return_value = {"name": "Thorin", "race": "dwarf"}

    # Mock the AI's suggest_next_question (called by _determine_next_question)
    mock_ai.suggest_next_question.return_value = {"question": "What class interests you?", "category": "class"}

    result = handler.process_message(session_id, "I want to be Thorin, a dwarf warrior.")

    # Assert state changed
    updated_session = session_system.get_session(session_id)
    assert updated_session.creation_state == "gathering_info"
    assert updated_session.character_data == {"name": "Thorin", "race": "dwarf"}

    # Assert narrative returned
    assert "narrative" in result
    assert len(result["narrative"]) == 1
    assert result["narrative"][0].content == "What class interests you?"