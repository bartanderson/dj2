# world/character_builder.py
from world.character import Character  # Now using our OG System Character
from world import dnd_data
from .tool_system import tool
from typing import Dict, Any, Optional, List

class CharacterBuilder:
    """Builds characters with AI‑enhanced personality, background, and items."""

    def __init__(self, ai_system):
        self.ai = ai_system

    def _create_character_impl(self, owner_id: str, char_data: dict,
                               context: dict = None) -> Character:
        """Internal: builds and returns Character. Raises on validation failure.
        The decorated `create_character` wraps this for tool-calling safety.
        """
        from world.character import Character, ABILITIES, SCORE_MIN, SCORE_MAX

        required = ("name", "race", "class")
        missing = [f for f in required if not char_data.get(f)]
        if missing:
            raise ValueError(f"Missing required field(s): {', '.join(missing)}")

        class_name = char_data["class"]
        if not dnd_data.validate_class(class_name):
            raise ValueError(f"Unknown class: {class_name}")
        char_class = dnd_data.get_class_object(class_name)

        race = dnd_data.Race.get(char_data["race"])
        if not race:
            raise ValueError(f"Unknown race: {char_data['race']}")

        # --- Abilities (pre-racial) ---
        raw = char_data.get("abilities")
        if raw is None:
            raise ValueError(
                "char_data['abilities'] required: dict of STR/DEX/CON/INT/WIS/CHA "
                "(pre-racial scores)"
            )
        pre_racial = {ab: int(raw.get(ab, 10)) for ab in ABILITIES}
        for ab, score in pre_racial.items():
            if not (SCORE_MIN <= score <= SCORE_MAX):
                raise ValueError(f"Ability {ab}={score} out of range {SCORE_MIN}-{SCORE_MAX}")

        # --- Racial choice validation + application ---
        chosen: List[str] = list(char_data.get("racial_choice") or [])
        racial_bonuses = race.apply_choices(chosen)  # raises on invalid

        abilities = dict(pre_racial)
        for ab, bonus in racial_bonuses.items():
            abilities[ab] = min(SCORE_MAX, abilities[ab] + bonus)

        # --- Proficiencies from class (fallbacks if class data absent) ---
        save_profs = list(getattr(char_class, "save_proficiencies", []) or [])
        skill_profs = list(char_data.get("skill_proficiencies") or [])
        if not skill_profs:
            # Default 3 from class skill list (drawn from core skill names).
            # This is deterministic, not random.
            all_skills = dnd_data.get_skill_list()
            skill_profs = all_skills[:3]

        # --- Build Character ---
        character = Character(
            name=char_data["name"],
            race=race.name,
            classs=char_class,
            level=int(char_data.get("level", 1)),
            background=char_data.get("background", "unknown"),
            owner_id=owner_id,
            abilities=abilities,
            save_proficiencies=save_profs,
            skill_proficiencies=skill_profs,
            skill_expertise=list(char_data.get("skill_expertise") or []),
            age=char_data.get("age"),
            gender=char_data.get("gender"),
            description=char_data.get("description"),
            alignment=char_data.get("alignment"),
            backstory={"story": self.generate_background_story(char_data, context).get("story", "")},
        )

        # AI-generated extras (unchanged behaviour)
        personality = self.generate_personality(char_data, context)
        character.ai_personality = {
            "traits": personality.get("traits", ""),
            "ideals": personality.get("ideals", ""),
            "bonds": personality.get("bonds", ""),
            "flaws": personality.get("flaws", ""),
        }
        if char_data.get("personal_item"):
            item = char_data["personal_item"]
            character.add_custom_item(
                item.get("name", "Mysterious Item"),
                item.get("description", "A strange object of unknown origin."),
            )
        return character


    @tool(name="create_character", description="...")
    def create_character(self, owner_id: str, char_data: dict, context: dict = None) -> dict:
        try:
            character = self._create_character_impl(owner_id, char_data, context)
            return {
                "success": True,
                "message": f"Character {character.name} created.",
                "character": character,
            }
        except Exception as e:
            return {"success": False, "message": f"Character creation failed: {e}"}
        
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