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

    def _detect_and_store_interest(self, message: str, session) -> None:
        """Detect interest expressions and store them without responding."""
        text_lower = message.lower()
        
        # Check for specific magic interests (avoid false positives by checking exclusivity)
        arcane_words = ['arcana', 'arcane', 'wizard', 'sorcerer', 'warlock', 'mage', 'spellbook']
        divine_words = ['divine', 'cleric', 'paladin', 'god', 'faith', 'holy', 'deity']
        primal_words = ['primal', 'druid', 'ranger', 'nature', 'wild', 'beast', 'spirit']
        
        has_arcane = any(w in text_lower for w in arcane_words)
        has_divine = any(w in text_lower for w in divine_words)
        has_primal = any(w in text_lower for w in primal_words)
        
        # Only store if clearly one category (not mixed)
        if has_arcane and not has_divine and not has_primal:
            self.world_controller.session_system.update_character_data(
                session.session_id, {'interested_in': 'arcane'}
            )
        elif has_divine and not has_arcane and not has_primal:
            self.world_controller.session_system.update_character_data(
                session.session_id, {'interested_in': 'divine'}
            )
        elif has_primal and not has_arcane and not has_divine:
            self.world_controller.session_system.update_character_data(
                session.session_id, {'interested_in': 'primal'}
            )

    def _process_creation_step(self, message: str, session_id: str) -> Dict:
        """Process a message during character creation – player‑driven exploration."""
        session = self.world_controller.session_system.get_session(session_id)
        if not session:
            return {"narrative": [Dialog("DM", "Session error. Please start over.", "system")]}

        # 1. INTERPRETATION
        intent_result = self.world_controller.dm_chat_ai.classify_intent(
            message, {
                "phase": "character_creation", 
                "session": session.get_creation_context(),
                "instruction": (
                    "If the message contains BOTH a statement AND a question, "
                    "classify based on the QUESTION. The question indicates player intent. "
                    "Example: 'Arcana sounds interesting. What races are good?' → intent: world_inquiry"
                )
            }
        )
        intent = intent_result.get("intent", "unknown")
        subintent = intent_result.get("parameters", {}).get("subintent", "")

        # 2. Handle confirmation state
        if session.awaiting_confirmation:
            if intent == "confirmation":
                is_confirmed, response = self._handle_confirmation(session_id, message, session)
                self.world_controller.session_system.set_awaiting_confirmation(session_id, False)
                if is_confirmed:
                    return self._continue_creation_after_confirmation(session_id)
                else:
                    action = {"action": "error", "parameters": {"message": response}}
                    narrative = self.world_controller.consequence_engine.generate_creation_narrative(action, {})
                    return {"narrative": narrative}
            elif intent == "clarification":
                # Answer the clarification question without clearing confirmation state
                answer = self._answer_exploratory_question(message, session)
                pending = session.pending_suggestion or {"primary_class": "that class"}
                primary = pending.get("primary_class", "that class")
                full_response = f"{answer}\n\nSo, about that suggestion: {primary} – does that work for you?"
                return {"narrative": [Dialog("DM", full_response, "dm")]}
            else:
                # Player diverted from confirmation – acknowledge and clear
                pending = session.pending_suggestion or "that choice"
                acknowledgment = f"You had {pending} on the table, but let's set that aside for a moment. "
                self.world_controller.session_system.set_awaiting_confirmation(session_id, False)
                self.world_controller.session_system.set_pending_suggestion(session_id, None)
                diverted_response = self._handle_diverted_confirmation(message, session, acknowledgment)
                return diverted_response

        # # 2. Handle confirmation state FIRST – with explicit acknowledgment of diversion
        # if session.awaiting_confirmation:
        #     if intent in ["confirmation", "clarification"]:
        #         is_confirmed, response = self._handle_confirmation(session_id, message, session)
        #         self.world_controller.session_system.set_awaiting_confirmation(session_id, False)
        #         if is_confirmed:
        #             return self._continue_creation_after_confirmation(session_id)
        #         else:
        #             action = {"action": "error", "parameters": {"message": response}}
        #             narrative = self.world_controller.consequence_engine.generate_creation_narrative(action, {})
        #             return {"narrative": narrative}
        #     else:
        #         # Player diverted from confirmation – acknowledge this explicitly
        #         pending = session.pending_suggestion or "that choice"
        #         acknowledgment = f"You had {pending} on the table, but let's set that aside for a moment. "
                
        #         self.world_controller.session_system.set_awaiting_confirmation(session_id, False)
        #         self.world_controller.session_system.set_pending_suggestion(session_id, None)
                
        #         diverted_response = self._handle_diverted_confirmation(message, session, acknowledgment)
        #         return diverted_response

        if intent == "character_creation":
            response = self._start_character_creation(session)
            return {"narrative": [Dialog("DM", response, "dm")]}

        # 2.5: Detect and store expressed interests before handling inquiries
        # This runs for ALL messages to catch "X sounds interesting" even in declarations
        self._detect_and_store_interest(message, session)

        # 3. Exploratory questions – use the robust system we built
        is_inquiry = (
            intent in ["world_inquiry", "rules_question", "clarification", "meta_dialogue"]
            or subintent in ["world_inquiry", "rules_question"]
        )
        
        # Content-based override for mixed messages with questions
        if not is_inquiry and '?' in message:
            question_words = ['what', 'which', 'how', 'who', 'where', 'why', 'when']
            has_question_word = any(w in message.lower() for w in question_words)
            
            world_keywords = ['race', 'class', 'magic', 'spell', 'god', 'faction', 'location', 'background', 'arcana', 'divine', 'primal']
            asks_about_world = any(w in message.lower() for w in world_keywords)
            
            if has_question_word and asks_about_world:
                is_inquiry = True

        if is_inquiry:
            # Check if we have interest context for targeted answer
            interest = None
            if hasattr(session, 'character_data') and session.character_data:
                interest = session.character_data.get('interested_in')
            
            if interest and any(w in message.lower() for w in ['race', 'class', 'background', 'good', 'best', 'recommend', 'what', 'which']):
                # Use interest-aware canned answer (no AI call)
                return self._answer_with_interest(message, session, interest)
            
            # No interest—use AI
            answer = self._answer_exploratory_question(message, session)
            return {"narrative": [Dialog("DM", answer, "dm")]}

        # 4. Character data extraction ONLY on declarative/intent-to-build
        extracted = None
        if intent in ["declare_intent", "describe_character", "make_choice"]:
            extracted = self.world_controller.dm_chat_ai.extract_character_data(message, session.character_data)
            if extracted:
                applied = []
                for field, value in extracted.items():
                    if value:
                        action = {
                            "action": "update_character_attribute",
                            "parameters": {"field": field, "value": value}
                        }
                        validated = self.world_controller.authority_system.validate_creation_action(action, {})
                        if validated.valid:
                            self.world_controller.session_system.update_character_data(session_id, {field: value})
                            applied.append(field)
                
                if applied:
                    confirmation = self._acknowledge_updates(applied, session.character_data)
                    return {"narrative": [Dialog("DM", confirmation, "dm")]}

        # 4.5: Interest expressed but no hard data extracted—engage substantively
        if intent in ["declare_intent", "describe_character"] and not extracted:
            return self._engage_with_interest(message, session)

        # 5. Guidance requests – explicit opt-in only
        if intent in ["seeking_guidance", "help"]:
            return self._offer_guided_help(session_id, session)

        # 6. Everything else – casual acknowledgment, NO AI pressure
        response = self._casual_acknowledgment(message, session)
        return {"narrative": [Dialog("DM", response, "dm")]}

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

    def _engage_with_interest(self, message: str, session) -> Dict:
        """Player expressed interest in a topic—engage substantively."""
        text_lower = message.lower()
        
        # Detect specific interest within broad category
        interest = None
        category = None
        
        if any(w in text_lower for w in ['magic', 'spell', 'arcane', 'cast', 'wizard', 'sorcerer']):
            category = 'magic'
            # Check if they specified which magic
            if any(w in text_lower for w in ['arcane', 'wizard', 'sorcerer']):
                interest = 'arcane'
            elif any(w in text_lower for w in ['divine', 'cleric', 'paladin', 'god']):
                interest = 'divine'
            elif any(w in text_lower for w in ['primal', 'druid', 'ranger', 'nature']):
                interest = 'primal'
        
        elif any(w in text_lower for w in ['fight', 'weapon', 'sword', 'combat', 'martial']):
            category = 'martial'
            # Could detect: heavy armor, rage, precision, etc.
            
        elif any(w in text_lower for w in ['sneak', 'stealth', 'rogue', 'thief', 'skill']):
            category = 'stealth'
            
        elif any(w in text_lower for w in ['heal', 'support', 'help', 'buff']):
            category = 'support'
        
        # Store for later contextualization
        if interest:
            self.world_controller.session_system.update_character_data(
                session.session_id, 
                {'interested_in': interest, 'interested_category': category}
            )
        
        # Check if they asked a follow-up question
        asked_followup = any(w in text_lower for w in ['race', 'class', 'good', 'best', 'what', 'which']) and '?' in message
        
        # If they specified interest AND asked followup, answer directly
        if interest and asked_followup:
            # Route to enhanced answer instead of generic menu
            return self._answer_with_interest(message, session, interest)
        
        # If they specified interest but no followup, acknowledge specifically
        if interest:
            responses = {
                'arcane': "Arcane magic—power through study or bloodline. Wizards master tomes, Sorcerers channel innate gifts. What draws you to it?",
                'divine': "Divine magic—faith made manifest. Gods grant power to their servants. What calling do you feel?",
                'primal': "Primal magic—the wild speaking through you. Nature's ally, not its master. What connection do you seek?"
            }
            return {"narrative": [Dialog("DM", responses[interest], "dm")]}
        
        # Broad category with no specification—show menu
        if category == 'magic':
            response = ("Magic comes in three main flavors: arcane (Wizards, Sorcerers—"
                       "learned or innate), divine (Clerics, Paladins—granted by gods), "
                       "and primal (Druids, Rangers—nature spirits). "
                       "What sounds appealing?")
        elif category == 'martial':
            response = ("Fighters, Paladins, Rangers, Barbarians, and Monks all handle "
                       "combat differently—heavy armor, rage, precision, or speed. "
                       "What style catches your eye?")
        elif category == 'stealth':
            response = ("Rogues excel at precision damage and skills, but Bards and "
                       "Rangers have their own tricks. Are you thinking criminal, spy, or scout?")
        elif category == 'support':
            response = ("Clerics are the classic healers, but Druids, Bards, and Paladins "
                       "keep parties alive too. Do you want to be primarily support, or mix it with offense?")
        else:
            # Unknown interest
            response = self._answer_exploratory_question(f"Tell me about {message}", session)
        
        return {"narrative": [Dialog("DM", response, "dm")]}


    def _start_character_creation(self, session) -> str:
        """Welcome the player to character creation with an open invitation."""
        # If there's already partial data, offer to resume
        if session.character_data and any(v for v in session.character_data.values()):
            summary = ", ".join([f"{k}: {v}" for k, v in session.character_data.items() if v])
            return f"Welcome back! You've already told me: {summary}. Would you like to continue there, or start fresh?"
        # No data yet – broad invitation
        return "Great! Let's explore who your adventurer might be. You can ask me about races, classes, backgrounds, or just tell me what kind of character you're imagining."

    def _handle_diverted_confirmation(self, message: str, session, acknowledgment: str) -> Dict:
        """Handle when player ignores a confirmation to ask something else."""
        # Process their new message through normal flow, then prepend acknowledgment
        # Simplified: treat as exploratory question with context
        answer = self._answer_exploratory_question(message, session)
        full_response = acknowledgment + answer
        return {"narrative": [Dialog("DM", full_response, "dm")]}


    def _acknowledge_updates(self, applied_fields: list, character_data: dict) -> str:
        """Generate tight acknowledgment of what was understood."""
        
        field_names = {
            'race': 'race',
            'class': 'class', 
            'background': 'background',
            'name': 'name',
            'ability_scores': 'ability scores',
            'equipment': 'equipment'
        }
        
        described = [field_names.get(f, f) for f in applied_fields]
        
        if len(described) == 1:
            templates = [
                f"Got it—{described[0]} noted.",
                f"Alright, {described[0]} locked in.",
                f"Copy that on the {described[0]}."
            ]
        else:
            items = ", ".join(described[:-1]) + f" and {described[-1]}"
            templates = [
                f"Got it—{items} noted.",
                f"Alright, {items} locked in.",
                f"Copy all that: {items}."
            ]
        
        # Add gentle prompt only if character is incomplete
        if not character_data.get('race') or not character_data.get('class'):
            templates = [t + " What else?" for t in templates]
        else:
            templates = [t + " Anything to adjust?" for t in templates]
        
        return random.choice(templates)

    def _answer_exploratory_question(self, message: str, session) -> str:
        """Answer a question about lore, rules, or world using AI – naturally."""
        
        # Check for recent similar first
        recent_str = self.world_controller.session_system.get_conversation_context(
            session.session_id, message_count=5
        )
        recent_pairs = self._parse_conversation_context(recent_str)
        if recent_pairs and (previous := self._find_similar_recent(message, recent_pairs)):
            return f"As I mentioned: {previous} Want me to expand on anything?"
        
        # Build the good prompt
        context = self._format_context(recent_str)
        character_guidance = self._build_character_guidance(session.character_data)
        creation_stage = self._estimate_creation_stage(session)
        
        stage_tone = {
            'blank': "The player is just starting—be welcoming and broad.",
            'early': "The player has begun choosing—connect concepts together.",
            'mid': "The player has core choices—help them integrate and refine.",
            'late': "The player is nearly done—help them finalize confidently."
        }.get(creation_stage, "Be helpful and natural.")
        
        prompt1 = f"""You are a knowledgeable, friendly Dungeon Master helping create a D&D character.

{stage_tone}

Player asks: "{message}"

{character_guidance}

Recent conversation:
{context}

Answer directly (2-4 sentences). Be specific about game elements (names, mechanics, lore).
Never ask "what would you like to know" or "what interests you"—provide substance immediately.
If their question relates to their character choices, reference those connections."""

        response = None
        
        try:
            response = self.world_controller.ai_system.generate_text(prompt1)
            if self._is_quality_response(response):
                return response.strip()
            logger.warning(f"Prompt1 failed quality check: {response[:100]}...")
        except Exception as e:
            logger.warning(f"Prompt1 exception: {e}")

        # Prompt2: stripped down but still substantive
        prompt2 = f"""The player asks: "{message}"

Answer as a DM. Name specific D&D races, classes, spells, or mechanics. 2-3 sentences. Be concrete."""

        try:
            response = self.world_controller.ai_system.generate_text(prompt2)
            # Use SAME quality check, not weaker one
            if self._is_quality_response(response):
                return response.strip()
            logger.warning(f"Prompt2 failed quality check: {response[:100]}...")
        except Exception as e:
            logger.warning(f"Prompt2 exception: {e}")

        # Both failed—use canned substantive answer or honest fallback
        return self._handle_exploratory_failure(message, session)

    def _handle_exploratory_failure(self, message: str, session) -> str:
        """
        Handle cases where _answer_exploratory_question falls through.
        Categorizes the failure and responds appropriately.
        """
        
        text_lower = message.lower().strip()
        recent = self.world_controller.session_system.get_conversation_context(
            session.session_id, message_count=5
        )
        
        # Category 1: Gibberish/Nonsense
        if self._is_gibberish(text_lower):
            return random.choice([
                "That isn't located in any of my advanced spellbooks, or lists of deities or rare monster guides.",
                "I don't find that in my tomes—perhaps a dialect I'm unfamiliar with?",
                "No record of that in the archives. Did you mean something else?"
            ])
        
        # Category 2: Overly broad "how do I play"
        if self._is_broad_play_question(text_lower):
            return ("Since we're building your character, tell me about one you'd like to play, "
                    "or was there a particular part of the game you wanted to discuss?")
        
        # Category 3: Minimal question with context
        if self._is_minimal_question(message) and recent:
            # Dredge memory for what we were discussing
            last_topic = self._extract_last_topic(recent)
            if last_topic:
                return f"Yes, regarding {last_topic}—what specifically about it?"
            return "Yes? What were we discussing?"
        
        # Category 4: Minimal question without context
        if self._is_minimal_question(message):
            return "That's a big question—what prompted that?"
        
        # Category 5: Meta/system questions
        if self._is_meta_question(text_lower):
            # Check if we actually have table rules stored
            has_rules = self._has_table_rules(session)
            if has_rules:
                answer = self._check_rule(text_lower, session)
                if answer:
                    return f"Yes, {answer}" if answer.startswith("you can") else f"No, {answer}"
            
            # No specific rules or unclear—honest fallback
            if "reroll" in text_lower:
                return "I don't have specific reroll rules set for this table—shall we allow it or stick to standard?"
            if "homebrew" in text_lower:
                return "Homebrew depends on what we're allowing—do you have something specific in mind?"
            return "That depends on the table rules—let me check what we're running."
        
        # Category 6: Setting/world questions
        if self._is_setting_question(text_lower):
            world_summary = self._get_world_summary()
            if world_summary == "A generic fantasy world.":
                return "I don't have a specific setting loaded—are we doing homebrew or a published world?"
            
            # We have world data, but AI failed to use it—give concise summary
            return f"We're in {world_summary.split(chr(10))[0].replace('Setting: ', '')}. What would you like to know about it?"

        # Category 7: Mechanics/stats questions (no interest required)
        if any(w in text_lower for w in ['stat', 'stats', 'ability', 'score', 'modifier', 'attributes', 'modifier']):
            return "Six abilities: Strength (melee, athletics), Dexterity (ranged, stealth), Constitution (health), Intelligence (knowledge, arcane), Wisdom (perception, divine), Charisma (social, magic). Scores range 3-20, with modifiers from -4 to +5."

        # Category 8: General magic types (no specific interest yet)
        if any(w in text_lower for w in ['magic', 'magical', 'spell', 'cast', 'types of magic']) and not session.character_data.get('interested_in'):
            return "Three main types: arcane (Wizards, Sorcerers—learned or innate), divine (Clerics, Paladins—granted by gods), and primal (Druids, Rangers—drawn from nature spirits). Which intrigues you?"
        
        # True edge case: unrecognized failure
        if '?' in message:
            return "I'm drawing a blank on that specific detail—let me get my books and come back to you."
        return "Still here. What were we looking at?"


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


    def _is_minimal_question(self, message: str) -> bool:
        """Detect very short questions."""
        if '?' not in message:
            return False
        words = message.replace('?', '').strip().split()
        return len(words) <= 3


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

    def _is_exploratory_question(self, message: str) -> bool:
        """Check if message actually asks for information."""
        text_lower = message.lower().strip()
        
        # Question marks are strong signal
        if '?' in message and len(text_lower) > 3:
            return True
        
        # Question starters
        question_starters = [
            'what', 'how', 'why', 'who', 'where', 'when', 'which',
            'tell me', 'explain', 'describe', 'elaborate', 'clarify',
            'can i', 'could i', 'do you', 'are there', 'is there',
            'list', 'give me', 'show me', 'i want to know'
        ]
        
        return any(text_lower.startswith(s) for s in question_starters)


    def _casual_acknowledgment(self, message: str, session) -> str:
        """Respond to non-questions with appropriate conversational momentum."""
        
        text_lower = message.lower().strip()
        creation_stage = self._estimate_creation_stage(session)
        
        # Pattern detection
        is_affirmation = any(w in text_lower for w in [
            'ok', 'okay', 'yes', 'yeah', 'yep', 'sure', 'right', 'exactly',
            'perfect', 'great', 'good', 'sounds good', 'that works', 'cool',
            'awesome', 'nice', 'excellent', 'alright', 'fine', 'sure thing'
        ])
        
        is_thinking = any(w in text_lower for w in [
            'hmm', 'um', 'uh', 'let me see', 'wait', 'hold on',
            'thinking', 'maybe', 'not sure', 'i dunno', 'huh'
        ]) or text_lower.endswith('...')
        
        is_transition = any(w in text_lower for w in [
            'so', 'anyway', 'next', 'moving on', 'what about', 'how about',
            'alright then', 'ok then', 'well then'
        ])
        
        is_hesitation = any(w in text_lower for w in [
            'i guess', 'i suppose', 'probably', 'maybe', 'kind of', 'sort of'
        ])
        
        # Stage-specific response pools
        if is_affirmation:
            if creation_stage == 'blank':
                return random.choice([
                    "Good. Where shall we start?",
                    "Alright. What sounds interesting to you?",
                    "Right then. Race, class, or something else first?",
                    "Good. What's calling to you?"
                ])
            elif creation_stage == 'early':
                return random.choice([
                    "Good. What draws your eye next?",
                    "Solid. Where shall we turn?",
                    "Right then. What else is on your mind?",
                    "Good good. Keep going."
                ])
            elif creation_stage == 'mid':
                return random.choice([
                    "Good. Seeing the shape of them yet?",
                    "Solid. How are these pieces fitting together?",
                    "Right then. What needs tightening?",
                    "Good. Feeling like a real person yet?"
                ])
            else:  # late
                return random.choice([
                    "Excellent. Ready to take them for a spin?",
                    "Perfect. Feeling good about this build?",
                    "Good. Anything still nagging at you before we finish?",
                    "Solid. Shall we lock it in?"
                ])
        
        elif is_thinking:
            return random.choice([
                "Take your time. No rush.",
                "Mull it over. I'll be here.",
                "Think it through. What's your gut saying?",
                "No pressure. Let it sit for a moment if you need.",
                "I'll wait. Better to get it right."
            ])
        
        elif is_transition:
            return random.choice([
                "Where to?",
                "What are we looking at next?",
                "What's next on your mind?",
                "Lead the way.",
                "I'm with you. Go ahead."
            ])
        
        elif is_hesitation:
            return random.choice([
                "No commitment yet—just exploring. What feels closest?",
                "Try it on mentally. See how it fits.",
                "You can always change it. What's your instinct?",
                "Hesitation's fine. What's giving you pause?"
            ])
        
        # Very short/unclear input
        if len(text_lower) < 4:
            return random.choice([
                "Mm?",
                "Yeah?",
                "I'm listening.",
                "Go on.",
                "Hmm?"
            ])
        
        # Default fallback
        return random.choice([
            "Got it.",
            "I hear you.",
            "Alright.",
            "Copy that."
        ])


    def _estimate_creation_stage(self, session) -> str:
        """Rough heuristic for how far along character creation is."""
        data = session.character_data or {}
        
        concrete_fields = ['race', 'class', 'background', 'name']
        filled = sum(1 for f in concrete_fields if data.get(f))
        
        has_ability_scores = bool(data.get('ability_scores') or data.get('stats'))
        has_equipment = bool(data.get('equipment') or data.get('gear'))
        has_spells = bool(data.get('spells') or data.get('spell_slots'))
        
        if filled == 0:
            return 'blank'
        
        elif filled <= 2 and not has_ability_scores:
            return 'early'
        
        elif filled >= 3 or (filled >= 2 and has_ability_scores):
            if has_equipment or has_spells:
                return 'late'
            return 'mid'
        
        return 'mid'


    # def _format_context(self, recent) -> str:
    #     """Convert conversation history to clean, readable string."""
    #     if not recent:
    #         return "No previous conversation."
        
    #     lines = []
    #     for q, a in recent:
    #         # Truncate long answers in context to prevent prompt bloat
    #         a_short = a[:200] + "..." if len(a) > 200 else a
    #         lines.append(f"Player: {q}\nDM: {a_short}")
        
    #     return "\n\n".join(lines)

    def _format_context(self, recent_str: str) -> str:
        """Format recent conversation for the prompt."""
        if not recent_str:
            return "No recent conversation."
        # The string already contains lines like "Player: ...\nDM: ..."
        return recent_str


    def _build_character_guidance(self, character_data: dict) -> str:
        """Create instructions for using character data in responses."""
        if not character_data:
            return "No character established yet—speak in general terms, but invite them to make choices."
        
        parts = ["Current character:"]
        for key, value in character_data.items():
            if value and not key.startswith('_'):
                parts.append(f"- {key}: {value}")
        
        parts.append("\nWhen answering:")
        parts.append("- Use 'you' to refer to their character-to-be")
        parts.append("- If they say 'my people', 'my kind', etc., refer to their race")
        parts.append("- If they ask about class features, reference their class if set")
        parts.append("- Connect lore to their choices when natural")
        
        return "\n".join(parts)


    def _find_similar_recent(self, message: str, recent_pairs: list, threshold: float = 0.8) -> Optional[str]:
        """Check if similar question was asked recently using list of (q,a) tuples."""
        import difflib
        message_lower = message.lower().strip()
        for q, a in recent_pairs:
            if message_lower == q.lower().strip():
                return a
            similarity = difflib.SequenceMatcher(None, message_lower, q.lower()).ratio()
            if similarity > threshold:
                return a
        return None


    def _is_quality_response(self, text: str) -> bool:
        """Detect substantive, non-generic responses."""
        if not text:
            return False
        
        text_lower = text.lower().strip()
        words = text.split()
        
        # Hard minimum
        if len(words) < 10:
            return False
        
        # No question-bouncing
        if text.count('?') > 0 and len(words) < 25:
            return False
        
        # Must contain at least one concrete game term
        concrete_terms = [
            'arcane', 'divine', 'primal', 'nature', 'eldritch', 'psionic',
            'wizard', 'sorcerer', 'cleric', 'druid', 'warlock', 'bard', 'paladin', 'ranger',
            'spell', 'cantrip', 'ritual', 'component', 'school', 'abjuration', 'evocation',
            'fireball', 'heal', 'magic missile', 'wild shape', 'sneak attack', 'rage',
            'elf', 'dwarf', 'human', 'halfling', 'dragonborn', 'tiefling',
            'sword', 'armor', 'shield', 'bow', 'dagger', 'axe',
            'dexterity', 'strength', 'wisdom', 'constitution', 'intelligence', 'charisma',
            'skill', 'proficiency', 'feat', 'background', 'trait', 'ideal', 'bond', 'flaw'
        ]
        
        has_concrete = any(term in text_lower for term in concrete_terms)
        if not has_concrete:
            return False
        
        # No generic hedges without substance
        hedge_phrases = [
            'many possibilities', 'various options', 'several choices',
            'interesting question', 'fascinating topic', 'great question',
            'depends on', 'up to you', 'could be many things'
        ]
        has_hedge = any(phrase in text_lower for phrase in hedge_phrases)
        
        # If it hedges, it needs MORE concrete terms to compensate
        if has_hedge and len([t for t in concrete_terms if t in text_lower]) < 3:
            return False
        
        return True

    def _simplify_prompt(self, message: str) -> str:
        """Generate fallback prompt when primary fails."""
        return f"""Answer this D&D question directly: "{message}"

    Be specific. Name actual races, classes, spells, or mechanics. 2-3 sentences."""


    def _graceful_fallback(self, message: str) -> str:
        """Honest, non-blaming response when AI fails."""
        # Don't lie about understanding
        if '?' in message:
            return "My mind's a bit clouded on that one—let me check my notes and circle back."
        
        return "I'm still here—just gathering my thoughts. What were we looking at?"       

    def _offer_guidance(self, session) -> str:
        """Offer gentle guidance when the player seems stuck or asks for help."""
        context = self.world_controller.session_system.get_conversation_context(session.session_id)
        suggestion = self.world_controller.dm_chat_ai.suggest_guidance(session.character_data, context)
        return suggestion.get("question", "What would you like to explore?")


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

    def _suggest_class(self, session_id: str, session) -> Dict:
        """Generate a class suggestion and transition to class_suggested state."""
        class_info = self._determine_character_class(
            session.character_data.get('class', ''),
            session.character_data
        )
        # Validate the suggestion action (optional, but we can keep)
        action = {
            "action": "suggest_class",
            "parameters": {"suggestion": class_info}
        }
        validated = self.world_controller.authority_system.validate_creation_action(action, {})
        if not validated.valid:
            error_action = {"action": "error", "parameters": {"message": validated.message}}
            narrative = self.world_controller.consequence_engine.generate_creation_narrative(error_action, {})
            return {"narrative": narrative}

        # Store suggestion in session
        updates = {
            'suggested_class': class_info['primary_class'],
            'suggested_multiclass': class_info['secondary_class'],
            'class_explanation': class_info['explanation'],
            'custom_traits': class_info['custom_traits']
        }
        self.world_controller.session_system.update_character_data(session_id, updates)
        self.world_controller.session_system.set_creation_state(session_id, "class_suggested")
        self.world_controller.session_system.set_awaiting_confirmation(session_id, True)
        self.world_controller.session_system.set_pending_suggestion(session_id, class_info)

        # Generate narrative via consequence engine
        narrative = self.world_controller.consequence_engine.generate_creation_narrative(action, {})
        return {"narrative": narrative}

    def _continue_creation_after_confirmation(self, session_id: str) -> Dict:
        """After a class confirmation, proceed with creation (may create character)."""
        session = self.world_controller.session_system.get_session(session_id)
        if not session:
            return {"narrative": [Dialog("DM", "Session error.", "system")]}

        # If we just confirmed, the state should now be class_confirmed
        if session.creation_state != "class_confirmed":
            self.world_controller.session_system.set_creation_state(session_id, "class_confirmed")
            session = self.world_controller.session_system.get_session(session_id)

        # Now handle the class_confirmed state (same as in _process_creation_step)
        if self._has_sufficient_character_data(session.character_data):
            action = {
                "action": "create_character",
                "parameters": {"character_data": session.character_data}
            }
            validated = self.world_controller.authority_system.validate_creation_action(action, {})
            if not validated.valid:
                return {"narrative": [Dialog("DM", validated.message, "system")]}

            character = self.world_controller.character_manager.create_character(
                session.player_id,
                session.character_data
            ) 
            if session.player_id:
                self.world_controller.character_manager.assign_character_to_player(
                    session.player_id, character.id
                )
                self.world_controller.session_system.set_creation_state(session_id, "completed")
                self.world_controller.session_system.set_active_character(session_id, character.id)
                return {
                    "narrative": [Dialog("DM", f"Character {character.name} created successfully as a {session.character_data.get('class', 'adventurer')}!", "narration")],
                    "character_data": session.character_data,
                    "character_id": character.id,
                }
            else:
                return {
                    "narrative": [Dialog("DM", "Character data is complete, but no player is associated with this session. Please start over.", "system")]
                }
        else:
            # Not enough data – should not happen if confirmation led here, but fallback
            next_q = self._determine_next_question(session.character_data, session_id)
            return {"narrative": [Dialog("DM", next_q['question'], "narration")]}

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
                print(f"DEBUG: resume check: character_id={character_id}, has_data={bool(session_state.character_data)}, creation_state={session_state.creation_state}, active_char={session_state.active_character_id}")
                if (not character_id and 
                    session_state.character_data and 
                    session_state.creation_state != "not_started" and 
                    not session_state.active_character_id):
                    print(f"DEBUG: Resume triggered for session {session_id}")
                    resume_message = self._generate_resume_prompt(session_id)
                    # Store the user message? For now, just return the resume prompt without processing the message.
                    # We'll add the user message to history later (optional).
                    return {
                        "narrative": [Dialog("DM", resume_message, "narration")],
                        "tool_result": None
                    }

            # Check if we're in a confirmation state
            if session_state.awaiting_confirmation:
                is_confirmed, response = self._handle_confirmation(session_id, message, session_state)
                # Use session system to clear confirmation flag
                self.world_controller.session_system.set_awaiting_confirmation(session_id, False)

                if is_confirmed:
                    # Continue with character creation
                    result = self._handle_character_creation_tools("", session_id)
                    if result.get("action") == "character_created":
                        return result
                    else:
                        return {
                            "narrative": [Dialog("DM", result["message"], "character_creation")],
                            "tool_result": None
                        }
                else:
                    return {
                        "narrative": [Dialog("DM", response, "clarification")],
                        "tool_result": None
                    }

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
            is_character_creation = not character_id and (not player or not player.active_character_id)

            if is_character_creation:
                creation_result = self._process_creation_step(message, session_id)
                narrative_responses = creation_result.get("narrative", [])
                if "character_data" in creation_result:
                    response_data['character_data'] = creation_result['character_data']
                if "character_id" in creation_result:
                    response_data['character_id'] = creation_result['character_id']
                # Skip the rest of the in-game processing (the else branch will not run)

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

    def _determine_next_question(self, character_data, session_id):
        conversation_context = self.world_controller.session_system.get_conversation_context(session_id)
        try:
            return self.world_controller.dm_chat_ai.suggest_next_question(character_data, conversation_context)
        except Exception as e:
            print(f"Error determining next question: {e}")
            return {
                "question": "What race would you like your character to be?",
                "priority": "Medium",
                "category": "race"
            }

    def _handle_confirmation(self, session_id: str, message: str, session_state) -> tuple:
        context = {
            "session_state": session_state,
            "character_data": session_state.character_data
        }
        try:
            assessment = self.world_controller.dm_chat_ai.interpret_confirmation(message, context)
            if assessment['is_confirmation'] and assessment['confidence'] > 0.7:
                # Player confirmed the suggestion – update class and remove temporary fields
                confirmed_class = session_state.character_data.get('suggested_class', '')
                action = {
                    "action": "confirm_class",
                    "parameters": {"confirmed_class": confirmed_class}
                }
                validated = self.world_controller.authority_system.validate_creation_action(action, {})
                if not validated.valid:
                    return False, validated.message

                self.world_controller.session_system.update_character_data(
                    session_id,
                    {"class": confirmed_class}
                )
                # Remove temporary suggestion fields
                for field in ['suggested_class', 'suggested_multiclass', 'class_explanation']:
                    self.world_controller.session_system.remove_character_data_field(session_id, field)

                self.world_controller.session_system.set_creation_state(session_id, "class_confirmed")
                self.world_controller.session_system.set_pending_suggestion(session_id, None)
                return True, "Great! Class confirmed. Let's continue with your character."

            elif assessment['corrected_value'] and assessment['confidence'] > 0.6:
                # Player provided a correction
                corrected = assessment['corrected_value']
                action = {
                    "action": "confirm_class",
                    "parameters": {"confirmed_class": corrected}
                }
                validated = self.world_controller.authority_system.validate_creation_action(action, {})
                if not validated.valid:
                    return False, validated.message

                self.world_controller.session_system.update_character_data(
                    session_id,
                    {"class": corrected}
                )
                for field in ['suggested_class', 'suggested_multiclass', 'class_explanation']:
                    self.world_controller.session_system.remove_character_data_field(session_id, field)

                self.world_controller.session_system.set_creation_state(session_id, "class_confirmed")
                self.world_controller.session_system.set_pending_suggestion(session_id, None)
                return True, f"Understood, I'll use {assessment['corrected_value']} instead. Let's continue."

            else:
                # Not a confirmation or correction – treat as rejection or unclear
                self.world_controller.session_system.set_awaiting_confirmation(session_id, False)
                self.world_controller.session_system.set_creation_state(session_id, "gathering_info")
                self.world_controller.session_system.set_pending_suggestion(session_id, None)
                # Clear temporary suggestion fields
                for field in ['suggested_class', 'suggested_multiclass', 'class_explanation']:
                    self.world_controller.session_system.remove_character_data_field(session_id, field)
                return False, "No problem! Let's keep exploring your character. Tell me more about what you're imagining."
        except Exception as e:
            print(f"Error handling confirmation: {e}")
            return False, "I had trouble understanding your response. Could you please clarify?"