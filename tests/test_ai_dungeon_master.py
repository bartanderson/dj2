import pytest
import json
import uuid
from unittest.mock import Mock, patch, MagicMock, ANY
# Import the classes under test
from world.ai_integration import BaseAI, WorldAI, DungeonAI
from routes.api import handle_ai_command  # optional, if we test the endpoint
# ----------------------------------------------------------------------
# Fixtures and mocks
# ----------------------------------------------------------------------
@pytest.fixture
def mock_ollama_client():
        mock_client = Mock()
        mock_client_class.return_value = mock_client
@pytest.fixture
def mock_psycopg2():
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_connect.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn
@pytest.fixture
def mock_uuid():
        mock_uuid.return_value.hex = 'abc123'
@pytest.fixture
def base_ai(mock_ollama_client):
    # Override tool_registry if needed (we'll keep it real but mock tools)
@pytest.fixture
def mock_campaign_state():
@pytest.fixture
def world_ai(mock_ollama_client, mock_campaign_state):
@pytest.fixture
def mock_dungeon_state():
@pytest.fixture
def dungeon_ai(mock_ollama_client, mock_dungeon_state):
# ----------------------------------------------------------------------
# Tests for BaseAI
# ----------------------------------------------------------------------
class TestBaseAI:
    def test_generate_embedding(self, base_ai, mock_ollama_client):
        mock_ollama_client.embeddings.return_value = {'embedding': [0.1, 0.2, 0.3]}
        mock_ollama_client.embeddings.assert_called_once_with(
        assert result == [0.1, 0.2, 0.3]
    def test_generate_embedding_fallback_on_error(self, base_ai, mock_ollama_client):
        mock_ollama_client.embeddings.side_effect = Exception("API error")
        assert result == [0.0] * 384
    def test_generate_structured_data(self, base_ai, mock_ollama_client):
        mock_response = {"name": "foo", "value": 42}
        mock_ollama_client.generate.return_value = {
        mock_ollama_client.generate.assert_called_once()
        assert call_args["model"] == "llama3.2:3b"
        assert call_args["format"] == "json"
        assert result == mock_response
    def test_generate_structured_data_fallback_on_invalid_json(self, base_ai, mock_ollama_client):
        mock_ollama_client.generate.return_value = {
        assert result == {"name": "foo"}
    def test_generate_text_success(self, base_ai, mock_ollama_client):
        mock_ollama_client.generate.return_value = {"response": "Hello world"}
        assert result == "Hello world"
        mock_ollama_client.generate.assert_called_once()
    def test_generate_text_retry_and_fallback(self, base_ai, mock_ollama_client):
        mock_ollama_client.generate.side_effect = [Exception("fail"), Exception("fail"), Exception("fail")]
        assert result == "Fallback response"
        assert mock_ollama_client.generate.call_count == 3
    def test_process_command_with_tool(self, base_ai, mock_ollama_client):
        # Mock tool registry to have a tool
        mock_tool = Mock(return_value={"success": True})
        # Mock AI response
        mock_ollama_client.generate.return_value = {
        assert result["success"] is True
        mock_tool.assert_called_once_with(arg=5)
    def test_process_command_with_invalid_tool(self, base_ai, mock_ollama_client):
        mock_ollama_client.generate.return_value = {
        assert result["success"] is False
        assert "Error" in result["message"]
# ----------------------------------------------------------------------
# Tests for WorldAI
# ----------------------------------------------------------------------
class TestWorldAI:
    def test_generate_location(self, world_ai, mock_campaign_state, mock_uuid):
        # Mock the structured data generation
        assert result["success"] is True
        assert result["location_id"] == "loc_abc123"
        mock_campaign_state.add_location.assert_called_once()
        assert added_location.name == "Misty Forest"
        assert added_location.type == "forest"
    def test_create_quest_success(self, world_ai, mock_campaign_state, mock_uuid):
        mock_location = Mock()
        mock_location.name = "Misty Forest"
        mock_location.quests = []
        mock_campaign_state.get_location.return_value = mock_location
        assert result["success"] is True
        assert result["quest_id"] == "quest_abc123"
        mock_campaign_state.add_quest.assert_called_once()
        assert added_quest.title == "Find the Lost Relic"
        assert added_quest.location_id == "loc_123"
        assert mock_location.quests == ["quest_abc123"]
    def test_create_quest_location_not_found(self, world_ai, mock_campaign_state):
        mock_campaign_state.get_location.return_value = None
        assert result["success"] is False
        assert "Location not found" in result["message"]
# ----------------------------------------------------------------------
# Tests for DungeonAI
# ----------------------------------------------------------------------
class TestDungeonAI:
    def test_process_command_without_state(self, mock_ollama_client):
        assert result["success"] is False
        assert "Dungeon state not initialized" in result["message"]
    def test_process_command_with_state(self, dungeon_ai, mock_ollama_client):
        # Mock the base method
            mock_base.assert_called_once_with("inspect")
            assert result["success"] is True
    def test_inspect_cell_found(self, dungeon_ai, mock_dungeon_state):
        mock_cell = Mock()
        mock_cell.type = "room"
        mock_cell.description = "A dusty chamber"
        mock_cell.entities = [Mock(type="goblin"), Mock(type="chest")]
        mock_cell.overlays = [1, 2]
        mock_dungeon_state.get_cell.return_value = mock_cell
        assert result["success"] is True
        assert result["type"] == "room"
        assert result["description"] == "A dusty chamber"
        assert result["entities"] == ["goblin", "chest"]
        assert result["overlays"] == 2
    def test_inspect_cell_not_found(self, dungeon_ai, mock_dungeon_state):
        mock_dungeon_state.get_cell.return_value = None
        assert result["success"] is False
        assert "Cell not found" in result["message"]
# ----------------------------------------------------------------------
# Tests for the API endpoint (optional, but included as a public interface)
# ----------------------------------------------------------------------
class TestAICommandEndpoint:
    @patch('routes.api.DungeonAI')
    def test_handle_ai_command_success(self, mock_dungeon_ai_class, mock_ollama_client):
        # Setup mocks
        mock_dungeon_ai = Mock()
        mock_dungeon_ai_class.return_value = mock_dungeon_ai
        mock_dungeon_ai.process_command.return_value = {
        # Mock Flask current_app and request
        mock_request = Mock()
        mock_request.json = {"command": "look"}
        mock_current_app = Mock()
        mock_current_app.game_state.dungeon.state = Mock()
        mock_current_app.logger = Mock()
             patch('routes.api.current_app', mock_current_app):
            from routes.api import handle_ai_command
            # response is a Flask jsonify result; we can check its data
            assert data["success"] is True
            assert data["message"] == "You see a door to the north."
    @patch('routes.api.DungeonAI')
    def test_handle_ai_command_exception(self, mock_dungeon_ai_class, mock_ollama_client):
        mock_dungeon_ai_class.side_effect = Exception("AI failure")
        mock_request = Mock()
        mock_request.json = {"command": "bad"}
        mock_current_app = Mock()
        mock_current_app.game_state.dungeon.state = Mock()
        mock_current_app.logger = Mock()
        mock_current_app.config = {"DEBUG": True}
             patch('routes.api.current_app', mock_current_app), \
             patch('routes.api.traceback.format_exc', return_value="trace"):
            from routes.api import handle_ai_command
            assert data["success"] is False
            assert "AI processing error" in data["message"])}}}}}