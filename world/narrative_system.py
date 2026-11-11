# world/narrative_system.py
"""
Narrative System – handles backstory, connections, revelations, and pacing.
Uses OG System data for all mechanical references.
"""
import logging
import random
import re
import uuid
from typing import Dict, List, Optional, Any

from world import dnd_data
from world.ai_dungeon_master import AIDungeonMaster, GameState
from world.character import Character
from world.player import Player
from world.dm_chat_handler import DialogResponse

# Drop-in alias for the many `Dialog(...)` calls in this file that were never
# defined. DialogResponse(speaker, content, dialog_type) matches positionally.

def Dialog(speaker, content, dialog_type="narration"):
    """Local 2-or-3-arg shim; defaults dialog_type to 'narration'."""
    return DialogResponse(speaker=speaker, content=content, dialog_type=dialog_type)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 6-ability system (mirrors world.dm_chat_handler; kept local to avoid coupling)
# -----------------------------------------------------------------------------
ABILITY_KEYS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
ABILITY_ALIASES = {
    "str": "STR", "strength": "STR",
    "dex": "DEX", "dexterity": "DEX",
    "con": "CON", "constitution": "CON",
    "int": "INT", "intelligence": "INT",
    "wis": "WIS", "wisdom": "WIS",
    "cha": "CHA", "charisma": "CHA",
    # Legacy OG 4-attribute names -> nearest new ability
    "brawn": "STR", "finesse": "DEX", "wits": "INT", "will": "WIS",
}
ABILITY_MIN = 3
ABILITY_MAX = 18
STANDARD_ARRAY = (15, 14, 13, 12, 10, 8)
POINT_BUY_COSTS = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
POINT_BUY_TOTAL = 27


class NarrativeGuide:
    """Provides gentle narrative nudges based on player behavior."""
    def __init__(self):
        self.fallback_hooks = [
            "A mysterious stranger approaches you with urgent news",
            "You overhear a conversation about strange occurrences nearby",
            "A sudden environmental change demands attention"
        ]

    def get_gentle_nudge(self, player_actions):
        if player_actions.get('distracted', False):
            return "As you investigate the side path, you discover evidence connecting it to the main quest"
        if player_actions.get('off_track', False):
            return "Your exploration leads you back to the main path, where new developments await"
        return None

    def emergency_nudge(self):
        hook = random.choice(self.fallback_hooks)
        return f"Suddenly, {hook} – demanding your immediate attention"


class ConsequenceSystem:
    """Tracks player actions and applies delayed consequences."""
    def __init__(self, world_state):
        self.world = world_state
        self.action_registry = []

    def log_action(self, action, significance):
        self.action_registry.append({
            "action": action,
            "significance": significance,
            "resolved": False
        })

    def apply_delayed_consequences(self):
        unresolved = [a for a in self.action_registry if not a['resolved']]
        for action in unresolved:
            if random.random() < 0.3:  # 30% chance
                consequence = self._generate_consequence(action)
                if hasattr(self.world, 'add_event'):
                    self.world.add_event(consequence)
                action['resolved'] = True

    def _generate_consequence(self, action):
        # Placeholder – expand with actual consequence logic
        return f"Your past action '{action['action']}' has unexpected consequences."


class MotivationTracker:
    """Analyzes player actions to infer motivations."""
    def analyze_action(self, action, character):
        action_lower = action.lower()
        if any(word in action_lower for word in ["explore", "look", "search"]):
            return "curiosity"
        if any(word in action_lower for word in ["fight", "attack", "kill"]):
            return "combat"
        if any(word in action_lower for word in ["take", "loot", "steal"]):
            return "acquisition"
        if any(word in action_lower for word in ["talk", "speak", "ask"]):
            return "social"
        return "unknown"

    def get_narrative_leverage(self, motivation):
        leverage_map = {
            "curiosity": "You notice something strange that begs investigation",
            "combat": "Dangerous foes appear, blocking your path forward",
            "acquisition": "A glint of treasure catches your eye nearby",
            "social": "An NPC approaches with potentially valuable information"
        }
        return leverage_map.get(motivation, "New developments unfold around you")


