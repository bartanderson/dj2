import pytest
from unittest.mock import Mock, patch

# ----------------------------------------------------------------------
# Mock the Character class BEFORE importing character_builder
# ----------------------------------------------------------------------
class MockCharacter:
    def __init__(self, owner_id=None, name=None, classs=None, level=None, background=None, race=None):
        self.owner_id = owner_id
        self.name = name
        self.classs = classs
        self.level = level
        self.background = background
        self.race = race
        self.ai_personality = None
        self.background_story = None
        self.add_custom_item = Mock()

# ----------------------------------------------------------------------
# Import the module under test and inject mock
# ----------------------------------------------------------------------
from world import character_builder
character_builder.Character = MockCharacter

# ----------------------------------------------------------------------
# Mock the CLASSES dict from dnd_character
# ----------------------------------------------------------------------
MOCK_CLASSES = {
    'fighter': Mock(name='FighterClass'),
    'wizard': Mock(name='WizardClass'),
    'rogue': Mock(name='RogueClass'),
    'cleric': Mock(name='ClericClass'),
    'bard': Mock(name='BardClass'),
}

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def mock_ai():
    """Mock the AI system so no real calls are made."""
    ai = Mock()
    ai.generate_structured_data.return_value = {
        "traits": "Brave but reckless",
        "ideals": "Freedom for all",
        "bonds": "I owe a life debt",
        "flaws": "I trust too easily"
    }
    ai.generate_text.return_value = (
        "Thorin was born in the Iron Hills, son of a legendary smith. "
        "He took up the axe after his clan was scattered by orc raiders. "
        "His starting equipment is a family heirloom axe and a shield bearing his clan's crest."
    )
    return ai

@pytest.fixture
def builder(mock_ai):
    """Create a CharacterBuilder with mocked dependencies."""
    with patch('world.character_builder.CLASSES', MOCK_CLASSES):
        instance = character_builder.CharacterBuilder(mock_ai)
        yield instance

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

def test_create_character_calls_ai_and_builds_character(builder, mock_ai):
    """Test that create_character() uses AI and returns a properly built Character."""
    char_data = {
        "name": "Thorin",
        "race": "Dwarf",
        "class": "fighter",
        "background": "Soldier",
        "personal_item": {
            "name": "Axe of Ancestors",
            "description": "A finely crafted dwarven axe passed down through generations."
        }
    }
    owner_id = "player123"

    character = builder.create_character(owner_id, char_data)

    assert mock_ai.generate_structured_data.called
    assert mock_ai.generate_text.called

    personality_prompt = mock_ai.generate_structured_data.call_args[0][0]
    assert "Dwarf" in personality_prompt
    assert "fighter" in personality_prompt
    assert "Soldier" in personality_prompt

    bg_prompt = mock_ai.generate_text.call_args[0][0]
    assert "Thorin" in bg_prompt
    assert "Dwarf" in bg_prompt
    assert "fighter" in bg_prompt
    assert "Soldier" in bg_prompt

    assert character.owner_id == "player123"
    assert character.name == "Thorin"
    assert character.race == "Dwarf"
    assert character.classs == MOCK_CLASSES['fighter']
    assert character.level == 1
    assert character.background == mock_ai.generate_text.return_value
    assert character.background_story == mock_ai.generate_text.return_value
    assert character.ai_personality == mock_ai.generate_structured_data.return_value

    character.add_custom_item.assert_called_once_with(
        "Axe of Ancestors",
        "A finely crafted dwarven axe passed down through generations."
    )

def test_create_character_without_personal_item(builder, mock_ai):
    """Test that no personal item is added when not provided."""
    char_data = {
        "name": "Eldrin",
        "race": "Elf",
        "class": "wizard",
        "background": "Sage"
    }
    owner_id = "player456"

    character = builder.create_character(owner_id, char_data)
    character.add_custom_item.assert_not_called()

def test_generate_personality_tool(builder, mock_ai):
    """Direct test of the _generate_personality tool method."""
    char_data = {
        "race": "Halfling",
        "class": "rogue",
        "background": "Criminal"
    }
    result = builder._generate_personality(char_data)
    assert result == mock_ai.generate_structured_data.return_value
    mock_ai.generate_structured_data.assert_called_once()

def test_generate_background_story_tool(builder, mock_ai):
    """Direct test of the _generate_background_story tool method."""
    char_data = {
        "name": "Balin",
        "race": "Dwarf",
        "class": "cleric",
        "background": "Acolyte"
    }
    result = builder._generate_background_story(char_data)
    assert result == mock_ai.generate_text.return_value
    mock_ai.generate_text.assert_called_once()

def test_generate_personal_item_tool(builder, mock_ai):
    """Test the generate_personal_item tool."""
    mock_ai.generate_structured_data.return_value = {
        "name": "Harmonica of Whimsy",
        "description": "A magical harmonica that plays tunes that lift spirits or confuse enemies.",
        "special_significance": "Once owned by a legendary bard"
    }
    result = builder.generate_personal_item("a musical rogue")
    assert result == mock_ai.generate_structured_data.return_value
    mock_ai.generate_structured_data.assert_called_once()
    prompt = mock_ai.generate_structured_data.call_args[0][0]
    assert "a musical rogue" in prompt

def test_get_equipment_suggestions_tool(builder, mock_ai):
    """Test the get_equipment_suggestions tool."""
    mock_ai.generate_text.return_value = "- Standard: Leather armor, shortsword\n- Unconventional: Flask of Alchemist's Fire"
    result = builder.get_equipment_suggestions("a sneaky rogue")
    assert result == ["- Standard: Leather armor, shortsword", "- Unconventional: Flask of Alchemist's Fire"]
    mock_ai.generate_text.assert_called_once()
    prompt = mock_ai.generate_text.call_args[0][0]
    assert "a sneaky rogue" in prompt

if __name__ == "__main__":
    pytest.main([__file__, "-v"])