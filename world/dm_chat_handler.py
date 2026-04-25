# dm_chat_handler.py – OG System version with AI topic extraction

import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from world import dnd_data
from world.character import Character
from world.intent_mapper import IntentMapper
from world.action_system import ActionPlanner, ActionQueue
from world.resolver import ResolverLoop
from world.intent import IntentFrame
from world.intent_manager import IntentManager
from world.adjudication_engine import AdjudicationEngine

logger = logging.getLogger(__name__)

@dataclass
class DialogResponse:
    """A single response in a dialog turn."""
    speaker: str  # 'DM' or 'Player'
    content: str
    dialog_type: str  # 'narration', 'question', 'suggestion', etc.

@dataclass
class SessionState:
    """Tracks a player's session state."""
    session_id: str
    player_name: str
    created_at: datetime
    last_active: datetime
    character_data: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    active_character_id: Optional[str] = None
    pending_confirmation: Optional[Dict[str, Any]] = None

class DMChatHandler:
    """
    Handles DM chat interactions, character creation, and game progression.
    Uses OG System data and AI for topic extraction and responses.
    """

    def __init__(self, world_controller):
        self.world_controller = world_controller
        self.sessions: Dict[str, SessionState] = {}
        self.intent_manager = IntentManager()
        self.adjudication_engine = AdjudicationEngine(world_controller)

    def create_session(self, session_id: str, player_name: str, initial_data: Dict = None) -> SessionState:
        """Create a new player session."""
        session = SessionState(
            session_id=session_id,
            player_name=player_name,
            created_at=datetime.now(),
            last_active=datetime.now(),
            character_data=initial_data or {},
            conversation_history=[]
        )
        self.sessions[session_id] = session
        return session

    def get_or_create_session(self, session_id: str, player_name: str = "Player") -> SessionState:
        """Retrieve existing session or create a new one."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.last_active = datetime.now()
            return session
        return self.create_session(session_id, player_name)

    def _build_game_context(self, session: SessionState, character: Optional[Character] = None) -> Dict[str, Any]:
        """
        Build a context dictionary of OG System data for the AI prompt.
        Includes lists of races, classes, skills, attributes, spells, etc.
        """
        context = {
            "classes": dnd_data.get_class_list(),
            "races": dnd_data.get_race_list(),
            "skills": dnd_data.get_skill_list(),
            "attributes": dnd_data.get_ability_score_full_names(),  # ['Brawn', 'Finesse', 'Wits', 'Will']
            "spells": dnd_data.get_spell_list(),
            "backgrounds": dnd_data.get_background_list(),
            "attribute_range": "0-4, total 4 points, max 3 per attribute",
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
                "attributes": {
                    "brawn": character.brawn,
                    "finesse": character.finesse,
                    "wits": character.wits,
                    "will": character.will,
                },
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
        prompt = f"""You are a knowledgeable guide for the OG System game.
The player is asking about {topic_type}: {topic_value}.
Provide an interesting, helpful, and immersive answer that fits the OG System rules.
Use the following data for reference:

Races: {', '.join(game_context['races'])}
Classes: {', '.join(game_context['classes'])}
Skills: {', '.join(game_context['skills'])}
Attributes: {', '.join(game_context['attributes'])}
Backgrounds: {', '.join(game_context['backgrounds'])}
Spells: {', '.join(game_context['spells'][:10])}... (and more)