class PacingController:
    """Manages narrative tension and pacing."""
    def __init__(self):
        self.current_phase = 'exploration'  # exploration, downtime, tension, climax
        self.phase_progress = 0  # 0-100
        self.player_actions = 0

    def handle_player_action(self, action_type: str):
        self.player_actions += 1
        if action_type in ['combat', 'discovery']:
            self._increase_tension(10)
        elif action_type in ['rest', 'dialogue']:
            self._decrease_tension(5)

    def handle_discovery_event(self):
        self._increase_tension(15)

    def handle_dungeon_completion(self, success: bool):
        if success:
            self.current_phase = 'downtime'
            self.phase_progress = 0
        else:
            self._increase_tension(25)

    def _increase_tension(self, amount: int):
        self.phase_progress = min(100, self.phase_progress + amount)
        if self.phase_progress >= 75 and self.current_phase != 'climax':
            self.current_phase = 'climax'
        elif self.phase_progress >= 50 and self.current_phase not in ['tension', 'climax']:
            self.current_phase = 'tension'

    def _decrease_tension(self, amount: int):
        self.phase_progress = max(0, self.phase_progress - amount)
        if self.phase_progress < 25 and self.current_phase != 'exploration':
            self.current_phase = 'exploration'
        elif self.phase_progress < 50 and self.current_phase == 'tension':
            self.current_phase = 'exploration'

    def get_pacing_recommendation(self) -> str:
        if self.current_phase == 'exploration':
            return "Introduce new locations or NPCs"
        if self.current_phase == 'downtime':
            return "Provide roleplaying opportunities"
        if self.current_phase == 'tension':
            return "Hint at upcoming dangers"
        if self.current_phase == 'climax':
            return "Trigger major story event or boss battle"
        return "Maintain current pacing"

    def get_status(self) -> dict:
        return {
            "phase": self.current_phase,
            "progress": self.phase_progress,
            "actions": self.player_actions,
            "recommendation": self.get_pacing_recommendation()
        }


