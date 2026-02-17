import pytest
from unittest.mock import MagicMock, patch, call
# Mock the dnd_character module globally
with patch.dict('sys.modules', {'dnd_character': MagicMock()}):
    from world.character_builder import CharacterBuilder
class TestCharacterBuilder:
    """Test suite for CharacterBuilder class."""
    @pytest.fixture
    def ai_system_mock(self):
        """Fixture for a mocked AI system."""
        ai = MagicMock()
        ai.generate_structured_data.return_value = {
            "traits": "Brave",
            "ideals": "Freedom",
            "bonds": "Family",
            "flaws": "Reckless",}
        ai.generate_text.return_value = (
            "Born in a small village, he always dreamed of adventure. "
            "One day he found a mysterious sword in the forest. "
            "Now he travels the land seeking glory.")
        return ai
    @pytest.fixture
    def character_builder(self, ai_system_mock):
        """Fixture for CharacterBuilder with mocked AI."""
        return CharacterBuilder(ai_system_mock)
    @patch('world.character_builder.CLASSES')
    @patch('world.character_builder.Character')
    def test_create_character_basic(self, mock_character_class, mock_classes, character_builder, ai_system_mock):
        """Test creating a character without personal item."""
        # Setup mocks
        mock_classes.__getitem__.return_value = "FighterClass"
        mock_character_instance = MagicMock()
        mock_character_class.return_value = mock_character_instance
        owner_id = "player_123"
        char_data = {
            "name": "Aragorn",
            "race": "Human",
            "class": "fighter",
            "background": "soldier"}
        # Call method
        result = character_builder.create_character(owner_id, char_data)
        # Verify CLASSES lookup
        mock_classes.__getitem__.assert_called_once_with("fighter")
        # Verify AI calls
        ai_system_mock.generate_structured_data.assert_called_once()
        ai_system_mock.generate_text.assert_called_once()
        # Verify Character constructor
        mock_character_class.assert_called_once_with(
            owner_id=owner_id,
            name="Aragorn",
            classs="FighterClass",
            level=1,
            background=ai_system_mock.generate_text.return_value,
            race="Human")
        # Verify attributes set
        assert mock_character_instance.ai_personality == ai_system_mock.generate_structured_data.return_value
        assert mock_character_instance.background_story == ai_system_mock.generate_text.return_value
        # Verify add_custom_item not called
        mock_character_instance.add_custom_item.assert_not_called()
        assert result == mock_character_instance
    @patch('world.character_builder.CLASSES')
    @patch('world.character_builder.Character')
    def test_create_character_with_personal_item(self, mock_character_class, mock_classes, character_builder, ai_system_mock):
        """Test creating a character with a personal item."""
        # Setup mocks
        mock_classes.__getitem__.return_value = "RogueClass"
        mock_character_instance = MagicMock()
        mock_character_class.return_value = mock_character_instance
        owner_id = "player_456"
        char_data = {
            "name": "Legolas",
            "race": "Elf",
            "class": "rogue",
            "background": "archer",
            "personal_item": {
                "name": "Elven Bow",
                "description": "A finely crafted bow passed down through generations."
            }
        }
        # Call method
        result = character_builder.create_character(owner_id, char_data)
        # Verify Character constructor
        mock_character_class.assert_called_once()
        # Verify add_custom_item called
        mock_character_instance.add_custom_item.assert_called_once_with(
            "Elven Bow",
            "A finely crafted bow passed down through generations.")
        assert result == mock_character_instance
    @patch('world.character_builder.CLASSES')
    @patch('world.character_builder.Character')
    def test_create_character_ai_fallback(self, mock_character_class, mock_classes, character_builder, ai_system_mock):
        """Test that AI methods are called with correct prompts."""
        # Setup mocks
        mock_classes.__getitem__.return_value = "WizardClass"
        mock_character_instance = MagicMock()
        mock_character_class.return_value = mock_character_instance
        owner_id = "player_789"
        char_data = {
            "name": "Gandalf",
            "race": "Maia",
            "class": "wizard",
            "background": "scholar"}
        character_builder.create_character(owner_id, char_data)
        # Check AI prompts
        personality_call = ai_system_mock.generate_structured_data.call_args[0][0]
        assert "Generate personality traits for a Maia wizard" in personality_call
        assert "with a scholar background" in personality_call
        story_call = ai_system_mock.generate_text.call_args[0][0]
        assert "Create a 3-paragraph background story for Gandalf" in story_call
        assert "a Maia wizard with a scholar background" in story_call
    def test_generate_personal_item(self, character_builder, ai_system_mock):
        """Test generating a personal item."""
        concept = "a sneaky rogue with a mysterious past"
        expected_item = {
            "name": "Shadow Dagger",
            "description": "A dagger that seems to absorb light.",
            "special_significance": "Once belonged to a legendary thief."}
        ai_system_mock.generate_structured_data.return_value = expected_item
        result = character_builder.generate_personal_item(concept)
        # Verify AI call
        ai_system_mock.generate_structured_data.assert_called_once()
        prompt = ai_system_mock.generate_structured_data.call_args[0][0]
        assert concept in prompt
        assert "level 1 D&D character" in prompt
        # Verify return value
        assert result == expected_item
    def test_get_equipment_suggestions(self, character_builder, ai_system_mock):
        """Test getting equipment suggestions."""
        concept = "a sturdy dwarf fighter"
        ai_system_mock.generate_text.return_value = (
            "- Standard: Battleaxe and shield\n"
            "- Unconventional: A small anvil used as a throwing weapon")
        result = character_builder.get_equipment_suggestions(concept)
        # Verify AI call
        ai_system_mock.generate_text.assert_called_once()
        prompt = ai_system_mock.generate_text.call_args[0][0]
        assert concept in prompt
        assert "1 standard choice and 1 unconventional" in prompt
        # Verify split
        assert result == [
            "- Standard: Battleaxe and shield",
            "- Unconventional: A small anvil used as a throwing weapon"]
    @patch('world.character_builder.CLASSES')
    @patch('world.character_builder.Character')
    def test_create_character_handles_missing_personal_item(self, mock_character_class, mock_classes, character_builder):
        """Test that absence of personal_item does not cause error."""
        mock_classes.__getitem__.return_value = "ClericClass"
        mock_character_instance = MagicMock()
        mock_character_class.return_value = mock_character_instance
        owner_id = "player_000"
        char_data = {
            "name": "Bran",
            "race": "Human",
            "class": "cleric",
            "background": "acolyte"
            # no personal_item
            }
        character_builder.create_character(owner_id, char_data)
        # Verify add_custom_item not called
        mock_character_instance.add_custom_item.assert_not_called()