Explain what this {topic_type} is, how it works in the game, and maybe give an example or suggestion.
Keep the tone friendly and immersive, as if you're a wise mentor.

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
            elif field in ("brawn", "finesse", "wits", "will"):
                try:
                    val = int(value)
                    if 0 <= val <= 4:
                        setattr(character, field, val)
                        # Recalculate derived stats after attribute change
                        character.max_hp = character._calculate_max_hp()
                        character.max_sp = character._calculate_max_sp()
                        character.hp = min(character.hp, character.max_hp)
                        character.sp = min(character.sp, character.max_sp)
                        character.base_defense = 10 + character.finesse
                        character.defense = character.base_defense + (2 if character.shield else 0)
                    else:
                        errors.append(f"{field} must be 0-4")
                except ValueError:
                    errors.append(f"{field} must be a number")
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
        return [{"speaker": "DM", "content": narrative, "dialog_type": "narration"}]

    def process_message(self, session_id: str, message: str, character_id: Optional[str] = None, encounter: Optional[Dict] = None) -> Dict[str, Any]:
        print("[DEBUG] dm_chat_handler.process_message called")
        session = self.get_or_create_session(session_id, "Player")
        session.conversation_history.append({"role": "user", "content": message})

        # ------------------------------------------------------------------
        # 1. DETERMINISTIC MOVEMENT PRE‑PROCESSOR
        # ------------------------------------------------------------------
        movement_map = {
            "north": "north", "south": "south", "east": "east", "west": "west",
            "northeast": "northeast", "northwest": "northwest",
            "southeast": "southeast", "southwest": "southwest",
            "n": "north", "s": "south", "e": "east", "w": "west",
            "ne": "northeast", "nw": "northwest", "se": "southeast", "sw": "southwest"
        }
        cmd = message.lower().strip()
        prefixes = [
            "go ", "head ", "walk ", "travel ", "climb ", "swim ", "sail ",
            "roll ", "slide ", "move ", "run ", "crawl ", "creep ", "march "
        ]
        for prefix in prefixes:
            if cmd.startswith(prefix):
                cmd = cmd[len(prefix):].strip()
                break
        if cmd in movement_map:
            direction = movement_map[cmd]
            frame = IntentFrame(action=f"move {direction}", category="movement", destination=direction)
            engine = AdjudicationEngine(self.world_controller)
            result = engine.process(frame, session_id)
            return {
                "responses": [DialogResponse(speaker="DM", content=result.get("message", ""), dialog_type="narration")],
                "map_data": result.get("map_data"),
                "action": result.get("action")
            }

        # ------------------------------------------------------------------
        # 2. GET ACTIVE CHARACTER & GAME CONTEXT
        # ------------------------------------------------------------------
        character = None
        if character_id:
            character = self.world_controller.character_manager.get_character(character_id)
        elif session.active_character_id:
            character = self.world_controller.character_manager.get_character(session.active_character_id)

        game_context = self._build_game_context(session, character)
        if encounter:
            game_context["encounter"] = encounter
            game_context["encounter_description"] = encounter.get("description", "")

        # ------------------------------------------------------------------
        # 3. RULES / LORE QUESTIONS (bypass everything)
        # ------------------------------------------------------------------
        topic = self._extract_message_topic(message, game_context)
        if topic and topic["type"] != "general":
            answer = self._answer_with_interest(topic["type"], topic["value"], game_context)
            responses = [DialogResponse(speaker="DM", content=answer, dialog_type="narration")]
            session.conversation_history.append({"role": "assistant", "content": answer})
            return {"responses": responses, "tool_result": None}

        # ------------------------------------------------------------------
        # 4. CLASSIFIER FIRST (embedding)
        # ------------------------------------------------------------------
        from world.intent_manager import IntentManager
        classifier = IntentManager()
        intent_name, confidence, emb_slots = classifier.classify(message)

        intent_to_action = {
            "acquire_goods": "buy",
            "dispose_goods": "sell",
            "relocate_self": "move",
            "survey_entity": "look",
            "survey_environment": "look",
            "negotiate_price": "haggle"
        }
        intent_to_category = {
            "acquire_goods": "economy",
            "dispose_goods": "economy",
            "negotiate_price": "economy",
            "relocate_self": "movement",
            "survey_entity": "exploration",
            "survey_environment": "exploration"
        }

        # Build frame from classifier
        action = intent_to_action.get(intent_name, "narrate")
        category = intent_to_category.get(intent_name, "other")
        frame = IntentFrame(
            action=action,
            category=category,
            target=emb_slots.get("target"),
            item=emb_slots.get("obj"),
            destination=emb_slots.get("destination"),
            price=emb_slots.get("currency"),
            raw_text=message
        )

        # ------------------------------------------------------------------
        # 5. AI VALIDATION (only for low confidence)
        # ------------------------------------------------------------------
        if confidence < 0.7 or intent_name == "clarification_needed" or category == "other":
            correction_prompt = f"""The system (using a similarity classifier) suggests the player wants to {action} with:
- category: {category}
- target: {frame.target}
- item: {frame.item}
- destination: {frame.destination}
- price: {frame.price}

Player message: "{message}"

If this is correct, output {{"ok": true}}.
If incorrect, output a corrected JSON with the same fields (action, category, target, item, destination, price). Use null for missing.
Output only JSON, no extra text."""
            ai_data = self.world_controller.chat_ai.json_response(correction_prompt)
            if ai_data.get("ok") != True:
                frame.action = ai_data.get("action", frame.action)
                frame.category = ai_data.get("category", frame.category)
                frame.target = ai_data.get("target", frame.target)
                frame.item = ai_data.get("item", frame.item)
                frame.destination = ai_data.get("destination", frame.destination)
                frame.price = ai_data.get("price", frame.price)

        # ------------------------------------------------------------------
        # 6. DEBUG PRINT
        # ------------------------------------------------------------------
        print(f"[DEBUG] Final IntentFrame: action={frame.action}, category={frame.category}, target={frame.target}, item={frame.item}, price={frame.price}")

        # ------------------------------------------------------------------
        # 7. ADJUDICATION ENGINE
        # ------------------------------------------------------------------
        engine = AdjudicationEngine(self.world_controller)
        result = engine.process(frame, session_id)
        if result.get("clarification"):
            return {
                "responses": [DialogResponse(speaker="DM", content=result["message"], dialog_type="narration")],
                "clarification": True
            }
        else:
            return {
                "responses": [DialogResponse(speaker="DM", content=result.get("message", ""), dialog_type="narration")],
                "map_data": result.get("map_data"),
                "action": result.get("action")
            }
           
    def handle_confirmation(self, session_id: str, confirmed: bool) -> Dict[str, Any]:
        """Handle player's response to a confirmation request."""
        session = self.sessions.get(session_id)
        if not session or not session.pending_confirmation:
            return {"responses": [DialogResponse(speaker="DM", content="Nothing to confirm.", dialog_type="narration")]}

        if confirmed:
            updates = session.pending_confirmation
            # Apply updates (similar logic as above)
            # For simplicity, we'd need a character reference; we'll assume a character exists or we're in creation.
            # This is a placeholder – you may extend as needed.
            session.character_data.update(updates)
            session.pending_confirmation = None
            return {"responses": [DialogResponse(speaker="DM", content="Confirmed. Changes applied.", dialog_type="narration")]}
        else:
            session.pending_confirmation = None
            return {"responses": [DialogResponse(speaker="DM", content="Confirmation cancelled.", dialog_type="narration")]}