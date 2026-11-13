# dm_chat_handler.py – OG System version with AI topic extraction

import json
import logging
import re
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import time
import copy

from world import dnd_data
from world.character import Character
from world.character_agent import CharacterAgent, DEFAULT_DRAFT
from world.equip_agent import EquipAgent, DEFAULT_EQUIP_DRAFT
from world.action_system import ActionPlanner, ActionQueue
from world.resolver import ResolverLoop
from world.intent import IntentFrame
from world.adjudication_engine import AdjudicationEngine
from world.intent_parser import IntentParser

DEBUG = True # False to turn off debug prints

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# New 6-ability system (dj2 ability redesign)
# -----------------------------------------------------------------------------
ABILITY_KEYS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
ABILITY_ALIASES = {
    "str": "STR", "strength": "STR",
    "dex": "DEX", "dexterity": "DEX",
    "con": "CON", "constitution": "CON",
    "int": "INT", "intelligence": "INT",
    "wis": "WIS", "wisdom": "WIS",
    "cha": "CHA", "charisma": "CHA",
    # Legacy 4-attribute names kept as a migration safety net
    "brawn": "STR", "finesse": "DEX", "wits": "INT", "will": "WIS",
}
ABILITY_MIN = 3
ABILITY_MAX = 18

@dataclass
class DialogResponse:
    """A single response in a dialog turn."""
    speaker: str  # 'DM' or 'Player'
    content: str
    dialog_type: str  # 'narration', 'question', 'suggestion', etc.
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            "speaker": self.speaker,
            "content": self.content,
            "dialog_type":self.dialog_type,
            "timestamp":self.timestamp
        }

# Pack contents lookup: maps pack names to lists of (name, description, quantity) tuples.
PACK_CONTENTS = {
    "explorer": [
        ("Explorer's Pack", "Standard explorer's gear", 1),
        ("Rations", "Trail rations (1 day)", 5),
        ("Water Skin", "Canteen with fresh water", 1),
        ("Bedroll", "Soft bedroll for resting", 1),
        ("Torch", "Wooden torch (10 ft. light)", 5),
        ("Hunting Trap", "Wooden snare trap", 2),
        ("Climber's Chalk", "Chalk bag for scaling", 1),
    ],
    "adventurer": [
        ("Adventurer's Pack", "Standard adventuring gear", 1),
        ("Rations", "Trail rations (1 day)", 5),
        ("Water Skin", "Canteen with fresh water", 1),
        ("Bedroll", "Soft bedroll for resting", 1),
        ("Torch", "Wooden torch (10 ft. light)", 5),
        ("Hunting Trap", "Wooden snare trap", 2),
    ],
    "dungeoneer": [
        ("Dungeoneer's Pack", "Standard dungeon gear", 1),
        ("Rations", "Trail rations (1 day)", 5),
        ("Water Skin", "Canteen with fresh water", 1),
        ("Bedroll", "Soft bedroll for resting", 1),
        ("Hempen Rope (50 ft.)", "Rope for climbing and binding", 1),
        ("Torch", "Wooden torch (10 ft. light)", 5),
        ("Chalk", "Marking chalk", 1),
        ("Flask of Oil", "Small clay oil flask", 1),
    ],
}

def _apply_pack_items(pack_name: str, character):
    """Apply pack items to a character's inventory based on pack type name."""
    key = next((k for k in PACK_CONTENTS if k in pack_name.lower()), None)
    if not key:
        # Default to explorer's pack if no match
        key = "explorer"
    from world.character import InventoryItem
    for item_name, description, quantity in PACK_CONTENTS[key]:
        character.inventory.append(InventoryItem(
            name=item_name,
            description=description,
            quantity=quantity,
            type="adventuring_gear",
        ))

