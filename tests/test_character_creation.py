import pytest
from unittest.mock import Mock, patch, MagicMock
import world.character_builder
# The class under test is CharacterBuilder (adjust if needed)
@pytest.fixture
def mock_ai():
    # Return a configured Mock for the AI dependency
    mock = Mock()
    # Configure default behavior; specific overrides can be set in tests
    mock.generate.return_value = {"name": "Default", "class": "Default"}
@pytest.fixture
def character_builder(mock_ai):
    # Instantiate CharacterBuilder with mock_ai and any other mocks
def test_create_character(character_builder, mock_ai):
    # Implement test
    mock_ai.generate.return_value = expected_character
    assert result == expected_character
    mock_ai.generate.assert_called_once()