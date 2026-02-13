# world\character_builder.py
from dnd_character import CLASSES
from world.ai_integration import DungeonAI

from .tool_system import tool

class CharacterBuilder:
    def __init__(self, ai_system):
        self.ai = ai_system
        
    @tool(
        name="create_character",
        description="Create a new character with AI enhancements. Requires owner_id and char_data (name, race, class, background, personal_item)."
    )
    def create_character(self, owner_id, char_data):
        """Create a new character with AI enhancements"""
        # Create base character
        char_class = CLASSES[char_data["class"].lower()]
        background = self._generate_background_story(char_data)
        
        character = Character(
            owner_id=owner_id,
            name=char_data["name"],
            classs=char_class,
            level=1,
            background=background,
            race=char_data["race"]
        )
        
        # Add AI-generated personality
        character.ai_personality = self._generate_personality(char_data)
        
        # Add AI-generated background story
        character.background_story = self._generate_background_story(char_data)
        
        # Add personalized item
        if char_data.get("personal_item"):
            character.add_custom_item(
                char_data["personal_item"]["name"],
                char_data["personal_item"]["description"]
            )
            
        return character
        
    @tool(
        name="generate_personality",
        description="Generate personality traits for a character. Requires char_data (race, class, background)."
    )
    def _generate_personality(self, char_data):
        """Generate personality traits using AI"""
        prompt = (
            f"Generate personality traits for a {char_data['race']} {char_data['class']} "
            f"with a {char_data['background']} background. Use D&D 5e format with "
            "Traits, Ideals, Bonds, and Flaws sections."
        )
        return self.ai.generate_structured_data(prompt, {
            "traits": "string",
            "ideals": "string",
            "bonds": "string",
            "flaws": "string"
        })
        
    @tool(
        name="generate_background_story",
        description="Generate a background story for a character. Requires char_data (name, race, class, background)."
    )
    def _generate_background_story(self, char_data):
        """Generate background story using AI"""
        prompt = (
            f"Create a 3-paragraph background story for {char_data['name']}, "
            f"a {char_data['race']} {char_data['class']} with a {char_data['background']} "
            "background. Include how they acquired their starting equipment."
        )
        return self.ai.generate_text(prompt)
        
    @tool(
        name="generate_personal_item",
        description="Generate a personalized starting item for a character concept. Requires char_concept."
    )
    def generate_personal_item(self, char_concept):
        """Generate a personalized starting item"""
        prompt = (
            f"Create a personalized starting item for a {char_concept}. "
            "It should be mechanically balanced for a level 1 D&D character. "
            "Format: JSON with name, description, and special_significance"
        )
        return self.ai.generate_structured_data(prompt, {
            "name": "string",
            "description": "string",
            "special_significance": "string"
        })
        
    @tool(
        name="get_equipment_suggestions",
        description="Get AI suggestions for equipment choices for a character concept. Requires char_concept."
    )
    def get_equipment_suggestions(self, char_concept):
        """Get AI suggestions for equipment choices"""
        prompt = (
            f"Suggest equipment considerations for a {char_concept}. "
            "Include 1 standard choice and 1 unconventional but useful option. "
            "Format: 2 bullet points"
        )
        return self.ai.generate_text(prompt).split("\n")