class NarrativeSystem:
    """
    Main narrative coordinator. Handles character creation guidance,
    backstory development, connection webs, revelations, and pacing.
    """

    def __init__(self, world_state, ai_system, dm_chat_ai=None):
        self.world = world_state
        self.ai = ai_system

        # Load narrative framework from OG System JSON
        self.narrative_framework = getattr(world_state, 'narrative_framework', {})

        # Initialize sub‑systems
        self.guide = NarrativeGuide()
        self.consequences = ConsequenceSystem(world_state)
        self.motivation = MotivationTracker()
        self.pacing = PacingController()

        # DM system (optional)
        if ai_system:
            self.dm = AIDungeonMaster(dm_chat_ai=dm_chat_ai)
            self.game_state = GameState()
        else:
            self.dm = None
            self.game_state = None

        # Active backstory creation sessions (character_id -> state)
        self.backstory_sessions = {}

    def on_location_discovered(self, location_id: str):
        """Handle location discovery: update pacing and trigger narrative hooks."""
        # Update pacing
        self.pacing.handle_discovery_event()

        # Get the location from world map
        location = self.world.world_map.get_location(location_id)
        if not location:
            return

        # If this is the first discovery, you might want to generate a quest or log it
        if not location.discovered:
            # Mark as discovered (though world_controller already does this)
            location.discovered = True

            # Optional: generate a quest for this location (will be implemented later)
            # For now, just log it
            if hasattr(self, 'session_log'):
                self.session_log.append(f"Discovered {location.name}")

            # Future: self.generate_quest(location_id, "First discovery")

    # ----------------------------------------------------------------------
    # Character Creation Guidance (OG System)
    # ----------------------------------------------------------------------
    def guide_character_creation(self, player_id, message, creation_state):
        """
        Fully guided character creation using OG System data.
        Flow: welcome (name) -> attribute_method -> attribute_assignment ->
              race_selection -> [racial_choice] -> class_selection ->
              background_selection -> skill_selection -> personality_development ->
              name_input -> finalization.
        Returns {responses, new_state}; new_state is None once the character is built.
        """
        if not isinstance(creation_state, dict) or not creation_state:
            creation_state = {
                'phase': 'welcome',
                'name': None,
                'method': None,
                'abilities': {},
                'race': None,
                'class': None,
                'background': None,
                'skills': [],
                'personality': None,
                'ideals': None,
                'bonds': None,
                'flaws': None,
                'conversation': [],
            }

        if message:
            creation_state['conversation'].append(("player", message))

        responses = []
        phase = creation_state['phase']

        def get_background_guide(bg_name):
            guides = {
                "acolyte": {"description": "Devoted to a faith.", "skills": ["Lore", "Social"]},
                "criminal": {"description": "Lived outside the law.", "skills": ["Stealth", "Social"]},
                "folk hero": {"description": "Champion of the common people.", "skills": ["Athletics", "Survival"]},
                "sage": {"description": "Scholar of forgotten lore.", "skills": ["Lore", "Craft"]},
                "soldier": {"description": "Trained for war.", "skills": ["Athletics", "Survival"]},
            }
            return guides.get(bg_name.lower(), {"description": bg_name, "skills": []})

        # --- welcome: collect the character's name ---
        if phase == 'welcome':
            if not message:
                responses.append(Dialog("DM", "Welcome, adventurer! What is your name?"))
            else:
                creation_state['name'] = message.strip()
                creation_state['phase'] = 'attribute_method'
                responses.append(Dialog(
                    "DM",
                    f"Pleased to meet you, {creation_state['name']}. "
                    f"How would you like to determine your abilities?\n"
                    f"- Standard Array (recommended): {', '.join(map(str, STANDARD_ARRAY))}, freely assignable\n"
                    f"- Point Buy: {POINT_BUY_TOTAL} points, scores 8-15\n"
                    f"Which method?"
                ))

        # --- attribute_method: choose standard array vs point buy ---
        elif phase == 'attribute_method':
            method_input = (message or "").strip().lower()
            if not message:
                responses.append(Dialog(
                    "DM",
                    f"How would you like to determine your abilities?\n"
                    f"- Standard Array: {', '.join(map(str, STANDARD_ARRAY))}\n"
                    f"- Point Buy: {POINT_BUY_TOTAL} points, scores 8-15\n"
                    f"Which method?"
                ))
            elif 'point' in method_input or 'buy' in method_input:
                creation_state['method'] = 'point_buy'
                creation_state['phase'] = 'attribute_assignment'
                responses.append(Dialog(
                    "DM",
                    f"Point Buy: assign scores 8-15 to STR, DEX, CON, INT, WIS, CHA. "
                    f"Cost: 8->0, 9->1, 10->2, 11->3, 12->4, 13->5, 14->7, 15->9. "
                    f"Total must be exactly {POINT_BUY_TOTAL}.\n"
                    f"Reply like: 'STR 15, DEX 14, CON 13, INT 12, WIS 10, CHA 8'"
                ))
            else:
                creation_state['method'] = 'standard'
                creation_state['phase'] = 'attribute_assignment'
                responses.append(Dialog(
                    "DM",
                    f"Standard Array: assign these to STR, DEX, CON, INT, WIS, CHA "
                    f"(one of each): {', '.join(map(str, STANDARD_ARRAY))}.\n"
                    f"Reply like: 'STR 15, DEX 14, CON 13, INT 12, WIS 10, CHA 8'"
                ))

        # --- attribute_assignment: parse and validate ---
        elif phase == 'attribute_assignment':
            assignments = self._parse_ability_assignments(message)
            method = creation_state.get('method', 'standard')
            if not assignments:
                responses.append(Dialog(
                    "DM",
                    "I didn't catch that. Reply like: 'STR 15, DEX 14, CON 13, INT 12, WIS 10, CHA 8'",
                    "error"
                ))
            elif set(assignments.keys()) != set(ABILITY_KEYS):
                missing = sorted(set(ABILITY_KEYS) - set(assignments.keys()))
                responses.append(Dialog("DM", f"Missing abilities: {', '.join(missing)}. Try again.", "error"))
            elif method == 'standard':
                if sorted(assignments.values()) != sorted(STANDARD_ARRAY):
                    responses.append(Dialog(
                        "DM",
                        f"Standard Array requires exactly one each of {sorted(STANDARD_ARRAY)}. Try again.",
                        "error"
                    ))
                else:
                    creation_state['abilities'] = dict(assignments)
                    creation_state['phase'] = 'race_selection'
                    responses.append(Dialog(
                        "DM",
                        f"Abilities set: {assignments}. Now choose your race:\n"
                        + ", ".join(dnd_data.get_race_list())
                    ))
            else:  # point_buy
                out_of_range = {k: v for k, v in assignments.items() if not (8 <= v <= 15)}
                if out_of_range:
                    responses.append(Dialog("DM", f"Point Buy scores must be 8-15: {out_of_range}. Try again.", "error"))
                else:
                    total = sum(POINT_BUY_COSTS[v] for v in assignments.values())
                    if total != POINT_BUY_TOTAL:
                        responses.append(Dialog("DM", f"Cost is {total}, must be exactly {POINT_BUY_TOTAL}. Try again.", "error"))
                    else:
                        creation_state['abilities'] = dict(assignments)
                        creation_state['phase'] = 'race_selection'
                        responses.append(Dialog(
                            "DM",
                            f"Abilities set: {assignments}. Now choose your race:\n"
                            + ", ".join(dnd_data.get_race_list())
                        ))

        # --- race_selection ---
        elif phase == 'race_selection':
            if not message:
                responses.append(Dialog(
                    "DM",
                    f"Races: {', '.join(dnd_data.get_race_list())}. Which one calls to you?"
                ))
            else:
                race = dnd_data.Race.get(message)
                if not race:
                    responses.append(Dialog("DM", f"'{message}' is not a valid race. Try again.", "error"))
                else:
                    creation_state['race'] = race.name
                    spec = race.choice_spec()
                    if spec:
                        creation_state['phase'] = 'racial_choice'
                        creation_state['pending_race'] = race
                        if spec.get('count', 1) == 1:
                            prompt = f"{race.name} grants +1 to one of: {', '.join(spec['from'])}. Choose one."
                        else:
                            prompt = (
                                f"{race.name} grants +1 to each of {spec['count']} abilities from: "
                                f"{', '.join(spec['from'])}. Choose {spec['count']}."
                            )
                        responses.append(Dialog("DM", prompt))
                    else:
                        bonuses = race.apply_choices([])
                        self._apply_ability_bonuses(creation_state['abilities'], bonuses)
                        creation_state['phase'] = 'class_selection'
                        responses.append(Dialog(
                            "DM",
                            f"{race.name} bonuses applied: {bonuses}.\n"
                            f"Now choose your class: {', '.join(dnd_data.get_class_list())}"
                        ))

        # --- racial_choice ---
        elif phase == 'racial_choice':
            race = creation_state['pending_race']
            chosen = [p.strip() for p in (message or "").split(",") if p.strip()]
            try:
                bonuses = race.apply_choices(chosen)
            except ValueError as exc:
                responses.append(Dialog("DM", str(exc), "error"))
                return self._wrap_creation_response(responses, creation_state, message)
            self._apply_ability_bonuses(creation_state['abilities'], bonuses)
            creation_state['phase'] = 'class_selection'
            creation_state.pop('pending_race', None)
            responses.append(Dialog(
                "DM",
                f"Bonuses applied: {bonuses}. Now choose your class: {', '.join(dnd_data.get_class_list())}"
            ))

        # --- class_selection ---
        elif phase == 'class_selection':
            if not message:
                responses.append(Dialog("DM", f"Classes: {', '.join(dnd_data.get_class_list())}. Which profession?"))
            else:
                cls = dnd_data.OGClass.get(message)
                if not cls:
                    responses.append(Dialog("DM", f"'{message}' is not a valid class.", "error"))
                else:
                    creation_state['class'] = cls.name
                    creation_state['phase'] = 'background_selection'
                    responses.append(Dialog(
                        "DM",
                        f"{cls.name}: {cls.core_mechanic.get('description', '')}\n"
                        f"HP per level: {cls.hp_per_level}, SP per level: {cls.sp_per_level}\n"
                        f"Subclasses: {', '.join(cls.subclasses.keys())}\n"
                        f"Now choose your background."
                    ))

        # --- background_selection ---
        elif phase == 'background_selection':
            if not message:
                responses.append(Dialog("DM", "Backgrounds: Acolyte, Criminal, Folk Hero, Sage, Soldier. Which fits your past?"))
            else:
                bg = get_background_guide(message)
                if not bg or not bg.get('description'):
                    responses.append(Dialog("DM", f"'{message}' not recognized. Choose from: Acolyte, Criminal, Folk Hero, Sage, Soldier.", "error"))
                else:
                    creation_state['background'] = message
                    creation_state['phase'] = 'skill_selection'
                    responses.append(Dialog(
                        "DM",
                        f"{message}: {bg['description']}. You gain proficiency in {', '.join(bg['skills'])}.\n"
                        f"Now select 3 skills: " + ", ".join(s.name for s in dnd_data.Skill.all())
                    ))

        # --- skill_selection ---
        elif phase == 'skill_selection':
            if not message:
                responses.append(Dialog("DM", "Please list 3 skills (e.g., 'Survival, Lore, Stealth')."))
            else:
                chosen = [s.strip() for s in message.split(',') if s.strip()]
                valid_skills = [s.name for s in dnd_data.Skill.all()]
                if len(chosen) != 3 or not all(s in valid_skills for s in chosen):
                    responses.append(Dialog("DM", "Please choose exactly 3 valid skills.", "error"))
                else:
                    creation_state['skills'] = chosen
                    creation_state['phase'] = 'personality_development'
                    responses.append(Dialog(
                        "DM",
                        f"Skills chosen: {', '.join(chosen)}. Now let's develop your personality.\n"
                        "How would you describe your character's personality? (e.g., brave, cunning, stoic)"
                    ))

        # --- personality_development ---
        elif phase == 'personality_development':
            if not creation_state.get('personality'):
                creation_state['personality'] = message
                responses.append(Dialog("DM", "What ideals drive your character? (e.g., justice, freedom)"))
            elif not creation_state.get('ideals'):
                creation_state['ideals'] = message
                responses.append(Dialog("DM", "What bonds connect your character to the world? (e.g., family, oath)"))
            elif not creation_state.get('bonds'):
                creation_state['bonds'] = message
                responses.append(Dialog("DM", "What flaws or weaknesses does your character have? (e.g., pride, fear)"))
            elif not creation_state.get('flaws'):
                creation_state['flaws'] = message
                creation_state['phase'] = 'name_input'
                responses.append(Dialog("DM", "One last thing -- what is your character's name?"))

        # --- name_input: build the character ---
        elif phase == 'name_input':
            if not message:
                responses.append(Dialog("DM", "What is your character's name?"))
            else:
                creation_state['name'] = message.strip()
                try:
                    character = self._finalize_character(creation_state, owner_id=player_id)
                    class_name = (
                        character.classs.name
                        if getattr(character, 'classs', None) else "adventurer"
                    )
                    responses.append(Dialog(
                        "DM",
                        f"Behold {character.name}, the {character.race} {class_name}!\n"
                        f"Your journey begins now.",
                        "narration"
                    ))
                    creation_state = None
                except Exception as exc:
                    logger.exception("Character finalization failed")
                    responses.append(Dialog(
                        "DM",
                        f"I couldn't complete your character: {exc}. "
                        f"Let's try again -- what is your character's name?",
                        "error"
                    ))
                    creation_state['name'] = None

        return self._wrap_creation_response(responses, creation_state, message)

    # ------------------------------------------------------------------
    # helpers for guide_character_creation
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_ability_bonuses(abilities: dict, bonuses: dict) -> None:
        """Apply race bonuses in place, translating legacy names (brawn -> STR, etc.)."""
        for ab, bonus in (bonuses or {}).items():
            key = ABILITY_ALIASES.get(str(ab).lower(), str(ab).upper())
            if key in ABILITY_KEYS and key in abilities:
                abilities[key] = min(ABILITY_MAX, abilities[key] + bonus)

    @staticmethod
    def _parse_ability_assignments(message: str) -> dict:
        """Parse 'STR 15, DEX 14, ...' (or full names, or legacy names) -> {'STR': 15, ...}."""
        if not message:
            return {}
        tokens = re.split(r'[,\s;]+', message.strip())
        result = {}
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            key = ABILITY_ALIASES.get(tok.lower())
            if key is None and tok.upper() in ABILITY_KEYS:
                key = tok.upper()
            if key and i + 1 < len(tokens):
                try:
                    result[key] = int(tokens[i + 1])
                    i += 2
                    continue
                except ValueError:
                    pass
            i += 1
        return result

    @staticmethod
    def _wrap_creation_response(responses, creation_state, message):
        """Shared return shaping: prepend the player's message, dict-ify DialogResponses."""
        if message:
            responses.insert(0, Dialog("Player", message, "character"))
        return {
            "responses": [r.to_dict() for r in responses],
            "new_state": creation_state,
        }

    def _finalize_character(self, char_data, owner_id=None):
        """
        Build a Character from collected creation data.
        HP/SP/defense are computed by Character from abilities; not passed as kwargs.
        """
        abilities = dict(char_data.get('abilities') or {})
        for k in ABILITY_KEYS:
            abilities.setdefault(k, 10)  # safety net; creation flow always fills all 6

        char_kwargs = {
            "name": char_data.get('name') or "Unnamed",
            "race": char_data['race'],
            "classs": char_data['class'],
            "level": 1,
            "abilities": abilities,
        }

        # Try with owner_id as a kwarg, fall back to attribute assignment if the
        # Character signature doesn't accept it.
        try:
            character = Character(owner_id=owner_id, **char_kwargs)
        except TypeError:
            character = Character(**char_kwargs)
            if owner_id and hasattr(character, "owner_id"):
                character.owner_id = owner_id

        # Skills dict (matches dm_chat_handler expectations: {name: rank})
        character.skills = {s: 1 for s in (char_data.get('skills') or [])}

        # Narrative fields
        character.backstory = {
            "personality": char_data.get('personality'),
            "ideals": char_data.get('ideals'),
            "bonds": char_data.get('bonds'),
            "flaws": char_data.get('flaws'),
            "background": char_data.get('background'),
        }
        if getattr(character, "connections", None) is None:
            character.connections = []
        if getattr(character, "secrets", None) is None:
            character.secrets = []
        if getattr(character, "vows", None) is None:
            character.vows = {}

        self.world.character_manager.add_character(character)
        return character

    # ----------------------------------------------------------------------
    # Backstory Creation (from 17_player_narrative.json)
    # ----------------------------------------------------------------------
    def guide_backstory_creation(self, character_id, message, creation_state):
        """
        Guided backstory creation using OG System framework.
        Expects creation_state to track phase (origin, wound, recent, secret_generation).
        """
        character = self.world.character_manager.get_character(character_id)
        if not character:
            return {"error": "Character not found"}

        # Load backstory framework from self.narrative_framework (loaded from JSON)
        framework = self.narrative_framework.get("backstory_framework", {})
        phases = framework.get("phases", [])

        if not creation_state:
            creation_state = {
                'phase': 'origin',
                'backstory': {},
                'conversation': []
            }

        if message:
            creation_state['conversation'].append(("player", message))

        responses = []
        current_phase = creation_state['phase']

        # Helper to find phase data by name
        def get_phase_data(phase_name):
            for p in phases:
                if p.get("phase") == phase_name:
                    return p
            return None

        if current_phase == 'origin':
            phase_data = get_phase_data('origin')
            if not creation_state['backstory'].get('origin'):
                # First time – show prompts
                prompts = phase_data.get('prompts', [])
                if not message:
                    # Initial prompt
                    responses.append(Dialog("DM", "Let's start with your origin. " + " ".join(prompts), "narration"))
                else:
                    # Store answers – for simplicity, store the whole message as origin dict
                    # In a full implementation, you'd parse answers to match prompts.
                    creation_state['backstory']['origin'] = {"raw": message}
                    creation_state['phase'] = 'formative_wound'
                    responses.append(Dialog("DM", "Now, tell me about the formative wound that shaped you.", "narration"))
            else:
                creation_state['phase'] = 'formative_wound'

        if current_phase == 'formative_wound':
            phase_data = get_phase_data('formative_wound')
            if not creation_state['backstory'].get('formative_wound'):
                if not message:
                    prompts = phase_data.get('prompts', [])
                    responses.append(Dialog("DM", "Your formative wound: " + " ".join(prompts), "narration"))
                else:
                    creation_state['backstory']['formative_wound'] = {"raw": message}
                    creation_state['phase'] = 'recent_history'
                    responses.append(Dialog("DM", "Now, what about your recent history?", "narration"))
            else:
                creation_state['phase'] = 'recent_history'

        if current_phase == 'recent_history':
            phase_data = get_phase_data('recent_history')
            if not creation_state['backstory'].get('recent_history'):
                if not message:
                    prompts = phase_data.get('prompts', [])
                    responses.append(Dialog("DM", "Your recent history: " + " ".join(prompts), "narration"))
                else:
                    creation_state['backstory']['recent_history'] = {"raw": message}
                    creation_state['phase'] = 'secret_generation'
                    responses.append(Dialog("DM", "Thank you. I will now weave in some hidden secrets...", "narration"))
            else:
                creation_state['phase'] = 'secret_generation'

        if current_phase == 'secret_generation':
            # Generate 1-2 secrets using framework rules
            secret_framework = framework.get("secret_generation", {})
            secret_types = secret_framework.get("types", {})
            triggers = secret_framework.get("revelation_triggers", [])
            import random
            rng = random.Random(self.world.seed + hash(character.id))
            num_secrets = rng.randint(1, 2)
            for i in range(num_secrets):
                sec_type = rng.choice(list(secret_types.keys()))
                trigger = rng.choice(triggers) if triggers else {"type": "random", "target": ""}
                secret = {
                    "id": str(uuid.uuid4()),
                    "type": sec_type,
                    "description": f"A hidden truth: {secret_types[sec_type]}",
                    "revelation_trigger": trigger,
                    "revealed": False
                }
                if 'secrets' not in creation_state['backstory']:
                    creation_state['backstory']['secrets'] = []
                creation_state['backstory']['secrets'].append(secret)

            # Store backstory in character
            character.backstory = creation_state['backstory']
            creation_state = None   # finished
            responses.append(Dialog("DM", "Your backstory is complete. Secrets lie waiting to be discovered.", "narration"))

            # Optionally build connection web now
            self.build_connection_web_for_character(character_id)

        # Add player message to history if exists
        if message:
            responses.insert(0, Dialog("Player", message, "character"))

        return {
            "responses": [r.to_dict() for r in responses],
            "new_state": creation_state
        }

    # ----------------------------------------------------------------------
    # Connection Web
    # ----------------------------------------------------------------------
    def build_connection_web_for_character(self, character_id):
        """
        Generate connections between a character's backstory and world elements.
        Populates character.connections and character.secrets.
        """
        character = self.world.character_manager.get_character(character_id)
        if not character:
            return

        # Gather world elements
        elements = []
        # Regions
        for region in self.world.campaign_state.surface_regions.values():
            elements.append(("region", region.id, region.name, region.terrain_tags))
        # Factions
        for faction in self.world.campaign_state.factions.values():
            elements.append(("faction", faction.id, faction.name, faction.goals))
        # Locations (settlements, dungeons) from world_map
        for loc in self.world.world_map.locations.values():
            elements.append(("location", loc.id, loc.name, [loc.type]))
        # NPCs (if any)
        if hasattr(self.world.world_map, 'npcs'):
            for npc in self.world.world_map.npcs.values():   # assuming world_map has npcs
                elements.append(("npc", npc.id, npc.name, [npc.role]))

        # Use seed for determinism
        rng = random.Random(self.world.seed + hash(character.id))

        # Define connection types
        connection_types = ["direct", "reflection", "consequence", "parallel", "inversion", "prophecy"]

        # Keep track of used element IDs to avoid duplicates
        used_elements = set()

        # For each backstory node, try to create connections
        backstory = character.backstory
        if not backstory:
            return

        # Origin
        if "origin" in backstory:
            origin = backstory["origin"]
            origin_region = origin.get("origin_region")
            if origin_region:
                # Try to find a region with matching ID
                for etype, eid, ename, etags in elements:
                    if etype == "region" and eid == origin_region:
                        self._add_connection(character, "direct", "origin", etype, eid,
                                             f"Your homeland, {ename}.", rng, used_elements)
                        break

        # Formative wound
        if "formative_wound" in backstory:
            wound = backstory["formative_wound"]
            wound_actor_id = wound.get("wound_actor", {}).get("id")
            if wound_actor_id:
                for etype, eid, ename, etags in elements:
                    if eid == wound_actor_id:
                        self._add_connection(character, "direct", "formative_wound", etype, eid,
                                             f"The one who wronged you: {ename}.", rng, used_elements)
                        break

        # Recent history
        if "recent_history" in backstory:
            recent = backstory["recent_history"]
            debt_to = recent.get("outstanding_debt", {}).get("to")
            if debt_to:
                for etype, eid, ename, etags in elements:
                    if eid == debt_to:
                        self._add_connection(character, "direct", "recent_history", etype, eid,
                                             f"You owe a debt to {ename}.", rng, used_elements)
                        break

        # Ensure at least 2-3 connections. If not enough, create random ones.
        needed = max(0, 2 - len(character.connections))
        for _ in range(needed):
            # Pick a random element not used yet
            candidates = [e for e in elements if e[1] not in used_elements]
            if not candidates:
                break
            etype, eid, ename, etags = rng.choice(candidates)
            conn_type = rng.choice(connection_types)
            self._add_connection(character, conn_type, "random", etype, eid,
                                 f"A mysterious link to {ename}.", rng, used_elements)

        # Generate one hidden secret connection
        secret_type = rng.choice(["lineage", "connection", "prophecy", "infection", "duplicity", "obligation"])
        # Pick a random element that hasn't been used for a direct connection
        secret_candidates = [e for e in elements if e[1] not in used_elements]
        if secret_candidates:
            etype, eid, ename, etags = rng.choice(secret_candidates)
            secret = {
                "id": str(uuid.uuid4()),
                "type": secret_type,
                "description": f"Unknown truth linking you to {ename}.",
                "revelation_trigger": self._generate_trigger(etype, eid, rng),
                "revealed": False
            }
            character.secrets.append(secret)

    def _add_connection(self, character, conn_type, backstory_node, target_type, target_id, description, rng, used_elements):
        """Helper to create a connection dict and append to character.connections."""
        conn = {
            "id": str(uuid.uuid4()),
            "type": conn_type,
            "pc_node": backstory_node,
            "world_element": {"type": target_type, "id": target_id},
            "description": description,
            "tension": rng.choice(["harmony", "irony", "tragedy", "hope", "mystery"]),
            "visibility": "hidden" if backstory_node == "random" else "hinted"
        }
        character.connections.append(conn)
        used_elements.add(target_id)

    def _generate_trigger(self, etype, eid, rng):
        """Generate a revelation trigger for a secret based on world element type."""
        triggers = {
            "region": {"type": "enter_region", "target": eid},
            "faction": {"type": "meet_faction", "target": eid},
            "location": {"type": "enter_location", "target": eid},
            "npc": {"type": "meet_npc", "target": eid}
        }
        return triggers.get(etype, {"type": "random", "target": eid})

    # ----------------------------------------------------------------------
    # Revelation System
    # ----------------------------------------------------------------------
    def _check_revelation_triggers(self, character, context):
        """Check if any secret's trigger matches the current context."""
        for secret in character.secrets:
            if secret.get('revealed'):
                continue
            trigger = secret.get('revelation_trigger', {})
            trigger_type = trigger.get('type')
            target = trigger.get('target')

            if trigger_type == 'enter_region' and context.get('region_id') == target:
                self._deliver_revelation(character, secret, context)
            elif trigger_type == 'enter_location' and context.get('location_id') == target:
                self._deliver_revelation(character, secret, context)
            elif trigger_type == 'meet_faction' and target in context.get('faction_ids', []):
                self._deliver_revelation(character, secret, context)
            elif trigger_type == 'meet_npc' and target in context.get('npc_ids', []):
                self._deliver_revelation(character, secret, context)
            elif trigger_type == 'random' and random.random() < 0.05:
                self._deliver_revelation(character, secret, context)

    def _deliver_revelation(self, character, secret, context):
        """Generate a revelation dialog and update secret."""
        secret['revealed'] = True
        methods = ["environmental", "npc_slip", "confrontation", "dream_vision", "item_resonance", "transformation", "research", "betrayal"]
        method = random.choice(methods)

        lines = {
            "lineage": "You discover your true parentage...",
            "connection": "You realize that person is not who they seemed...",
            "prophecy": "An ancient prophecy speaks of you...",
            "infection": "Something stirs within you...",
            "duplicity": "You did something you don't remember...",
            "obligation": "A debt you didn't know you owed comes due..."
        }
        description = lines.get(secret['type'], "A truth is revealed.")

        if self.dm:
            self.dm.add_dialog(Dialog("DM", f"{description} ({method})", "revelation"))

    # ----------------------------------------------------------------------
    # Player Action Processing
    # ----------------------------------------------------------------------
    def process_player_action(self, player_id: str, message: str):
        """Process player input, update pacing, check revelations, and return DM response."""
        if not self.dm:
            return {
                "responses": [
                    DialogResponse(
                        speaker="DM",
                        content="Narrative system is not fully initialized",
                        dialog_type="system"
                    )
                ],
                "dialog_history": []
            }

        # Update game state with current scene
        self.game_state.current_scene = self.world.get_current_scene()

        # Analyze motivation and update pacing
        player = self.world.players.get(player_id)
        character = None
        if player and player.active_character_id:
            character = self.world.character_manager.get_character(player.active_character_id)

        motivation = self.motivation.analyze_action(message, character)
        action_type_map = {
            "combat": "combat",
            "curiosity": "discovery",
            "acquisition": "discovery",
            "social": "dialogue",
            "unknown": "dialogue"
        }
        pacing_action_type = action_type_map.get(motivation, "dialogue")
        self.pacing.handle_player_action(pacing_action_type)

        # Log for consequences
        self.consequences.log_action(message, motivation)

        # Get DM response
        dialogs = self.dm.process_player_input(player_id, message)
        responses = list(dialogs)

        # Gentle nudge if needed
        guidance = self.guide.get_gentle_nudge({'action': message, 'motivation': motivation, 'pacing': self.pacing.current_phase})
        if guidance:
            responses.append(DialogResponse(speaker="DM", content=guidance, dialog_type= "narration"))

        # Check revelations
        if character:
            context = {
                'location_id': self.world.current_location.id if self.world.current_location else None,
                'region_id': getattr(self.world.current_location, 'region_id', None),
                'faction_ids': [],  # TODO: populate
                'npc_ids': []       # TODO: populate
            }
            self._check_revelation_triggers(character, context)

        # Process consequences periodically
        if random.random() < 0.3:
            self.consequences.apply_delayed_consequences()

        return {
            "responses": responses,
            "dialog_history": [d.to_dict() for d in self.dm.get_dialog_history()],
            "motivation": motivation,
            "pacing": self.pacing.get_status()
        }

    # ----------------------------------------------------------------------
    # Scene Management
    # ----------------------------------------------------------------------
    def set_current_scene(self, scene_description: str):
        """Update the current scene for narrative context."""
        if self.game_state is not None:
            self.game_state.current_scene = scene_description
        if self.dm:
            self.dm.game_state.current_scene = scene_description

    # ----------------------------------------------------------------------
    # Utility: Execute narrative commands (vows, bonuses, etc.)
    # ----------------------------------------------------------------------
    def execute_narrative_command(self, command: str, context: dict) -> dict:
        """
        Execute a narrative‑system command (e.g., vow advancement).
        See previous answer for implementation.
        """
        parts = command.split()
        if not parts:
            return {"success": False, "error": "Empty command"}

        cmd = parts[0]
        if cmd == "vow_advance" and len(parts) == 4:
            char_id, vow_id, amount = parts[1], parts[2], int(parts[3])
            character = self.world.character_manager.get_character(char_id)
            if character and vow_id in character.vows:
                character.vows[vow_id]['progress'] += amount
                return {"success": True, "message": f"Vow {vow_id} advanced by {amount}"}
        elif cmd == "vow_complete" and len(parts) == 3:
            char_id, vow_id = parts[1], parts[2]
            character = self.world.character_manager.get_character(char_id)
            if character and vow_id in character.vows:
                character.vows[vow_id]['status'] = 'complete'
                return {"success": True, "message": f"Vow {vow_id} completed"}
        # Add more commands as needed

        return {"success": False, "error": f"Unknown command: {cmd}"}