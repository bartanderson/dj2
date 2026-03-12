# world/dm_chat_handler.py
# coding=utf-8
import re
import random
import logging
import difflib
import traceback
from typing import Dict, List, Optional, Tuple
from world.ai_dungeon_master import Dialog  # Ensure Dialog is imported
from world.session_system import SessionState
from world import dnd_data

logger = logging.getLogger(__name__)

class DMChatHandler:
    """
    PHASE_MIGRATION_IN_PROGRESS: This class is being migrated from monolithic phase mixing
    to phase-compliant architecture.
    
    Current violations being addressed:
    1. AI boundary compliance → Use DMChatAI system
    2. Direct state mutation → Use SessionSystem (NOW COMPLIANT ✅)
    3. Direct tool execution → TODO: Use AuthoritySystem (NOW COMPLIANT ✅)
    """

    def __init__(self, world_controller):
        self.world_controller = world_controller
        self.dm = world_controller.dungeon_master  # Will be replaced by ConsequenceEngine in step 4
        self.consequence_engine = world_controller.consequence_engine   # new

    def _update_conversation_topics(self, session_id: str, message: str, is_dm_response: bool = False):
        """Extract and update recent topics from messages"""
        if hasattr(self.world_controller, 'session_system') and self.world_controller.session_system:
            topic = self._extract_message_topic(message)
            if topic:
                self.world_controller.session_system.add_topic(session_id, topic)

    def _extract_message_topic(self, message):
        """Use AI to extract the main topic from a single message"""
        prompt = f"""
        Extract the primary topic or subject from this message. Return only the topic phrase, not a complete sentence.
        
        Message: "{message}"
        
        Examples:
        - "I want to create a magic user" → "magic character creation"
        - "Tell me about stealth classes" → "stealth classes" 
        - "What's the best race for a wizard?" → "wizard race selection"
        - "Can you summarize what we discussed?" → "conversation summary request"
        
        Topic:
        """
        try:
            topic = self.world_controller.world_ai.generate_text(prompt)
            return topic.strip().lower()
        except Exception as e:
            print(f"AI topic extraction failed: {e}")
            return None

    def _generate_resume_prompt(self, session_id: str) -> str:
        """Generate a prompt to resume character creation."""
        session = self.world_controller.session_system.get_session(session_id)
        if not session:
            return "Let's start creating your character. Tell me about the kind of adventurer you'd like to play."
        
        context = session.get_creation_context()
        prompt = f"""
        The player was in the middle of creating a character. Here's what we have so far:
        {context}
        
        Generate a friendly, concise message that:
        1. Summarizes what we've discussed (the key details already provided).
        2. Asks if they want to continue or start over.
        
        Keep it conversational and encouraging.
        """
        try:
            return self.world_controller.ai_system.generate_text(prompt)
        except Exception as e:
            print(f"Resume prompt generation failed: {e}")
            # Fallback
            details = ", ".join([f"{k}: {v}" for k, v in session.character_data.items() if v])
            return f"Welcome back! You were creating a character with these details: {details}. Would you like to continue or start over?"

    def _ensure_creation_state(self, session_id: str, session) -> 'SessionState':
        """If creation_state is not_started, set to gathering_info and return updated session."""
        if session.creation_state == "not_started":
            self.world_controller.session_system.set_creation_state(session_id, "gathering_info")
            return self.world_controller.session_system.get_session(session_id)
        return session

    def _process_creation_step(self, message: str, session_id: str) -> Dict:
        session = self.world_controller.session_system.get_session(session_id)
        if not session:
            return {"narrative": [Dialog("DM", "Session error. Please start over.", "system")]}

        # Build session state for AI
        session_state = {
            "character_data": session.character_data,
            "creation_state": session.creation_state,
            "awaiting_confirmation": session.awaiting_confirmation,
            "pending_suggestion": session.pending_suggestion,
            "recent_topics": list(session.conversation_topics),
            "chat_history": session.chat_history[-5:]  # last few messages
        }

        # Get game data from dnd_data
        game_data = {
            "classes": dnd_data.get_class_list(),                     # e.g., ['Warrior', 'Mage', ...]
            "races": dnd_data.get_race_list(),                         # e.g., ['Human', 'Elf', ...]
            "skills": dnd_data.get_skill_list(),                       # e.g., ['Survival', 'Lore', ...]
            "attributes": dnd_data.get_ability_score_full_names(),     # ['Brawn', 'Finesse', 'Wits', 'Will']
            "spells": dnd_data.get_spell_list(),                       # list of spell effect names
            "backgrounds": dnd_data.get_background_list()              # existing hardcoded list
        }
        # Optionally include class-specific spells if needed
        if current_class:
            # If OG system has class-specific spell lists, add them here
            # For now, just include all spells
            pass

        # AI processes the turn
        ai_result = self.world_controller.dm_chat_ai.process_creation_turn(
            message, session_state, game_data
        )

        # If AI returned an error, just return the narrative (don't update state)
        if ai_result.get("error"):
            return {"narrative": [Dialog("DM", ai_result["narrative"], "dm")]}

        # Validate and apply updates
        updates = ai_result.get("updates", {})
        # Remove entries with None or empty string values (lists are kept even if empty)
        updates = {k: v for k, v in updates.items() if v is not None and v != ""}
        applied = []
        if updates:
            # Get current character data (before any changes)
            session = self.world_controller.session_system.get_session(session_id)
            current_data = session.character_data.copy()
            # Simulate the final state after applying all updates
            simulated_data = current_data.copy()
            simulated_data.update(updates)

            validation_errors = []
            validated_updates = {}
            for field, value in updates.items():
                if not value:
                    continue
                action = {
                    "action": "update_character_attribute",
                    "parameters": {"field": field, "value": value}
                }
                # Pass simulated_data as context (the state after all updates)
                validated = self.world_controller.authority_system.validate_creation_action(
                    action, {"character_data": simulated_data}
                )
                if validated.valid:
                    validated_updates[field] = value
                else:
                    validation_errors.append(f"{field}: {validated.message}")

            if validation_errors:
                # Log errors and inform the user
                error_msg = "I'm having trouble with some details: " + "; ".join(validation_errors) + " Could you rephrase?"
                print(f"DEBUG: AI proposed invalid updates: {validation_errors}")
                return {"narrative": [Dialog("DM", error_msg, "system")]}

            # All updates valid – apply them in batch
            for field, value in validated_updates.items():
                self.world_controller.session_system.update_character_data(session_id, {field: value})
                applied.append(field)
            # Refresh session after updates
            session = self.world_controller.session_system.get_session(session_id)

        # Apply state change if provided
        if ai_result.get("state_change"):
            self.world_controller.session_system.set_creation_state(session_id, ai_result["state_change"])

        # Set confirmation flag and pending suggestion if needed
        if ai_result.get("needs_confirmation"):
            self.world_controller.session_system.set_awaiting_confirmation(session_id, True)
            if ai_result.get("pending_suggestion"):
                self.world_controller.session_system.set_pending_suggestion(session_id, ai_result["pending_suggestion"])
        else:
            self.world_controller.session_system.set_awaiting_confirmation(session_id, False)
            self.world_controller.session_system.set_pending_suggestion(session_id, None)

        # --- FINALIZATION: If state became "completed", create the character ---
        if ai_result.get("state_change") == "completed":
            # Ensure we have the latest session data
            session = self.world_controller.session_system.get_session(session_id)
            char_data = session.character_data

            # Validate required fields (just in case the AI messed up)
            required = ["name", "race", "class"]
            missing = [f for f in required if not char_data.get(f)]
            if missing:
                # AI shouldn't set completed without these, but if it does, roll back
                error_msg = f"I'm missing some essential details: {', '.join(missing)}. Let's continue."
                self.world_controller.session_system.set_creation_state(session_id, "gathering_info")
                return {"narrative": [Dialog("DM", error_msg, "system")]}

            # Attempt to create the character
            try:
                character = self.world_controller.character_manager.create_character(
                    session.player_id,
                    char_data
                )
                # Assign character to player and set as active
                self.world_controller.character_manager.assign_character_to_player(
                    session.player_id, character.id
                )
                self.world_controller.session_system.set_active_character(session_id, character.id)

                # Clear creation state (optional)
                self.world_controller.session_system.set_creation_state(session_id, "completed")

                # Return success with character data
                return {
                    "narrative": [Dialog("DM", ai_result["narrative"], "dm")],
                    "character_data": char_data,
                    "character_id": character.id
                }
            except Exception as e:
                # Log error and tell user
                print(f"DEBUG: Character creation failed: {e}")
                error_msg = "Something went wrong creating your character. Let's try again."
                self.world_controller.session_system.set_creation_state(session_id, "gathering_info")
                return {"narrative": [Dialog("DM", error_msg, "system")]}

        # Return narrative
        return {"narrative": [Dialog("DM", ai_result["narrative"], "dm")]}

    def _answer_with_interest(self, message: str, session, interest: str = None) -> Dict:
        """Answer question informed by expressed interest."""
        import random
        
        text_lower = message.lower()
        
        # Get stored interest if not provided
        if not interest and session.character_data:
            interest = session.character_data.get('interested_in')
        
        # No interest stored—fall back to generic
        if not interest:
            answer = self._answer_exploratory_question(message, session)
            return {"narrative": [Dialog("DM", answer, "dm")]}
        
        # Detect what they're asking about
        asking_race = any(w in text_lower for w in ['race', 'racial', 'species', 'people', 'folk'])
        asking_class = any(w in text_lower for w in ['class', 'job', 'role', 'profession', 'career'])
        asking_background = any(w in text_lower for w in ['background', 'history', 'origin', 'past'])
        
        # Arcane interest
        if interest == 'arcane':
            if asking_race:
                answers = [
                    "For arcane magic—High Elves get +2 Int and a free cantrip, natural Wizards. Tieflings carry innate magic in their blood. Half-Elves flex between classes. But any race can master the arcane with study.",
                    "Elves and Tieflings have natural affinities, but Gnomes are clever tinkerers and Humans adapt to any magical discipline. What kind of arcanist—scholarly or instinctive?"
                ]
            elif asking_class:
                answers = [
                    "Wizard if you love preparation and vast spellbooks. Sorcerer if power burns in your blood and you want flexibility. Warlock if you made a deal for quick power. Eldritch Knight or Arcane Trickster if you want steel with your spells.",
                    "Wizards know the most spells. Sorcerers cast more freely. Warlocks recover quickly but know fewer tricks. Artificers build magic into objects. Which approach fits?"
                ]
            elif asking_background:
                answers = [
                    "Sage spent years in libraries. Hermit discovered secrets in isolation. Noble had tutors. Charlatan faked it until the magic became real. What led to your power?"
                ]
            else:
                answers = [
                    "Arcane magic—power through knowledge or bloodline. The weave responds to intellect and force of will.",
                    "Study or inheritance—arcane magic doesn't care which, only that you can grasp it."
                ]
        
        # Divine interest
        elif interest == 'divine':
            if asking_race:
                answers = [
                    "Dwarves make sturdy Clerics, their gods carved into mountain and forge. Half-Orcs surprise as Paladins—redemption through oaths. Aasimar are literally touched by divinity. But faith knows no race.",
                    "Dragonborn carry their gods' pride. Humans spread faith everywhere. What divine warrior calls to you?"
                ]
            elif asking_class:
                answers = [
                    "Cleric if you serve a god's full portfolio. Paladin if you swore an oath of devotion. Divine Soul Sorcerer if the gods touched your bloodline. Celestial Warlock if you made a pact with an angel.",
                    "Clerics heal and smite. Paladins avenge and protect. Both wear armor and stand in the front line. Do you want to preach or to embody?"
                ]
            elif asking_background:
                answers = [
                    "Acolte grew up in the temple. Soldier found faith in war. Folk Hero was touched by the divine for saving others. How did your god find you?"
                ]
            else:
                answers = [
                    "Divine magic—faith made manifest. Gods grant power, but oaths and devotion can too.",
                    "The gods listen. Some answer with power, others with purpose."
                ]
        
        # Primal interest
        elif interest == 'primal':
            if asking_race:
                answers = [
                    "Wood Elves and Forest Gnomes have natural affinities—born to the wild. Ghostwise Halflings speak to beasts silently. Firbolgs tower among trees. But any can hear nature's call if they listen.",
                    "Dwarves of the mountain caves, Humans of the vast plains—primal magic doesn't care where you came from, only that you respect the balance."
                ]
            elif asking_class:
                answers = [
                    "Druid if you want to become the beast and command nature. Ranger if you move through it, ally but separate. Some Barbarians tap primal rage. Where do you stand—within nature or beside it?",
                    "Druids shapechange and command elements. Rangers track and companion with beasts. Both know the wild. Do you want to be nature's voice or its guardian?"
                ]
            elif asking_background:
                answers = [
                    "Outlander lived in the wilds. Hermit spoke with spirits alone. Folk Hero saved a village from natural disaster. How did the wild claim you?"
                ]
            else:
                answers = [
                    "Primal magic—the speaking of the wild. Not command, but conversation with forces older than gods.",
                    "The spirits of land, beast, and weather. They lend power to those who respect their balance."
                ]
        
        # Unknown interest—shouldn't reach here
        else:
            answer = self._answer_exploratory_question(message, session)
            return {"narrative": [Dialog("DM", answer, "dm")]}
        
        # Return random selection from appropriate answers
        return {"narrative": [Dialog("DM", random.choice(answers), "dm")]}


    def _start_character_creation(self, session) -> str:
        """Welcome the player to character creation with an open invitation."""
        # If there's already partial data, offer to resume
        if session.character_data and any(v for v in session.character_data.values()):
            summary = ", ".join([f"{k}: {v}" for k, v in session.character_data.items() if v])
            return f"Welcome back! You've already told me: {summary}. Would you like to continue there, or start fresh?"
        # No data yet – broad invitation
        return "Great! Let's explore who your adventurer might be. You can ask me about races, classes, backgrounds, or just tell me what kind of character you're imagining."


    # Detection helpers

    def _is_gibberish(self, text: str) -> bool:
        """Detect if text is nonsense or unrecognizable."""
        # Check for dictionary words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                       'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
                       'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
                       'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
                       'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
                       'can', 'shall', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
                       'what', 'when', 'where', 'why', 'how', 'who', 'which', 'whose',
                       'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her',
                       'its', 'our', 'their', 'play', 'game', 'character', 'dnd', 'd&d',
                       'magic', 'spell', 'race', 'class', 'roll', 'dice', 'dungeon',
                       'dragon', 'player', 'dm', 'master', 'quest', 'adventure'}
        
        words = set(text.replace('?', '').replace('!', '').split())
        recognizable = words & common_words
        
        # If less than 30% recognizable words, likely gibberish
        if len(words) > 0 and len(recognizable) / len(words) < 0.3:
            return True
        
        # Check for repeated nonsense patterns
        if re.search(r'(.)\1{3,}', text):  # "blarrrrgh"
            return True
        if re.search(r'[bcdfghjklmnpqrstvwxz]{5,}', text):  # "blarghle"
            return True
        
        return False


    def _is_broad_play_question(self, text: str) -> bool:
        """Detect 'how do I play' without specific topic."""
        broad_indicators = ['how do i play', 'how to play', 'how does this work',
                           'what do i do', 'where do i start', 'help me play']
        return any(ind in text for ind in broad_indicators)


    def _extract_last_topic(self, recent) -> str:
        """Extract what we were last discussing from conversation history."""
        if not recent:
            return None
        
        # Look at last player message that wasn't minimal
        for q, a in reversed(recent):
            if len(q.split()) > 3:
                # Extract noun phrases or key terms
                keywords = ['race', 'class', 'background', 'magic', 'spell', 
                           'combat', 'skill', 'equipment', 'god', 'religion',
                           'faction', 'location', 'quest']
                for kw in keywords:
                    if kw in q.lower():
                        return kw
                # Return first content word
                words = [w for w in q.lower().split() if w not in 
                        {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'about'}]
                if words:
                    return words[-1]  # Usually the object of question
        return None


    def _is_meta_question(self, text: str) -> bool:
        """Detect questions about system/rules rather than world."""
        meta_keywords = ['reroll', 'homebrew', 'house rule', 'pvp', 'can i', 'allowed',
                        'do you allow', 'rule', 'mechanic', 'system', 'point buy',
                        'standard array', 'rolled stats', 'multclass', 'feat']
        return any(kw in text for kw in meta_keywords)


    def _has_table_rules(self, session) -> bool:
        """Check if session has stored table rules."""
        # Check session or world controller for house rules
        if hasattr(session, 'table_rules') and session.table_rules:
            return True
        wc = self.world_controller
        if hasattr(wc, 'campaign_settings') and wc.campaign_settings:
            return True
        return False


    def _check_rule(self, text: str, session) -> str:
        """Check specific rule against stored table rules."""
        # Simplified—would need actual rule storage
        rules = getattr(session, 'table_rules', {}) or {}
        
        if 'reroll' in text:
            return rules.get('reroll_policy', None)
        if 'homebrew' in text:
            return rules.get('homebrew_policy', None)
        return None


    def _is_setting_question(self, text: str) -> bool:
        """Detect questions about world/setting."""
        setting_keywords = ['setting', 'world', 'realm', 'kingdom', 'land', 'place',
                           'where are we', 'what world', 'tell me about', 'history',
                           'faction', 'location', 'city', 'town', 'region']
        return any(kw in text for kw in setting_keywords)


    def _get_world_summary(self) -> str:
        """Return brief world description for context."""
        wc = self.world_controller
        if not hasattr(wc, 'world_data') or not wc.world_data:
            return "A generic fantasy world."
        
        world = wc.world_data
        summary = f"Setting: {world.get('name', 'Unnamed World')}\n"
        summary += f"Theme: {world.get('theme', 'fantasy')}\n"
        
        locations = world.get('locations', [])[:3]
        if locations:
            summary += "Notable: " + ", ".join(loc['name'] for loc in locations) + "\n"
        
        factions = world.get('factions', [])[:2]
        if factions:
            summary += "Factions: " + ", ".join(f['name'] for f in factions) + "\n"
        
        return summary.strip()      


    def _offer_guided_help(self, session_id: str, session) -> Dict:
        """Offer help based on current state: either suggest a class if enough data, or ask an exploratory question."""
        if self._has_sufficient_data_for_class_suggestion(session.character_data):
            # Enough data to make a suggestion
            return self._suggest_class(session_id, session)
        else:
            # Not enough data – offer to explore some aspect
            guidance = self._offer_guidance(session)
            action = {"action": "ask_question", "parameters": {"question": guidance}}
            narrative = self.world_controller.consequence_engine.generate_creation_narrative(action, {})
            return {"narrative": narrative}

    def get_recent_topics(self, session_id: str) -> List[str]:
        """Get recent topics for a session"""
        if hasattr(self.world_controller, 'session_system') and self.world_controller.session_system:
            return self.world_controller.session_system.get_recent_topics(session_id)
        return []

    def _generate_resume_prompt(self, session_id: str) -> str:
        """Generate a prompt to resume character creation."""
        session = self.world_controller.session_system.get_session(session_id)
        if not session:
            return "Let's start creating your character. Tell me about the kind of adventurer you'd like to play."
        
        context = session.get_creation_context()
        prompt = f"""
        The player was in the middle of creating a character. Here's what we have so far:
        {context}
        
        Generate a friendly, concise message that:
        1. Summarizes what we've discussed (the key details already provided).
        2. Asks if they want to continue or start over.
        
        Keep it conversational and encouraging.
        """
        try:
            return self.world_controller.ai_system.generate_text(prompt)
        except Exception as e:
            print(f"Resume prompt generation failed: {e}")
            # Fallback
            details = ", ".join([f"{k}: {v}" for k, v in session.character_data.items() if v])
            return f"Welcome back! You were creating a character with these details: {details}. Would you like to continue or start over?"

    def _parse_conversation_context(self, context_str: str) -> list:
        """Convert the conversation string into a list of (player_msg, dm_msg) tuples."""
        lines = context_str.strip().split('\n')
        pairs = []
        current_player = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('Player:'):
                current_player = line[7:].strip()
            elif line.startswith('DM:') and current_player is not None:
                dm_msg = line[3:].strip()
                pairs.append((current_player, dm_msg))
                current_player = None  # reset, assuming one DM response per player message
        return pairs

    def process_message(self, session_id: str, message: str, character_id=None):
        """Process a message from a player session"""
        response_data = {}
        tool_result = None 
        print("DEBUG: DMChatHandler.process_message called")
        try:
            session_state = self.world_controller.session_system.get_or_create_session(session_id, None)
            # Retrieve player object if a player_id is associated with the session
            player = None
            if session_state.player_id:
                player = self.world_controller.players.get(session_state.player_id)

                # Resume detection for interrupted character creation
                print("DEBUG: Resume checkpoint")
                # --- Resume detection for interrupted character creation (only if no history) ---
                if not session_state.chat_history:  # ← only on first message
                    if (not character_id and 
                        session_state.character_data and 
                        session_state.creation_state != "not_started" and 
                        not session_state.active_character_id):
                        print(f"DEBUG: Resume triggered for session {session_id}")
                        resume_message = self._generate_resume_prompt(session_id)
                        return {
                            "narrative": [Dialog("DM", resume_message, "narration")],
                            "tool_result": None
                        }
                # --- END ---

            # Get character context if specified – use character_manager exclusively
            character_context = {}
            if character_id:
                character = self.world_controller.character_manager.get_character(character_id)
                if character:
                    character_context = {
                        'character_id': character_id,
                        'character_name': character.name,
                        'character_class': character.classs.name if hasattr(character, 'classs') else 'Unknown',
                        'character_race': character.race,
                        'character_level': character.level
                    }
                    # Store active character in session
                    self.world_controller.session_system.set_active_character(session_id, character_id)

            # Use active character from session if no specific character was provided
            if not character_id and session_state.active_character_id:
                character_id = session_state.active_character_id
                character = self.world_controller.character_manager.get_character(character_id)
                if character:
                    character_context = {
                        'character_id': character_id,
                        'character_name': character.name,
                        'character_class': character.classs.name if hasattr(character, 'classs') else 'Unknown',
                        'character_race': character.race,
                        'character_level': character.level
                    }


            # Build context for intent classification
            intent_context = {
                "phase": "character_creation" if not character_id else "in_game",
                "character_context": character_context,
                "session": session_state.get_creation_context() if hasattr(session_state, 'get_creation_context') else {}
            }
            intent_result = self._classify_intent(message, intent_context)
            
            print(f"AI Intent Classification: {intent_result}")

            # Handle meta-requests early
            if intent_result["intent"] == "meta_dialogue" and intent_result["confidence"] > 0.6:
                meta_response = self._handle_meta_request(message, session_id)
                narrative_responses = [Dialog("DM", meta_response, "narration")]
                # Track topic for DM response
                self._update_conversation_topics(session_id, meta_response, is_dm_response=True)
                return {
                    "narrative": narrative_responses,
                    "tool_result": {"meta_request": True}
                }

            # Track topic for regular player messages
            self._update_conversation_topics(session_id, message, is_dm_response=False)

            # If in character creation mode (no active character), use the dedicated creation flow
            # Determine if in character creation mode
            is_character_creation = not character_id and (not player or not player.active_character_id)
            if is_character_creation:
                # Return a simple response directing to the form
                return {
                    "narrative": [Dialog("DM", "Please use the character creation form to build your character.", "system")],
                    "tool_result": None
                }
            else:
                # ---- NEW: Use ConsequenceEngine instead of self.dm ---
                # First, check if tool execution is needed
                requires_tool = self._ai_detect_tool_intent(message, [], character_context)  # we don't have dm_responses yet
                tool_result = None
                if requires_tool:
                    tool_result = self._handle_tool_usage(message, session_id)
                    print(f"DEBUG: Tool result: {tool_result}")

                # Build context for consequence engine
                context = {
                    "player_id": player.id if player else session_state.player_id,
                    "character_context": character_context,
                    "session_id": session_id,
                }

                # Generate narrative responses using the consequence engine
                if tool_result and not tool_result.get("error"):
                    # If a tool was used, generate narrative based on tool result
                    narrative_responses = self.consequence_engine.generate_response_for_action(tool_result, context)
                else:
                    # No tool used, generate narrative based on intent
                    # We need to pass the original message or intent details
                    intent_result["message"] = message  # attach original message for AI use
                    narrative_responses = self.consequence_engine.generate_response_for_intent(intent_result, context)

                # If tool_result contains character data, propagate for frontend
                if tool_result and 'character_data' in tool_result:
                    response_data['character_data'] = tool_result['character_data']
                    response_data['show_character_sheet'] = True
                # ---- END NEW ----

            # Store in chat history using session_system
            if hasattr(self.world_controller, 'session_system') and self.world_controller.session_system:
                self.world_controller.session_system.add_message(session_id, "Player", message)
                for response in narrative_responses:
                    self.world_controller.session_system.add_message(session_id, "DM", response.content)

            print(f"DEBUG: Final response_data: {response_data}")
            return {
                "narrative": narrative_responses,
                "tool_result": tool_result,
                "character_data": tool_result.get('character_data') if tool_result else None
            }

            # Update topics for DM responses
            for response in narrative_responses:
                self._update_conversation_topics(session_id, response.content, is_dm_response=True)

        except Exception as e:
            print(f"DEBUG: Exception in process_message: {e}")

            traceback.print_exc()
            error_response = [Dialog("DM", "I'm having trouble processing that right now. Could you try again?", "system")]
            return {
                "narrative": error_response,
                "tool_result": {"error": str(e)}
            }

            tool_result = None
            tool_followup_responses = []

            # Check if tool execution is needed
            requires_tool = self._ai_detect_tool_intent(message, narrative_responses, character_context)

            if requires_tool:
                print("DEBUG: Tool execution required")
                tool_result = self._handle_tool_usage(message, session_id)
                print(f"DEBUG: Tool result: {tool_result}")

                # If a tool was successfully used, generate a narrative follow-up
                if tool_result and not tool_result.get("error"):
                    tool_followup_responses = self.dm.process_player_input(
                        player.id if player else session_id,
                        f"Tool execution result: {tool_result.get('message', 'Action completed')}"
                    )
                # No separate 'skipped' branch – if no tool was applicable, we simply have no tool_followup_responses

            # If tool_result contains character data, propagate it for frontend display
            if tool_result and 'character_data' in tool_result:
                response_data['character_data'] = tool_result['character_data']
                response_data['show_character_sheet'] = True

            # Combine all narrative responses
            all_narrative_responses = narrative_responses + tool_followup_responses

            # Store in chat history using session_system
            if hasattr(self.world_controller, 'session_system') and self.world_controller.session_system:
                self.world_controller.session_system.add_message(session_id, "Player", message)
                for response in all_narrative_responses:
                    self.world_controller.session_system.add_message(session_id, "DM", response.content)

            print(f"DEBUG: Final response_data: {response_data}")
            return {
                "narrative": all_narrative_responses,
                "tool_result": tool_result,
                "character_data": tool_result.get('character_data') if tool_result else None
            }

        except Exception as e:
            print(f"DEBUG: Exception in process_message: {e}")
            traceback.print_exc()
            error_response = [Dialog("DM", "I'm having trouble processing that right now. Could you try again?", "system")]
            return {
                "narrative": error_response,
                "tool_result": {"error": str(e)}
            }

    def _classify_intent(self, message, context=None):
        """Use AI exclusively to classify message intent without any keyword fallbacks"""
        try:
            return self.world_controller.dm_chat_ai.classify_intent(message, context)
        except Exception as e:
            print(f"AI intent classification failed: {e}")
            return {"intent": "general_question", "confidence": 0.5, "explanation": "AI classification failed"}

    def _handle_meta_request(self, message: str, session_id: str) -> str:
        """Generate response to meta-questions about the conversation"""
        recent_topics = self.get_recent_topics(session_id)
        if not recent_topics:
            # Brand new conversation – be welcoming, not pushy
            return "Welcome to the world! I'm here to help you explore. You can ask me about races, classes, lore, or just tell me what kind of adventure you're dreaming of."
        prompt = f"""
        You're a Dungeon Master handling a player's request about your conversation.
        
        PLAYER REQUEST: "{message}"
        RECENT TOPICS DISCUSSED: {recent_topics}
        
        Provide a helpful, specific response that references the actual topics we've been discussing.
        Mention 2-3 of the most recent specific topics, not generic categories.
        Keep your response conversational and natural.
        
        Response:
        """
        try:
            response = self.world_controller.world_ai.generate_text(prompt)
            return response.strip()
        except Exception as e:
            print(f"AI meta-response generation failed: {e}")
            if recent_topics:
                return f"We've recently discussed: {', '.join(recent_topics[-3:])}. Would you like to focus on any of these aspects?"
            return "We've been discussing character creation options. What would you like to focus on?"

    def _extract_conversation_context(self, session_id):
        """Use AI to extract meaningful context from the conversation history (placeholder)"""
        # Placeholder – will be implemented with DMChatAI later
        return {"topics_discussed": [], "last_questions": [], "current_focus": "character creation"}

    def _ai_detect_tool_intent(self, message, dm_responses, character_context=None):
        """Use AI exclusively to determine if this message requires tool execution"""
        context = {
            "dm_responses": [r.content for r in dm_responses] if dm_responses else [],
            "character_context": character_context or {}
        }
        try:
            result = self.world_controller.dm_chat_ai.detect_action_intent(message, context)
            return result.get("requires_action", False)
        except Exception as e:
            print(f"AI tool detection failed: {e}")
            return False

    def _handle_tool_usage(self, message, session_id):
        """Handle tool execution using AuthoritySystem for validation"""
        session_state = self.world_controller.session_system.get_session(session_id)
        if not session_state:
            return {"error": "Session not found"}

        player_id = session_state.player_id
        if not player_id:
            return {"error": "No player in session"}

        character_id = session_state.active_character_id
        character = None
        if character_id:
            character = self.world_controller.character_manager.get_character(character_id)

        # Use AI to determine which tool to use
        tool_to_use = None
        try:
            tool_to_use = self._determine_tool_for_message(message, "in_game")
        except Exception as e:
            print(f"Tool detection error: {e}")

        if tool_to_use:
            context = {
                "session_id": session_id,
                "player_id": player_id,
                "character_id": character_id,
                "character_name": character.name if character else "Unknown",
                "current_location": self.world_controller.current_location.id if self.world_controller.current_location else None,
                "world_id": self.world_controller.world_id if hasattr(self.world_controller, 'world_id') else None,
                "phase": "authority"
            }
            parameters = {
                "message": message,
                "character_id": character_id,
                "player_id": player_id,
                "session_id": session_id
            }
            try:
                tool_result = self.world_controller.authority_system.execute_tool(
                    tool_name=tool_to_use,
                    parameters=parameters,
                    context=context
                )
                if tool_result.get("success"):
                    return {
                        "message": tool_result.get("message", "Action processed"),
                        "action": "in_game_tool",
                        "tool_used": tool_to_use,
                        "action_data": tool_result.get("action_data"),
                        "validated": True,
                        "requires_mutation": True
                    }
                else:
                    return {
                        "message": tool_result.get("message", "Action validation failed"),
                        "action": "in_game_tool",
                        "tool_used": tool_to_use,
                        "error": tool_result.get("message"),
                        "validated": False
                    }
            except Exception as e:
                print(f"AuthoritySystem tool execution error: {e}")
                return {
                    "message": f"System error: {str(e)}",
                    "action": "in_game_tool",
                    "tool_used": tool_to_use,
                    "error": str(e)
                }
        else:
            # No tool found – return a generic result without a 'skipped' flag
            return {
                "message": f"Processed action: {message}",
                "action": "in_game_generic",
                "action_data": {"original_message": message}
            }

    def _determine_tool_for_message(self, message, context):
        """Use AI to determine which tool to invoke."""
        try:
            tool_registry = self._get_tool_registry()
            if not tool_registry:
                return None
            available_tools = list(tool_registry.tools.keys())

            ai_result = self.world_controller.dm_chat_ai.detect_action_intent(
                message,
                {"available_tools": available_tools, "context": context}
            )
            if ai_result.get("requires_action") and ai_result.get("action_type"):
                return ai_result.get("action_type")
            return None
        except Exception as e:
            print(f"Tool detection error: {e}")
            return None

    def _get_tool_registry(self):
        """Helper to get tool registry from authority_system or ai_system."""
        if hasattr(self.world_controller, 'authority_system'):
            return self.world_controller.authority_system.tool_registry
        elif hasattr(self.world_controller.ai_system, 'tool_registry'):
            return self.world_controller.ai_system.tool_registry
        return None

    # ----------------------------------------------------------------------
    # Character creation helper methods – now using SessionSystem for all state mutations
    # ----------------------------------------------------------------------
    def _handle_character_creation_tools(self, message, session_id):
        """Handle tool usage during character creation phase with proper state management"""
        session_state = self.world_controller.session_system.get_session(session_id)
        if not session_state:
            session_state = self.world_controller.session_system.get_or_create_session(session_id, None)

        # Reset character data if needed (use session system to replace)
        if not session_state.character_data:
            self.world_controller.session_system.set_character_data(session_id, {})

        if session_state.creation_state == "not_started":
            self.world_controller.session_system.set_creation_state(session_id, "gathering_info")

        extracted_data = self._extract_character_data(message, session_state.character_data)
        self.world_controller.session_system.update_character_data(session_id, extracted_data)

        if session_state.creation_state == "gathering_info":
            if self._has_sufficient_data_for_class_suggestion(session_state.character_data):
                class_info = self._determine_character_class(
                    session_state.character_data.get('class', ''),
                    session_state.character_data
                )
                # Get fresh data to avoid stale reference
                current_data = self.world_controller.session_system.get_session(session_id).character_data
                updated_data = current_data.copy()
                updated_data['suggested_class'] = class_info['primary_class']
                updated_data['suggested_multiclass'] = class_info['secondary_class']
                updated_data['class_explanation'] = class_info['explanation']
                updated_data['custom_traits'] = class_info['custom_traits']

                self.world_controller.session_system.update_character_data(session_id, updated_data)
                self.world_controller.session_system.set_creation_state(session_id, "class_suggested")
                self.world_controller.session_system.set_awaiting_confirmation(session_id, True)
                self.world_controller.session_system.set_pending_suggestion(session_id, class_info)

                return {
                    "message": f"Based on your description, I suggest {class_info['primary_class']} "
                               f"{('with a dip into ' + class_info['secondary_class'] + ' ') if class_info['secondary_class'] else ''}"
                               f"because: {class_info['explanation']}. Does this work for you?",
                    "action": "class_suggestion",
                    "character_data": session_state.character_data,
                    "requires_confirmation": True
                }

        elif session_state.creation_state == "class_suggested":
            return {
                "message": "I'm still waiting for your confirmation on the class suggestion. Does the suggested class work for you?",
                "action": "class_confirmation_reminder",
                "character_data": session_state.character_data
            }

        elif session_state.creation_state == "class_confirmed":
            if self._has_sufficient_character_data(session_state.character_data):
                character = self.world_controller.character_manager.create_character(
                    session_state.player_id,
                    session_state.character_data
                )
                if session_state.player_id:
                    # Use the new manager method to assign character to player
                    self.world_controller.character_manager.assign_character_to_player(
                        session_state.player_id, character.id
                    )
                    self.world_controller.session_system.set_creation_state(session_id, "completed")
                    return {
                        "message": f"Character {character.name} created successfully as a {session_state.character_data.get('class', 'adventurer')}!",
                        "action": "character_created",
                        "character_data": session_state.character_data,
                        "character_id": character.id,
                    }
                else:
                    return {
                        "message": "Character data is complete, but no player is associated with this session. Please start over.",
                        "action": "error",
                        "character_data": session_state.character_data
                    }

        next_question = self._determine_next_question(session_state.character_data, session_id)
        return {
            "message": next_question['question'],
            "action": "character_creation_question",
            "question_category": next_question['category'],
            "character_data": session_state.character_data
        }

    def _extract_character_data(self, message, existing_data):
        try:
            return self.world_controller.dm_chat_ai.extract_character_data(message, existing_data)
        except Exception as e:
            print(f"Error extracting character data: {e}")
            return {}

    def _has_sufficient_character_data(self, char_data):
        required = ["name", "race", "class"]
        return all(field in char_data and char_data[field] for field in required)

    def _has_sufficient_data_for_class_suggestion(self, char_data):
        has_concept = any([
            char_data.get('class'),
            char_data.get('skills'),
            char_data.get('background'),
            char_data.get('motivations')
        ])
        has_identity = char_data.get('name') and char_data.get('race')
        return has_concept and has_identity

    def _determine_character_class(self, class_concept, character_data):
        try:
            return self.world_controller.dm_chat_ai.suggest_character_class(class_concept, character_data)
        except Exception as e:
            print(f"Error determining character class: {e}")
            return {
                "primary_class": "fighter",
                "secondary_class": "",
                "explanation": "Fallback class due to analysis error",
                "custom_traits": []
            }