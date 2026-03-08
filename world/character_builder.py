# world/character_builder.py
from dnd_character import Character # We'll leave the Character import as is. It's the base class for our custom Character subclass, and it's only used in character.py for inheritance.
from world import dnd_data # This is standardized because of shared usage for consistency
from .tool_system import tool
from typing import Dict, Any, Optional

class CharacterBuilder:
    """Builds characters with AI‑enhanced personality, background, and items."""

    def __init__(self, ai_system):
        self.ai = ai_system

    @tool(
        name="create_character",
        description="Create a new character with AI enhancements. Requires owner_id and char_data (name, race, class, background, personal_item)."
    )
    def create_character(self, owner_id: str, char_data: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a new character with AI enhancements.

        Args:
            owner_id: ID of the player who owns the character.
            char_data: Dictionary with at least 'name', 'race', 'class'.
                       May include 'background' (the background type, e.g., "knight"),
                       'personality', 'ideals', 'bonds', 'flaws', and 'personal_item'.
            context: Optional session context (unused here, but required by tool system).

        Returns:
            Dict with keys:
                - success (bool): True if character created.
                - message (str): Human‑readable outcome.
                - character (Character, optional): The created character if successful.
        """
        try:
            # Validate required fields
            required = ['name', 'race', 'class']
            missing = [f for f in required if f not in char_data or not char_data[f]]
            if missing:
                return {
                    "success": False,
                    "message": f"Missing required field(s): {', '.join(missing)}"
                }

            # Get character class object
            class_name = char_data["class"]
            if not dnd_data.validate_class(class_name):
                return {"success": False, "message": f"Unknown class: {class_name}"}
            char_class = dnd_data.get_class_object(class_name)

            # Generate background story (may fail, we'll capture message)
            story_result = self.generate_background_story(char_data, context)
            background_story = story_result.get("story", "")
            story_message = story_result.get("message", "")

            # Generate personality (may fail)
            personality_result = self.generate_personality(char_data, context)
            personality_data = {
                "traits": personality_result.get("traits", ""),
                "ideals": personality_result.get("ideals", ""),
                "bonds": personality_result.get("bonds", ""),
                "flaws": personality_result.get("flaws", "")
            }
            personality_message = personality_result.get("message", "")

            # Create base character using the library's constructor.
            # Note: The library expects 'background' to be a short descriptor (e.g., "knight").
            # We store the full AI‑generated story separately as a custom attribute.
            character = Character(
                name=char_data["name"],
                race=char_data["race"],
                classs=char_class,
                level=1,
                background=char_data.get("background", "unknown"),
                # Other optional fields can be added if present in char_data:
                age=char_data.get("age"),
                gender=char_data.get("gender"),
                description=char_data.get("description"),
                alignment=char_data.get("alignment"),
                # Ability scores can also be provided; otherwise the library rolls them.
                strength=char_data.get("strength"),
                dexterity=char_data.get("dexterity"),
                constitution=char_data.get("constitution"),
                intelligence=char_data.get("intelligence"),
                wisdom=char_data.get("wisdom"),
                charisma=char_data.get("charisma"),
            )

            # Attach AI-generated content as custom attributes (safe because Character is flexible)
            character.full_background_story = background_story
            character.ai_personality = personality_data

            # Add personalized item if provided
            if char_data.get("personal_item"):
                item = char_data["personal_item"]
                character.add_custom_item(
                    item.get("name", "Mysterious Item"),
                    item.get("description", "A strange object of unknown origin.")
                )

            # Compose final message, including any AI generation warnings
            messages = []
            if story_result.get("success"):
                messages.append("Background story generated.")
            else:
                messages.append(f"Background story failed: {story_message}")
            if personality_result.get("success"):
                messages.append("Personality generated.")
            else:
                messages.append(f"Personality generation failed: {personality_message}")

            return {
                "success": True,
                "message": f"Character {character.name} created. " + " ".join(messages),
                "character": character
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Character creation failed: {str(e)}"
            }

    @tool(
        name="generate_personality",
        description="Generate personality traits for a character. Requires char_data (race, class, background)."
    )
    def generate_personality(self, char_data: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate personality traits using AI.

        Args:
            char_data: Dictionary with 'race', 'class', 'background'.
            context: Optional session context.

        Returns:
            Dict with keys:
                - success (bool)
                - message (str)
                - traits (str)
                - ideals (str)
                - bonds (str)
                - flaws (str)
        """
        try:
            prompt = (
                f"Generate personality traits for a {char_data.get('race', 'unknown')} "
                f"{char_data.get('class', 'unknown')} with a {char_data.get('background', 'unknown')} "
                "background. Use D&D 5e format with Traits, Ideals, Bonds, and Flaws sections. "
                "Return a JSON object with exactly the keys: traits, ideals, bonds, flaws."
            )
            result = self.ai.generate_structured_data(prompt, {
                "traits": "string",
                "ideals": "string",
                "bonds": "string",
                "flaws": "string"
            })
            return {
                "success": True,
                "message": "Personality generated.",
                "traits": result.get("traits", ""),
                "ideals": result.get("ideals", ""),
                "bonds": result.get("bonds", ""),
                "flaws": result.get("flaws", "")
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Personality generation failed: {str(e)}",
                "traits": "", "ideals": "", "bonds": "", "flaws": ""
            }

    @tool(
        name="generate_background_story",
        description="Generate a background story for a character. Requires char_data (name, race, class, background)."
    )
    def generate_background_story(self, char_data: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate background story using AI.

        Args:
            char_data: Dictionary with 'name', 'race', 'class', 'background'.
            context: Optional session context.

        Returns:
            Dict with keys:
                - success (bool)
                - message (str)
                - story (str) – the generated text
        """
        try:
            prompt = (
                f"Create a 3‑paragraph background story for {char_data.get('name', 'the character')}, "
                f"a {char_data.get('race', 'unknown')} {char_data.get('class', 'unknown')} with a "
                f"{char_data.get('background', 'unknown')} background. Include how they acquired their "
                "starting equipment."
            )
            story = self.ai.generate_text(prompt)
            return {
                "success": True,
                "message": "Background story generated.",
                "story": story.strip() if story else ""
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Background story generation failed: {str(e)}",
                "story": ""
            }

    @tool(
        name="generate_personal_item",
        description="Generate a personalized starting item for a character concept. Requires char_concept."
    )
    def generate_personal_item(self, char_concept: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate a personalized starting item.

        Args:
            char_concept: Description of the character (e.g., "elven rogue").
            context: Optional session context.

        Returns:
            Dict with keys:
                - success (bool)
                - message (str)
                - name (str)
                - description (str)
                - special_significance (str)
        """
        try:
            prompt = (
                f"Create a personalized starting item for a {char_concept}. "
                "It should be mechanically balanced for a level 1 D&D character. "
                "Return a JSON object with keys: name, description, special_significance."
            )
            item = self.ai.generate_structured_data(prompt, {
                "name": "string",
                "description": "string",
                "special_significance": "string"
            })
            return {
                "success": True,
                "message": "Personal item generated.",
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "special_significance": item.get("special_significance", "")
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Personal item generation failed: {str(e)}",
                "name": "", "description": "", "special_significance": ""
            }

    @tool(
        name="get_equipment_suggestions",
        description="Get AI suggestions for equipment choices for a character concept. Requires char_concept."
    )
    def get_equipment_suggestions(self, char_concept: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Get AI suggestions for equipment choices.

        Args:
            char_concept: Description of the character.
            context: Optional session context.

        Returns:
            Dict with keys:
                - success (bool)
                - message (str)
                - suggestions (list of str)
        """
        try:
            prompt = (
                f"Suggest equipment considerations for a {char_concept}. "
                "Include 1 standard choice and 1 unconventional but useful option. "
                "Format: 2 bullet points, one per line."
            )
            text = self.ai.generate_text(prompt)
            suggestions = [line.strip() for line in text.split('\n') if line.strip()]
            return {
                "success": True,
                "message": "Equipment suggestions generated.",
                "suggestions": suggestions
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Equipment suggestions failed: {str(e)}",
                "suggestions": []
            }