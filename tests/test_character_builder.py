import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the class under test
from world.character_builder import CharacterBuilder


@pytest.fixture
def mock_ai():
    """Fixture providing a mocked DungeonAI instance."""
    return Mock()


@pytest.fixture
def mock_character_class():
    """Fixture providing a mocked Character class with call tracking."""
    mock = Mock()
    # Create a mock instance that tracks method calls
    mock_instance = Mock()
    mock.return_value = mock_instance
    return mock, mock_instance


@pytest.fixture
def mock_classes():
    """Fixture providing mocked CLASSES dictionary."""
    return {
        "warrior": Mock(),
        "mage": Mock(),
        "rogue": Mock()
    }


@pytest.fixture
def character_builder(mock_ai):
    """Fixture providing a CharacterBuilder instance with mocked AI."""
    return CharacterBuilder(ai_system=mock_ai)


class TestCharacterBuilder:
    """Test suite for CharacterBuilder class."""

    def test_create_character_success(self, character_builder, mock_ai, mock_character_class, mock_classes):
        """Test successful character creation with all AI enhancements applied.
        
        Arrange: Mock CLASSES, Character, and AI responses
        Act: Call create_character with complete char_data
        Assert: Character instantiated correctly, AI methods called, custom item added
        """
        # Arrange
        mock_char_cls, mock_instance = mock_character_class
        
        char_data = {
            "name": "Test Hero",
            "race": "Human",
            "class": "warrior",
            "background": "Soldier",
            "personal_item": {
                "name": "Family Sword",
                "description": "An old but reliable blade"
            }
        }
        owner_id = "user_123"
        
        mock_classes["warrior"] = Mock()
        mock_ai.generate_structured_data.return_value = {
            "traits": "Brave",
            "ideals": "Honor",
            "bonds": "Family",
            "flaws": "Stubborn"
        }
        mock_ai.generate_text.return_value = "Background story text"
        
        # Act
        with patch("world.character_builder.CLASSES", mock_classes):
            with patch("world.character_builder.Character", mock_char_cls):
                result = character_builder.create_character(owner_id, char_data)
        
        # Assert
        assert result == mock_instance
        mock_char_cls.assert_called_once_with(
            owner_id=owner_id,
            name="Test Hero",
            classs=mock_classes["warrior"],
            level=1,
            background="Background story text",
            race="Human"
        )
        assert mock_instance.ai_personality == {
            "traits": "Brave",
            "ideals": "Honor",
            "bonds": "Family",
            "flaws": "Stubborn"
        }
        assert mock_instance.background_story == "Background story text"
        mock_instance.add_custom_item.assert_called_once_with(
            "Family Sword",
            "An old but reliable blade"
        )

    def test_create_character_without_personal_item(self, character_builder, mock_ai, mock_character_class, mock_classes):
        """Test character creation without a personal item.
        
        Arrange: Mock dependencies, provide char_data without personal_item
        Act: Call create_character
        Assert: Character created, add_custom_item not called
        """
        # Arrange
        mock_char_cls, mock_instance = mock_character_class
        
        char_data = {
            "name": "Minimal Hero",
            "race": "Elf",
            "class": "mage",
            "background": "Sage"
        }
        owner_id = "user_456"
        
        mock_classes["mage"] = Mock()
        mock_ai.generate_structured_data.return_value = {}
        mock_ai.generate_text.return_value = "Story"
        
        # Act
        with patch("world.character_builder.CLASSES", mock_classes):
            with patch("world.character_builder.Character", mock_char_cls):
                result = character_builder.create_character(owner_id, char_data)
        
        # Assert
        assert result == mock_instance
        mock_instance.add_custom_item.assert_not_called()

    def test_create_character_class_case_insensitive(self, character_builder, mock_ai, mock_character_class, mock_classes):
        """Test that class lookup is case-insensitive.
        
        Arrange: Mock CLASSES with lowercase key, provide uppercase class name
        Act: Call create_character with uppercase class name
        Assert: Correct class retrieved from CLASSES
        """
        # Arrange
        mock_char_cls, mock_instance = mock_character_class
        
        char_data = {
            "name": "Case Test",
            "race": "Dwarf",
            "class": "WARRIOR",  # Uppercase
            "background": "Knight"
        }
        owner_id = "user_789"
        
        mock_warrior_class = Mock()
        mock_classes["warrior"] = mock_warrior_class
        mock_ai.generate_structured_data.return_value = {}
        mock_ai.generate_text.return_value = "Story"
        
        # Act
        with patch("world.character_builder.CLASSES", mock_classes):
            with patch("world.character_builder.Character", mock_char_cls):
                result = character_builder.create_character(owner_id, char_data)
        
        # Assert
        mock_char_cls.assert_called_once()
        call_kwargs = mock_char_cls.call_args[1]
        assert call_kwargs["classs"] == mock_warrior_class

    def test_generate_personality(self, character_builder, mock_ai):
        """Test AI personality generation with correct prompt and schema.
        
        Arrange: Set up mock AI response
        Act: Call _generate_personality
        Assert: AI called with correct prompt and schema, result returned
        """
        # Arrange
        char_data = {
            "race": "Halfling",
            "class": "rogue",
            "background": "Criminal"
        }
        expected_response = {
            "traits": "Sneaky",
            "ideals": "Freedom",
            "bonds": "Thieves' Guild",
            "flaws": "Greedy"
        }
        mock_ai.generate_structured_data.return_value = expected_response
        
        # Act
        result = character_builder._generate_personality(char_data)
        
        # Assert
        assert result == expected_response
        mock_ai.generate_structured_data.assert_called_once()
        call_args = mock_ai.generate_structured_data.call_args[0]
        assert "Halfling" in call_args[0]
        assert "rogue" in call_args[0]
        assert "Criminal" in call_args[0]
        assert call_args[1] == {
            "traits": "string",
            "ideals": "string",
            "bonds": "string",
            "flaws": "string"
        }

    def test_generate_background_story(self, character_builder, mock_ai):
        """Test background story generation with correct prompt.
        
        Arrange: Set up mock AI text response
        Act: Call _generate_background_story
        Assert: AI called with correct prompt, result returned
        """
        # Arrange
        char_data = {
            "name": "Aria",
            "race": "Elf",
            "class": "mage",
            "background": "Hermit"
        }
        expected_story = "Aria grew up in isolation..."
        mock_ai.generate_text.return_value = expected_story
        
        # Act
        result = character_builder._generate_background_story(char_data)
        
        # Assert
        assert result == expected_story
        mock_ai.generate_text.assert_called_once()
        call_prompt = mock_ai.generate_text.call_args[0][0]
        assert "Aria" in call_prompt
        assert "Elf" in call_prompt
        assert "mage" in call_prompt
        assert "Hermit" in call_prompt

    def test_generate_personal_item(self, character_builder, mock_ai):
        """Test personalized item generation with correct prompt and schema.
        
        Arrange: Set up mock AI response
        Act: Call generate_personal_item
        Assert: AI called with correct prompt and schema, result returned
        """
        # Arrange
        char_concept = "mysterious warlock"
        expected_item = {
            "name": "Shadow Tome",
            "description": "A dark book",
            "special_significance": "Family heirloom"
        }
        mock_ai.generate_structured_data.return_value = expected_item
        
        # Act
        result = character_builder.generate_personal_item(char_concept)
        
        # Assert
        assert result == expected_item
        mock_ai.generate_structured_data.assert_called_once()
        call_args = mock_ai.generate_structured_data.call_args[0]
        assert "mysterious warlock" in call_args[0]
        assert call_args[1] == {
            "name": "string",
            "description": "string",
            "special_significance": "string"
        }

    def test_get_equipment_suggestions(self, character_builder, mock_ai):
        """Test equipment suggestions with text splitting.
        
        Arrange: Set up mock AI response with newline-separated items
        Act: Call get_equipment_suggestions
        Assert: AI called with correct prompt, result split into list
        """
        # Arrange
        char_concept = "stealthy archer"
        ai_response = "- Longbow with darkwood finish\n- Smoke bombs for quick escapes"
        mock_ai.generate_text.return_value = ai_response
        
        # Act
        result = character_builder.get_equipment_suggestions(char_concept)
        
        # Assert
        assert result == ["- Longbow with darkwood finish", "- Smoke bombs for quick escapes"]
        mock_ai.generate_text.assert_called_once()
        call_prompt = mock_ai.generate_text.call_args[0][0]
        assert "stealthy archer" in call_prompt

    def test_get_equipment_suggestions_empty_response(self, character_builder, mock_ai):
        """Test equipment suggestions with empty AI response.
        
        Arrange: Set up mock AI to return empty string
        Act: Call get_equipment_suggestions
        Assert: Result is list with empty string
        """
        # Arrange
        mock_ai.generate_text.return_value = ""
        
        # Act
        result = character_builder.get_equipment_suggestions("any concept")
        
        # Assert
        assert result == [""]