class DMChatHandler:
    """
    Handles DM chat interactions, character creation, and game progression.
    Uses OG System data and AI for topic extraction and responses.
    """

    def __init__(self, world_controller):
        self.world_controller = world_controller
        self.adjudication_engine = AdjudicationEngine(world_controller)

    def should_invoke_ai(self, result: dict) -> bool:
        """Determines whether AI narration should run."""
        if not result:
            return False
        if result.get("error"):
            return False
        if result.get("clarification"):
            return False
        if result.get("action") in {"centerOnParty", "move"}:
            return False
        if not result.get("message", "").strip():
            return False
        return True

    def _build_game_context(self, session, character: Optional[Character] = None) -> Dict[str, Any]:
        """
        Build a context dictionary of OG System data for the AI prompt.
        Includes lists of races, classes, skills, attributes, spells, etc.
        """

        context = {
            "classes": dnd_data.get_class_list(),
            "races": dnd_data.get_race_list(),
            "skills": dnd_data.get_skill_list(),
            "attributes": dnd_data.get_ability_score_full_names(),  # ['Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma']
            "spells": dnd_data.get_spell_list(),
            "backgrounds": dnd_data.get_background_list(),
            "attribute_range": "3-18 per ability (STR, DEX, CON, INT, WIS, CHA)",
            "skill_limit": "2-3 starting skills",
        }

        # Add hex info if in world mode
        if not getattr(self.world_controller, 'dungeon_mode', False):
            party_pos = self.world_controller.campaign_state.party_position
            hex = self.world_controller.campaign_state.get_hex(*party_pos)
            if hex:
                pois = self.world_controller.campaign_state.get_or_generate_pois(hex)
                discovered_pois = [p for p in pois if p.get('discovered', False)]
                available = self.world_controller.get_available_hex_moves(*party_pos)
                context["current_hex"] = {
                    "terrain": hex['terrain'],
                    "explored": hex.get('explored', False),
                    "discovered_pois": discovered_pois,
                    "available_moves": [{"direction": d, "terrain": t['terrain']} for d, t in available]
                }
        # Add character info if present
        if character:
            # Add character-specific info
            context["character"] = {
                "name": character.name,
                "race": character.race,
                "class": character.classs.name if character.classs else "Unknown",
                "level": character.level,
                "attributes": dict(character.abilities),
                "skills": list(character.skills.keys()),
                "spells": character.spells_known,
                "hp": f"{character.hp}/{character.max_hp}",
                "sp": f"{character.sp}/{character.max_sp}",
                "defense": character.defense,
            }
        return context

    def _extract_message_topic(self, message: str, game_context: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Use AI to determine the topic of the player's message.
        Returns a dict with 'type' and 'value' (e.g., {'type': 'race', 'value': 'Elf'}).
        If no clear topic, returns None.
        """
        prompt = f"""You are a topic extractor for an OG System game.
Given a player message, identify if they are asking about a specific race, class, skill, attribute, background, or spell.
Use only the following valid options from the OG System:

Races: {', '.join(game_context['races'])}
Classes: {', '.join(game_context['classes'])}
Skills: {', '.join(game_context['skills'])}
Attributes: {', '.join(game_context['attributes'])}
Backgrounds: {', '.join(game_context['backgrounds'])}
Spells: {', '.join(game_context['spells'][:20])}... (and more)

If the message asks about something not in these lists, or is a general question, return {{"type": "general", "value": null}}.

Player message: "{message}"

Respond with a JSON object containing "type" and "value". Examples:
- For "Tell me about elves" -> {{"type": "race", "value": "Elf"}}
- For "What does Brawn do?" -> {{"type": "attribute", "value": "Brawn"}}
- For "How do I become a mage?" -> {{"type": "class", "value": "Mage"}}
- For "What skills can I choose?" -> {{"type": "general", "value": null}}
"""
        # Use the same AI function as main responses, but with a specific prompt
        # We'll parse the JSON from the AI.
        try:
            data = self.world_controller.chat_ai.json_response(prompt)
            if "type" in data and "value" in data:
                return data
        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
        return None

    def _answer_with_interest(self, topic_type: str, topic_value: str, game_context: Dict[str, Any]) -> str:
        """
        Generate a detailed, engaging answer about a specific topic using AI.
        """
        prompt = f"""You are the Dungeon Master in a tabletop RPG.
The player is asking about {topic_type}: {topic_value}.

Answer them conversationally, in-character. 
Keep it brief (2-3 sentences maximum). Do not use markdown, bullet points, bold text, or emojis. Do not say "Let me guide you" or "Your GM". You are the DM speaking directly to the player.

Here is the actual game data for this topic:
Races: {', '.join(game_context['races'])}
Classes: {', '.join(game_context['classes'])}
Attributes: {', '.join(game_context['attributes'])}

Explain what this {topic_type} is, how it works in this world, and maybe give one short example. Keep the tone friendly and immersive, as if you're a wise mentor.

Your answer:
"""
        try:
            # Direct call to ChatAI
            data = self.world_controller.chat_ai.json_response(prompt)
            return data.get("narrative", "I'm not sure about that, but I'll find out.")
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"I can tell you about {topic_value}, but I need a moment to think."

    def _update_character_from_ai(self, character: Character, updates: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Apply AI-suggested updates to a character, validating against OG rules.
        Returns (success, list of error messages).
        """
        errors = []
        for field, value in updates.items():
            if field == "race":
                if dnd_data.validate_race(value):
                    character.race = value
                else:
                    errors.append(f"Invalid race: {value}")
            elif field == "class":
                if dnd_data.validate_class(value):
                    character.classs = dnd_data.OGClass.get(value)
                else:
                    errors.append(f"Invalid class: {value}")
            elif field == "background":
                if value in dnd_data.get_background_list():
                    character.background = value
                else:
                    errors.append(f"Invalid background: {value}")
            elif isinstance(field, str) and field.lower() in ABILITY_ALIASES:
                abil = ABILITY_ALIASES[field.lower()]
                try:
                    val = int(value)
                except (ValueError, TypeError):
                    errors.append(f"{abil} must be a number")
                    continue
                if ABILITY_MIN <= val <= ABILITY_MAX:
                    if not hasattr(character, "abilities") or character.abilities is None:
                        character.abilities = {}
                    character.abilities[abil] = val
                    # Recalculate derived stats after ability change
                    character.max_hp = character._calculate_max_hp()
                    character.max_sp = character._calculate_max_sp()
                    character.hp = min(character.hp, character.max_hp)
                    character.sp = min(character.sp, character.max_sp)
                    if hasattr(character, "_calculate_defense"):
                        character.defense = character._calculate_defense()
                    else:
                        dex_mod = (character.abilities.get("DEX", 10) - 10) // 2
                        character.base_defense = 10 + dex_mod
                        character.defense = character.base_defense + (2 if getattr(character, "shield", False) else 0)
                else:
                    errors.append(f"{abil} must be {ABILITY_MIN}-{ABILITY_MAX}")
            elif field == "skills":
                if isinstance(value, list):
                    # Replace all skills
                    for skill in value:
                        if not dnd_data.validate_skill(skill):
                            errors.append(f"Invalid skill: {skill}")
                            break
                    else:
                        character.skills = {skill: 1 for skill in value}
                else:
                    errors.append("Skills must be a list")
            elif field == "spells":
                if isinstance(value, list):
                    for spell in value:
                        if not dnd_data.validate_spell(spell):
                            errors.append(f"Invalid spell: {spell}")
                            break
                    else:
                        character.spells_known = value
                else:
                    errors.append("Spells must be a list")
            else:
                errors.append(f"Unknown field: {field}")
        return len(errors) == 0, errors

    def _format_context(self, ctx: dict) -> str:
        visible = ctx.get("visible_entities", [])
        env = ctx.get("environment", {})
        events = ctx.get("salient_events", [])
        effects = ctx.get("escalation_context", [])

        # Lighting description
        lighting_val = env.get("lighting", 1.0)
        if lighting_val >= 0.8:
            lighting_desc = "well lit"
        elif lighting_val >= 0.3:
            lighting_desc = "dim"
        else:
            lighting_desc = "dark"

        # Entities with type annotation
        if visible:
            names = []
            for e in visible:
                name = e.get('name', e.get('id', 'Unknown'))
                etype = e.get('type', '')
                desc = f"{name} ({etype})" if etype else name
                names.append(desc)
            visible_str = ", ".join(names)
        else:
            visible_str = "None"

        # Structured environment
        env_str = (
            f"Location: {env.get('location', 'Unknown')}, "
            f"Terrain: {env.get('terrain', 'unknown')}, "
            f"Lighting: {lighting_desc}, "
            f"Weather: {env.get('weather', 'unknown')}"
        )

        # Generic event formatting (no domain‑specific hardcoding)
        event_strs = []
        for e in events[:5]:
            etype = e.get("type", "unknown")
            data = e.get("data", {})
            if data:
                event_strs.append(f"{etype} ({data})")
            else:
                event_strs.append(etype)
        events_str = ", ".join(event_strs) if event_strs else "None"

        # Escalation effects with data
        effects_strs = []
        for e in effects:
            etype = e.get("type", "unknown")
            data = e.get("data", {})
            if data:
                effects_strs.append(f"{etype} ({data})")
            else:
                effects_strs.append(etype)
        effects_str = ", ".join(effects_strs) if effects_strs else "None"

        return (
            f"Visible entities: {visible_str}\n"
            f"Environment: {env_str}\n"
            f"Recent events: {events_str}\n"
            f"Escalation effects: {effects_str}"
        )

    def handle_movement(self, direction: str, success: bool, new_hex=None, block_reason=None):
        """Generate a narrative for a movement attempt."""
        # Build context as usual (includes current hex, available moves, etc.)
        context = self._build_game_context(...)  # we need session and character, but for movement we can pass dummy
        # For now, we'll use a simple prompt
        if success:
            # Get description of new hex
            hex_desc = self._describe_hex(new_hex)
            prompt = f"The party moves {direction}. They arrive at: {hex_desc}. Describe the scene in an immersive way."
        else:
            prompt = f"The party tries to move {direction} but is blocked by {block_reason}. Describe what happens."
        # Use the AI to generate a response
        response = get_ai_response(prompt, None, context)  # simplified, we'll need proper session/context
        # Parse and return DialogResponse(s)
        return [DialogResponse(speaker="DM", content=response, dialog_type="narration")]

    def _describe_hex(self, hex):
        desc = f"A {hex['terrain']} hex."
        if hex.get('pois'):
            discovered = [p['name'] for p in hex['pois'] if p.get('discovered')]
            if discovered:
                desc += f" You see {', '.join(discovered)}."
        return desc

    def generate_movement_narrative(self, direction: str, success: bool, new_hex=None, block_reason=None):
        """Generate narrative for a movement attempt using AI."""
        # Build minimal context (no session/character needed)
        context = {
            "current_hex": self.world_controller.describe_current_hex(),
            "available_moves": self.world_controller.get_available_hex_moves(*self.world_controller.campaign_state.party_position),
            # add any other relevant data
        }
        if success:
            # new_hex is a dict
            prompt = f"The party moves {direction} and arrives at a {new_hex['terrain']} hex. "
            # Add discovered POIs if any
            pois = [p for p in new_hex.get('pois', []) if p.get('discovered')]
            if pois:
                prompt += f"They see {', '.join(p['name'] for p in pois)}. "
            prompt += "Describe the scene in an immersive, vivid way."
        else:
            prompt = f"The party tries to move {direction} but is blocked by {block_reason}. Describe what happens."
        
        # Use the AI to generate a response
        narrative = self.world_controller.chat_ai.json_response(prompt, None, context)  # adjust parameters as needed
        # Return a list of DialogResponse objects (for consistency)
        return [DialogResponse(speaker="DM", content=narrative, dialog_type="narration")]
    
    def _is_creation_intent(self, message: str) -> bool:
        """
        Semantic creation intent check. Purely LLM-driven. 
        If the LLM is unavailable, we fail gracefully and let the caller fall back to pre-game chat.
        """
        prompt = f"""Analyze the following message from a player in a tabletop RPG.
Message: "{message}"

Is the player explicitly ready to START the character creation process right now, or are they just asking questions/discussing it?
If they are asking questions about classes, races, or how creation works, return false. Only return true if they are committing to the process.
Respond with a JSON object containing a single boolean key "is_creation".
Examples:
- "Let's make a new character" -> {{"is_creation": true}}
- "I want to roll up a rogue" -> {{"is_creation": true}}
- "Start character creation" -> {{"is_creation": true}}
- "I have questions about character creation" -> {{"is_creation": false}}
- "What classes are available?" -> {{"is_creation": false}}
- "Hello there" -> {{"is_creation": false}}
"""
        try:
            data = self.world_controller.chat_ai.json_response(prompt)
            if isinstance(data, dict) and "is_creation" in data:
                return bool(data["is_creation"])
            logger.warning(f"_is_creation_intent got non-dict response: {data!r}")
            return False
        except Exception as e:
            logger.error(f"Semantic creation intent check failed: {e}")
            return False

    def process_message(self, session_id: str, message: str, character_id: Optional[str] = None, encounter: Optional[Dict] = None) -> Dict[str, Any]:
        import copy
        print("[DEBUG] dm_chat_handler.process_message called")

        # --- Setup ---
        session = self.world_controller.session_manager.get_or_create_session(session_id)
        player_id = session.player_id
        if not player_id:
            raise Exception(f"Session missing player_id: {session_id}")

        player = self.world_controller.get_player_by_id(player_id)
        if player is None:
            player = self.world_controller.players.get(player_id)
        if player is None:
            return {"error": "player_not_loaded"}

        # --- FSM (combat/dialogue) takes priority ---
        fsm = self.adjudication_engine.active_fsms.get(session_id)
        if fsm:
            fsm_result = fsm.handle_input(message, session_id)
            return {
                "responses": [DialogResponse(speaker="DM", content=fsm_result.get("message", ""), dialog_type="narration")],
                "map_data": fsm_result.get("map_data"),
                "action": fsm_result.get("action")
            }

        self.world_controller.session_manager.add_message(session_id, "Player", message)

        # --- Load character ---
        character = None
        if character_id:
            character = self.world_controller.character_manager.get_character(character_id)
        elif session.active_character_id:
            character = self.world_controller.character_manager.get_character(session.active_character_id)

        game_context = self._build_game_context(session, character)
        if encounter:
            game_context["encounter"] = encounter
            game_context["encounter_description"] = encounter.get("description", "")

        # --- 1. Rules/Lore (works in every phase) ---
        if self._is_rules_question(message):
            topic = self._extract_message_topic(message, game_context)
            if topic and topic["type"] != "general":
                answer = self._answer_with_interest(topic["type"], topic["value"], game_context)
                self.world_controller.session_manager.add_message(session_id, "DM", answer)
                return {"responses": [DialogResponse(speaker="DM", content=answer, dialog_type="narration")], "tool_result": None}

        # --- 2. Pre-Game (creation or chat) ---
        creation_state = getattr(session, 'creation_state', None)
        is_pre_game = (not character) or (creation_state is not None)

        if is_pre_game:
            # 2a. Character creation (in progress OR just triggered)
            is_creating = (creation_state is not None) or self._is_creation_intent(message)

            if is_creating:
                ns = getattr(self.world_controller, 'narrative_system', None)
                final_char = None
                if ns:
                    if creation_state is None:
                        creation_state = copy.deepcopy(DEFAULT_DRAFT)

                    world_context = {}
                    try:
                        ws = self.world_controller.campaign_state
                        if hasattr(ws, "world_map") and hasattr(ws.world_map, "locations"):
                            world_context["locations"] = [loc.name for loc in list(ws.world_map.locations.values())[:15]]
                        if hasattr(ws, "factions"):
                            world_context["factions"] = [f.name for f in list(ws.factions.values())[:10]]
                    except Exception:
                        pass

                    agent = CharacterAgent(self.world_controller.chat_ai, world_context=world_context)
                    updated_draft, dm_text, ready_to_build = agent.process_turn(message, creation_state)
                    session.creation_state = updated_draft

                    resp_objs = [DialogResponse(speaker="DM", content=dm_text, dialog_type="narration")]

                    if ready_to_build:
                        try:
                            final_char = ns._finalize_character(updated_draft, owner_id=player_id)
                            session.creation_state = None
                            session.equip_draft = copy.deepcopy(DEFAULT_EQUIP_DRAFT)
                            resp_objs = [DialogResponse(
                                speaker="DM",
                                content=f"Behold {final_char.name}, the {final_char.race} {final_char.classs.name}! Let's get your starting equipment sorted.",
                                dialog_type="narration"
                            )]
                        except Exception as e:
                            logger.error(f"Finalization failed: {e}")
                            resp_objs.append(DialogResponse(
                                speaker="DM",
                                content=f"I couldn't finish building the character: {e}",
                                dialog_type="error"
                            ))

                    return {   # <--- THE MISSING RETURN
                        "responses": resp_objs,
                        "action": "create_character",
                        "map_data": None
                    }

            # 2c. Equipment selection (equip_draft is set but not yet complete)
            equip_draft = getattr(session, 'equip_draft', None)
            if equip_draft is not None and final_char is not None:
                equip_agent = EquipAgent(self.world_controller.chat_ai)
                updated_draft, dm_text, is_complete = equip_agent.process_turn(message, final_char, equip_draft)
                session.equip_draft = updated_draft

                if is_complete:
                    # Apply equipment to character using InventoryItem objects
                    from world.character import InventoryItem
                    weapon_name = updated_draft.get("weapon")
                    armor_name = updated_draft.get("armor")
                    pack_name = updated_draft.get("pack")

                    if weapon_name:
                        item = InventoryItem(name=weapon_name, description=f"Equipped weapon: {weapon_name}", slot="weapon", equipped=True)
                        final_char.inventory.append(item)
                        final_char.weapons.append(item)
                        final_char.equipped_gear["weapon"] = item

                    if armor_name:
                        item = InventoryItem(name=armor_name, description=f"Equipped armor: {armor_name}", slot="armor", equipped=True)
                        final_char.inventory.append(item)
                        final_char.equipped_gear["armor"] = item
                        final_char.armor = item
                        lname = armor_name.lower()
                        if lname in ("mail", "leather", "robes") or "armor" in lname:
                            final_char._update_armor_stats(lname)

                    # Apply pack items (adventuring gear like rations, waterskin, bedroll, torches)
                    if pack_name:
                        _apply_pack_items(pack_name, final_char)

                    session.equip_draft = None
                    # Fall through to in-game flow below
                else:
                    self.world_controller.session_manager.add_message(session_id, "DM", dm_text)
                    return {
                        "responses": [DialogResponse(speaker="DM", content=dm_text, dialog_type="narration")],
                        "action": "equip_character",
                        "map_data": None
                    }

            # 2d. Pre-game chat (no character, not creating)
            try:
                prompt = f"""You are the Dungeon Master. The player does not have an active character yet.
The player says: "{message}"

Respond warmly. If they asked a question, answer it. Then gently remind them that they can create a character whenever they're ready.
"""
                ai_resp = self.world_controller.chat_ai.json_response(prompt)
                dm_text = None
                if isinstance(ai_resp, dict):
                    dm_text = ai_resp.get("narrative") or ai_resp.get("message") or ai_resp.get("response")
                if not dm_text:
                    dm_text = "You don't have a character yet. Whenever you're ready, say 'I want to make a character' and we'll begin."
            except Exception as e:
                logger.error(f"Pre-game chat failed: {e}")
                dm_text = "You don't have a character yet. Whenever you're ready, say 'I want to make a character' and we'll begin."

            self.world_controller.session_manager.add_message(session_id, "DM", dm_text)
            return {
                "responses": [DialogResponse(speaker="DM", content=dm_text, dialog_type="narration")],
                "action": "pre_game_chat",
                "map_data": None
            }

        # --- 3. In-Game: movement + parser + adjudication ---
        movement_map = {
            "north": "north", "south": "south", "east": "east", "west": "west",
            "northeast": "northeast", "northwest": "northwest", "southeast": "southeast", "southwest": "southwest",
            "n": "north", "s": "south", "e": "east", "w": "west",
            "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest"
        }
        prefixes = ["go ", "head ", "walk ", "travel ", "climb ", "swim ", "sail ", "roll ", "slide ", "move ", "run ", "crawl ", "creep ", "march "]
        cmd = message.lower().strip()
        for prefix in prefixes:
            if cmd.startswith(prefix):
                cmd = cmd[len(prefix):].strip()
                break

        if cmd in movement_map:
            direction = movement_map[cmd]
            frame = IntentFrame(action=f"move {direction}", category="movement", destination=direction)
            result = self.adjudication_engine.process(frame, session_id)
            if result is None:
                result = {"success": False, "message": "Movement failed.", "action": None}
            return {
                "responses": [DialogResponse(speaker="DM", content=result.get("message", ""), dialog_type="narration")],
                "map_data": result.get("map_data"),
                "action": result.get("action")
            }

        parser = IntentParser(self.world_controller.chat_ai)
        conversation_context = self.world_controller.session_manager.get_conversation_context(session_id)
        frame = parser.parse(message, game_context, conversation_context)
        print(f"[DEBUG] Parsed frame: action={frame.action}, target={frame.target}, item={frame.item}")
        if frame.category is None:
            frame.category = "other"

        if frame.clarification_needed:
            return {
                "responses": [DialogResponse(
                    speaker="DM",
                    content=f"I need clarification: {', '.join(frame.missing_fields)}. Can you rephrase?",
                    dialog_type="question"
                )],
                "clarification": True
            }

        result = self.adjudication_engine.process(frame, session_id)
        base_message = result.get("message", "")

        import re
        if hasattr(base_message, "content"):
            base_message = base_message.content
        if isinstance(base_message, str) and base_message.startswith("DialogResponse("):
            match = re.search(r"content=['\"](.*?)['\"],?\s*(?:dialog_type|timestamp|$)", base_message, re.DOTALL)
            if match:
                base_message = match.group(1)

        unified_context = self.adjudication_engine.context_builder.build(session_id)
        salient_events = unified_context.get("salient_events", [])
        context_str = self._format_context(unified_context)

        if not self.should_invoke_ai(result):
            return {
                "responses": [DialogResponse(speaker="DM", content=base_message, dialog_type="narration")],
                "map_data": result.get("map_data"),
                "action": result.get("action"),
                "salient_events": salient_events
            }

        dm_prompt = f"""
You are the Dungeon Master.

Current situation:
{context_str}

Base action result:
{base_message}

Return ONLY valid JSON:
{{"narrative": "..."}}
"""
        ai_response = self.world_controller.chat_ai.json_response(dm_prompt)
        final_text = base_message
        if isinstance(ai_response, dict) and "narrative" in ai_response:
            final_text = ai_response["narrative"]

        if hasattr(final_text, "content"):
            final_text = final_text.content
        if isinstance(final_text, str) and final_text.startswith("DialogResponse("):
            match = re.search(r"content=['\"](.*?)['\"],?\s*(?:dialog_type|timestamp|$)", final_text, re.DOTALL)
            if match:
                final_text = match.group(1)
        if not isinstance(final_text, str):
            final_text = str(final_text)

        return {
            "responses": [DialogResponse(speaker="DM", content=final_text, dialog_type="narration")],
            "map_data": result.get("map_data"),
            "action": result.get("action"),
            "salient_events": salient_events
        } 
           
    def handle_confirmation(self, session_id: str, confirmed: bool) -> Dict[str, Any]:
        """Handle player's response to a confirmation request."""

        session = self.world_controller.session_manager.get_session(session_id)

        if not session or not session.pending_confirmation:
            return {
                "responses": [
                    DialogResponse(
                        speaker="DM",
                        content="Nothing to confirm.",
                        dialog_type="narration"
                    )
                ]
            }

        if confirmed:
            updates = session.pending_confirmation

            session.character_data.update(updates)
            session.pending_confirmation = None

            return {
                "responses": [
                    DialogResponse(
                        speaker="DM",
                        content="Confirmed. Changes applied.",
                        dialog_type="narration"
                    )
                ]
            }

        session.pending_confirmation = None

        return {
            "responses": [
                DialogResponse(
                    speaker="DM",
                    content="Confirmation cancelled.",
                    dialog_type="narration"
                )
            ]
        }

    # helper
    def _is_rules_question(self, message: str) -> bool:
        """
        Fast deterministic check: is this message asking about game rules/lore?
        Returns True if it's likely a rules question, False otherwise.
        """
        from world import dnd_data

        msg = message.lower().strip()

        # 1. Must be a question or ask for explanation
        question_markers = ["?", "what is", "how do", "tell me about", "explain", "can i", "how does", "what are", "why would"]
        is_question = any(msg.startswith(marker) or f" {marker}" in msg for marker in question_markers) or "?" in msg
        if not is_question:
            return False

        def _has_word_boundary(needle: str, haystack: str) -> bool:
            """True iff `needle` appears in `haystack` not surrounded by letters."""
            if not needle:
                return False
            pattern = rf"(?<![A-Za-z]){re.escape(needle.lower())}(?![A-Za-z])"
            return re.search(pattern, haystack) is not None

        # 2. Known rule topics (from dnd_data)
        rule_topics = (
            dnd_data.get_race_list()
            + dnd_data.get_class_list()
            + dnd_data.get_skill_list()
            + dnd_data.get_background_list()
            + dnd_data.get_spell_list()
            + dnd_data.get_ability_score_full_names()
        )

        # 3. Whole-word match against known topics
        for topic in rule_topics:
            if _has_word_boundary(topic, msg):
                return True

        # 4. Additional explicit rule terms
        extra_terms = ["ability score", "attribute", "race", "class", "background", "skill", "spell", "level", "feat", "trait"]
        for term in extra_terms:
            if _has_word_boundary(term, msg):
                return True

        return False