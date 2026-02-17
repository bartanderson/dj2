import pytest
from unittest.mock import MagicMock, patch, ANY
# Patch external dependencies at the module level before importing CharacterBuilder
@patch.multiple(
    "world.character_builder",
    CLASSES={"wizard": MagicMock()},                     # mock CLASSES dict
    Character=MagicMock(),                               # mock Character class
    tool=lambda **kwargs: lambda f: f,                   # no?op decorator
class TestCharacterBuilder:
    """Test suite for CharacterBuilder class."""
    def test_create_character_basic(
        self, mock_classes, mock_Character, mock_tool
        """Test create_character with minimal data (no personal item)."""
        from world.character_builder import CharacterBuilder
        # Arrange
        mock_ai = MagicMock()
        mock_ai.generate_structured_data.return_value = {
            "traits": "Brave",
            "ideals": "Freedom",
            "bonds": "Family",
            "flaws": "Reckless",
        mock_ai.generate_text.return_value = "A mysterious past..."
        builder = CharacterBuilder(mock_ai)
        owner_id = "player123"
        char_data = {
            "name": "Eldrin",
            "race": "Elf",
            "class": "wizard",
            "background": "sage",
        mock_character_instance = MagicMock()
        mock_Character.return_value = mock_character_instance
        # Act
        result = builder.create_character(owner_id, char_data)
        # Assert
        # Character constructor called once with correct arguments
        mock_Character.assert_called_once_with(
            owner_id=owner_id,
            name="Eldrin",
            classs=mock_classes["wizard"],   # the mocked class object
            level=1,
            background=ANY,
            race="Elf",
        # _generate_personality called once
        mock_ai.generate_structured_data.assert_any_call(
            "Generate personality traits for a Elf wizard with a sage background. Use D&D 5e format with Traits, Ideals, Bonds, and Flaws sections.",
            {"traits": "string", "ideals": "string", "bonds": "string", "flaws": "string"},
        # _generate_background_story called twice (once for background, once for background_story)
        assert mock_ai.generate_text.call_count == 2
        mock_ai.generate_text.assert_any_call(
            "Create a 3-paragraph background story for Eldrin, a Elf wizard with a sage background. Include how they acquired their starting equipment."
        # Character attributes set
        assert mock_character_instance.ai_personality == {
            "traits": "Brave",
            "ideals": "Freedom",
            "bonds": "Family",
            "flaws": "Reckless",
        assert mock_character_instance.background_story == "A mysterious past..."
        # No personal item, so add_custom_item not called
        mock_character_instance.add_custom_item.assert_not_called()
        assert result == mock_character_instance
    def test_create_character_with_personal_item(
        self, mock_classes, mock_Character, mock_tool
        """Test create_character with personal item data."""
        from world.character_builder import CharacterBuilder
        # Arrange
        mock_ai = MagicMock()
        mock_ai.generate_structured_data.return_value = {
            "traits": "Curious",
            "ideals": "Discovery",
            "bonds": "Mentor",
            "flaws": "Naive",
        mock_ai.generate_text.return_value = "A story of origin..."
        builder = CharacterBuilder(mock_ai)
        owner_id = "player456"
        char_data = {
            "name": "Lyra",
            "race": "Human",
            "class": "wizard",
            "background": "acolyte",
            "personal_item": {
                "name": "Amulet of Whispers",
                "description": "A silver amulet that murmurs secrets.",
            },
        mock_character_instance = MagicMock()
        mock_Character.return_value = mock_character_instance
        # Act
        result = builder.create_character(owner_id, char_data)
        # Assert
        # Personal item added
        mock_character_instance.add_custom_item.assert_called_once_with(
            "Amulet of Whispers",
            "A silver amulet that murmurs secrets.",
        assert result == mock_character_instance
    def test_generate_personality(self, mock_classes, mock_Character, mock_tool):
        """Test _generate_personality calls AI with correct prompt."""
        from world.character_builder import CharacterBuilder
        # Arrange
        mock_ai = MagicMock()
        mock_ai.generate_structured_data.return_value = {
            "traits": "Bold",
            "ideals": "Change",
            "bonds": "Adventure",
            "flaws": "Impulsive",
        builder = CharacterBuilder(mock_ai)
        char_data = {
            "race": "Dwarf",
            "class": "fighter",
            "background": "soldier",
        # Act
        result = builder._generate_personality(char_data)
        # Assert
        mock_ai.generate_structured_data.assert_called_once_with(
            "Generate personality traits for a Dwarf fighter with a soldier background. Use D&D 5e format with Traits, Ideals, Bonds, and Flaws sections.",
            {"traits": "string", "ideals": "string", "bonds": "string", "flaws": "string"},
        assert result == {
            "traits": "Bold",
            "ideals": "Change",
            "bonds": "Adventure",
            "flaws": "Impulsive",
    def test_generate_background_story(self, mock_classes, mock_Character, mock_tool):
        """Test _generate_background_story calls AI with correct prompt."""
        from world.character_builder import CharacterBuilder
        # Arrange
        mock_ai = MagicMock()
        mock_ai.generate_text.return_value = "A tale of heroism..."
        builder = CharacterBuilder(mock_ai)
        char_data = {
            "name": "Borin",
            "race": "Dwarf",
            "class": "fighter",
            "background": "soldier",
        # Act
        result = builder._generate_background_story(char_data)
        # Assert
        mock_ai.generate_text.assert_called_once_with(
            "Create a 3-paragraph background story for Borin, a Dwarf fighter with a soldier background. Include how they acquired their starting equipment."
        assert result == "A tale of heroism..."
    def test_generate_personal_item(self, mock_classes, mock_Character, mock_tool):
        """Test generate_personal_item calls AI with structured output."""
        from world.character_builder import CharacterBuilder
        # Arrange
        mock_ai = MagicMock()
        mock_ai.generate_structured_data.return_value = {
            "name": "Shadow Dagger",
            "description": "A blade that blends with darkness.",
            "special_significance": "Once belonged to a master thief.",
        builder = CharacterBuilder(mock_ai)
        char_concept = "rogue with a mysterious past"
        # Act
        result = builder.generate_personal_item(char_concept)
        # Assert
        mock_ai.generate_structured_data.assert_called_once_with(
            f"Create a personalized starting item for a {char_concept}. "
            "It should be mechanically balanced for a level 1 D&D character. "
            "Format: JSON with name, description, and special_significance",
            {"name": "string", "description": "string", "special_significance": "string"},
        assert result == {
            "name": "Shadow Dagger",
            "description": "A blade that blends with darkness.",
            "special_significance": "Once belonged to a master thief.",
    def test_get_equipment_suggestions(self, mock_classes, mock_Character, mock_tool):
        """Test get_equipment_suggestions splits AI text into lines."""
        from world.character_builder import CharacterBuilder
        # Arrange
        mock_ai = MagicMock()
        mock_ai.generate_text.return_value = (
            "- Standard: Leather armor and shortbow\n"
            "- Unconventional: A collapsible grappling hook"
        builder = CharacterBuilder(mock_ai)
        char_concept = "ranger who grew up in a city"
        # Act
        result = builder.get_equipment_suggestions(char_concept)
        # Assert
        mock_ai.generate_text.assert_called_once_with(
            f"Suggest equipment considerations for a {char_concept}. "
            "Include 1 standard choice and 1 unconventional but useful option. "
            "Format: 2 bullet points"
        assert result == [
            "- Standard: Leather armor and shortbow",
            "- Unconventional: A collapsible grappling hook",