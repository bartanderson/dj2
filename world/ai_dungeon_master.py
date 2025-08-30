# world\aidungeon_master.py
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from abc import ABC, abstractmethod
import random
import time
import json
import uuid
from world.db import Database
import psycopg2
from psycopg2.extras import Json, register_uuid
register_uuid()

class ActionType(Enum):
    SOCIAL = "social"
    TACTICAL = "tactical" 
    NARRATIVE = "narrative"
    CREATIVE = "creative"
    COMBAT = "combat"

class ChoiceOutcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    COMPLICATION = "complication"
    MIXED = "mixed"

@dataclass
class Character:
    name: str
    player_id: str
    backstory: Dict[str, Any] = field(default_factory=dict)
    traits: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    
class Choice:
    def __init__(self, description: str, action_type: ActionType, 
                 difficulty: int = 10, consequences: Dict[str, Any] = None):
        self.description = description
        self.action_type = action_type
        self.difficulty = difficulty
        self.consequences = consequences or {}
        self.is_real = True  # Prevents illusion of choice

@dataclass
class GameState:
    current_scene: str = ""
    world_state: Dict[str, Any] = field(default_factory=dict)
    active_npcs: List[str] = field(default_factory=list)
    pending_consequences: List[Dict] = field(default_factory=list)
    session_choices: List[Dict] = field(default_factory=list)

class Dialog:
    def __init__(self, speaker: str, content: str, dialog_type: str = "narration"):
        self.speaker = speaker
        self.content = content
        self.dialog_type = dialog_type  # narration, character, npc, system
        self.timestamp = time.time()
        
    def __str__(self):
        if self.dialog_type == "narration":
            return f"DM: {self.content}"
        elif self.dialog_type == "system":
            return f"[System] {self.content}"
        else:
            return f"{self.speaker}: {self.content}"

class PlayerAction:
    def __init__(self, player_id: str, character_name: str, action_description: str, 
                 intended_outcome: str = "", is_creative: bool = False):
        self.player_id = player_id
        self.character_name = character_name
        self.action_description = action_description
        self.intended_outcome = intended_outcome
        self.is_creative = is_creative
        self.timestamp = time.time()

class ConsequenceTracker:
    def __init__(self):
        self.unpaid_choices = []  # Choices that haven't had consequences yet
        self.character_threads = {}  # Unresolved backstory elements
        self.world_changes = []  # How player actions changed the world
        
    def add_unpaid_choice(self, choice_data: Dict):
        """Track choices that need future consequences"""
        self.unpaid_choices.append(choice_data)
        
    def add_character_thread(self, character: str, thread: str):
        """Track unresolved character backstory elements"""
        if character not in self.character_threads:
            self.character_threads[character] = []
        self.character_threads[character].append(thread)
        
    def log_world_change(self, change: Dict):
        """Record how player actions changed the world"""
        self.world_changes.append(change)

class ResponseGenerator:
    """Handles the 7 invisible forces for better DM responses"""
    
    def __init__(self):
        self.three_bucket_outcomes = {
            'social': ['reputation change', 'new relationship', 'information gained'],
            'tactical': ['resource gained/lost', 'position advantage', 'ally gained'],
            'narrative': ['new problem', 'opportunity', 'revelation']
        }
    
    def generate_real_choice_outcomes(self, choices: List[Choice]) -> Dict:
        """Ensure each choice leads to meaningfully different outcomes"""
        outcomes = {}
        for choice in choices:
            bucket = choice.action_type.value
            if bucket in self.three_bucket_outcomes:
                outcomes[choice.description] = random.choice(self.three_bucket_outcomes[bucket])
        return outcomes
    
    def transform_failure_to_complication(self, action: PlayerAction, roll_result: int) -> str:
        """Transform failure into new story opportunities instead of dead ends"""
        complications = [
            f"Your attempt doesn't work as planned, but you notice something new...",
            f"It fails, but this reveals a different approach you hadn't considered...",
            f"The failure creates an unexpected opportunity when...",
            f"You don't succeed, but now you understand why - which helps because..."
        ]
        return random.choice(complications)
    
    def create_micro_recognition(self, character: Character, detail: str) -> str:
        """Build on small character details players reveal"""
        return f"Your character's {detail} becomes relevant here because..."

class AIDungeonMaster:
    def __init__(self, world_controller=None):
        self.characters = {}
        self.game_state = GameState()
        self.consequence_tracker = ConsequenceTracker()
        self.response_generator = ResponseGenerator()
        self.dialog_history = []
        self.choice_timer = 0  # For respecting choice timing
        self.world_id = None  # Current world ID
        self.character_contexts = {} # character_id -> context
        self.character_creation_states = {}
        self.world_controller = world_controller

    def set_world(self, world_id):
        self.world_id = world_id

    def log_context(self, world_id, player_id, context_type, content):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                # Convert string player_id to UUID if needed
                try:
                    player_uuid = uuid.UUID(player_id) if player_id else None
                except ValueError:
                    # If it's not a valid UUID format, create a deterministic UUID from the string
                    player_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, player_id)
                
                # Handle world_id similarly if needed
                world_uuid = None
                if world_id:
                    try:
                        world_uuid = uuid.UUID(world_id)
                    except ValueError:
                        world_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, world_id)
                
                cur.execute(
                    "INSERT INTO narrative_context "
                    "(world_id, player_id, context_type, content) "
                    "VALUES (%s, %s, %s, %s)",
                    (world_uuid, player_uuid, context_type, Json(content))
                )
                conn.commit()
        finally:
            conn.close()
        
    def get_recent_context(self, world_id, player_id, limit=10):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM narrative_context "
                    "WHERE world_id = %s AND player_id = %s "
                    "ORDER BY timestamp DESC LIMIT %s",
                    (world_id, player_id, limit))
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    def process_player_input(self, player_id: str, message: str, character_context: Dict = None) -> List[Dialog]:
        """Main method to process any player input and generate appropriate responses"""
        responses = []

        if character_context:
            self.character_context = character_context

        # Check for character creation intent using AI
        if self._detect_character_creation_intent(message):
            return self._handle_character_creation_intent(player_id, message)
        
        # Check if player is in character creation flow
        if player_id in self.character_creation_states:
            return self._continue_character_creation(player_id, message)
        
        # Check if this is a question (contains question words or ends with ?)
        is_question = (any(word in message.lower() for word in 
                          ["what", "how", "why", "when", "where", "who", "which", "can you", "is there", "are there"]) 
                       or message.endswith('?'))
        
        # If it's a question, handle it with the AI system
        if is_question:
            return self._handle_general_input(player_id, message)
        
        # Determine if this is an action, dialog, or other general input
        if self._is_action_attempt(message):
            action = self._parse_action(player_id, message)
            responses.extend(self._handle_action(action))
        elif self._is_character_dialog(message):
            responses.extend(self._handle_character_dialog(player_id, message))
        else:
            # For non-question general input, still use the AI system
            return self._handle_general_input(player_id, message)

        return responses

    def _is_action_attempt(self, message: str) -> bool:
        """Detect if player is attempting an action"""
        action_keywords = ['try to', 'attempt', 'roll', 'check', 'i want to', 'can i', 'i use']
        return any(keyword in message.lower() for keyword in action_keywords)
    
    def _is_character_dialog(self, message: str) -> bool:
        """Detect if player is speaking in character"""
        dialog_indicators = ['"', "'", 'says', 'tells', 'whispers', 'shouts']
        return any(indicator in message.lower() for indicator in dialog_indicators)
    
    def _parse_action(self, player_id: str, message: str) -> PlayerAction:
        """Parse player message into structured action"""
        character = self.characters.get(player_id)
        
        # Use character context if available
        if hasattr(self, 'character_context') and self.character_context:
            char_name = self.character_context.get('character_name', f"Player{player_id}")
        elif character:
            char_name = character.name
        else:
            char_name = f"Player{player_id}"
        
        # Detect creativity in the approach
        is_creative = self._detect_creative_attempt(message)
        
        return PlayerAction(
            player_id=player_id,
            character_name=char_name,
            action_description=message,
            is_creative=is_creative
        )
    
    def _detect_creative_attempt(self, message: str) -> bool:
        """Detect if player is trying something creative vs. standard"""
        creative_indicators = ['unusual', 'creative', 'different', 'instead', 'what if']
        return any(indicator in message.lower() for indicator in creative_indicators)
    
    def _handle_action(self, action: PlayerAction) -> List[Dialog]:
        """Handle player actions with the 7 invisible forces in mind"""
        responses = []
        
        # 1. Real Agency - Don't create fake choices
        if self._requires_choice(action):
            choices = self._generate_real_choices(action)
            responses.append(Dialog("DM", f"You have several options: {self._format_choices(choices)}", "narration"))
            
        # 2. Safe Risk-Taking - Make failure interesting
        if self._requires_roll(action):
            roll_result = random.randint(1, 20)
            if roll_result < 10:  # Failure
                complication = self.response_generator.transform_failure_to_complication(action, roll_result)
                responses.append(Dialog("DM", complication, "narration"))
                # Ask follow-up to let them respond to the complication
                responses.append(Dialog("DM", "What do you do now?", "narration"))
            else:  # Success
                responses.append(Dialog("DM", self._generate_success_response(action), "narration"))
        
        # 3. Emotional Recognition - Notice character moments
        if self._is_character_moment(action):
            recognition = self._generate_recognition_response(action)
            responses.append(Dialog("DM", recognition, "narration"))
            
        # 4. Respect Timing - Don't rush important choices
        if self._is_important_choice(action):
            responses.append(Dialog("DM", "Take your time thinking about this...", "system"))
            
        # 5. Use Backstory - Make character history relevant
        if self._can_use_backstory(action):
            backstory_response = self._integrate_backstory(action)
            responses.append(Dialog("DM", backstory_response, "narration"))
            
        # 6. Collaborative Worldbuilding - Let players contribute
        if self._opportunity_for_collaboration(action):
            collaboration_prompt = self._create_collaboration_prompt(action)
            responses.append(Dialog("DM", collaboration_prompt, "narration"))
            
        # 7. Lasting Consequences - Make choices matter long-term
        self.consequence_tracker.add_unpaid_choice({
            'action': action.action_description,
            'character': action.character_name,
            'session': len(self.dialog_history)
        })
        
        return responses
    
    def _requires_choice(self, action: PlayerAction) -> bool:
        """Determine if action should present multiple options"""
        choice_keywords = ['how should', 'what way', 'approach', 'options']
        return any(keyword in action.action_description.lower() for keyword in choice_keywords)

    def _requires_tool_execution(self, message: str) -> bool:
        """Determine if the response indicates tool usage is needed"""
        # Simple heuristic - you might want to improve this
        tool_indicators = [
            "roll", "check", "attack", "cast", "use", "travel", "move",
            "inspect", "search", "look", "ask about", "tell", "give", "take"
        ]
        return any(indicator in message.lower() for indicator in tool_indicators)
    
    def _generate_real_choices(self, action: PlayerAction) -> List[Choice]:
        """Generate choices that lead to meaningfully different outcomes"""
        return [
            Choice("Direct approach", ActionType.TACTICAL, 12),
            Choice("Social approach", ActionType.SOCIAL, 10), 
            Choice("Creative solution", ActionType.NARRATIVE, 15)
        ]
    
    def _format_choices(self, choices: List[Choice]) -> str:
        """Format choices for presentation"""
        return " | ".join([f"{i+1}. {choice.description}" for i, choice in enumerate(choices)])
    
    def _requires_roll(self, action: PlayerAction) -> bool:
        """Determine if action needs a dice roll"""
        return "roll" in action.action_description.lower() or action.is_creative
    
    def _generate_success_response(self, action: PlayerAction) -> str:
        """Generate response for successful actions"""
        # Use character context if available
        if hasattr(self, 'character_context') and self.character_context:
            char_name = self.character_context.get('character_name', action.character_name)
        else:
            char_name = action.character_name
            
        return f"{char_name}'s {action.action_description} succeeds! Here's what happens next..."
    
    def _is_character_moment(self, action: PlayerAction) -> bool:
        """Detect when player is having a character development moment"""
        character_keywords = ['feel', 'remember', 'think about', 'backstory', 'past']
        return any(keyword in action.action_description.lower() for keyword in character_keywords)
    
    def _generate_recognition_response(self, action: PlayerAction) -> str:
        """Generate response that recognizes character development"""
        return f"I can see this means something important to {action.character_name}..."
    
    def _is_important_choice(self, action: PlayerAction) -> bool:
        """Identify choices that deserve time and consideration"""
        important_keywords = ['decide', 'choose', 'major', 'important', 'life or death']
        return any(keyword in action.action_description.lower() for keyword in important_keywords)
    
    def _can_use_backstory(self, action: PlayerAction) -> bool:
        """Check if character backstory is relevant to current action"""
        character = self.characters.get(action.player_id)
        if not character:
            return False
        return any(trait in action.action_description.lower() 
                  for trait in character.backstory.keys())
    
    def _integrate_backstory(self, action: PlayerAction) -> str:
        """Integrate character backstory into the current situation"""
        character = self.characters.get(action.player_id)
        relevant_backstory = "your past experience"  # Would be more specific in real implementation
        return f"Because of {relevant_backstory}, you recognize something others might miss..."
    
    def _opportunity_for_collaboration(self, action: PlayerAction) -> bool:
        """Identify when to invite player worldbuilding contribution"""
        return "describe" in action.action_description.lower() or "what do I see" in action.action_description.lower()
    
    def _create_collaboration_prompt(self, action: PlayerAction) -> str:
        """Create a prompt that invites player collaboration in worldbuilding"""
        return f"{action.character_name}, what detail about this place catches your attention first?"
    
    def _handle_character_dialog(self, player_id: str, message: str) -> List[Dialog]:
        """Handle in-character speech"""
        # Use character context if available
        if hasattr(self, 'character_context') and self.character_context:
            char_name = self.character_context.get('character_name', f"Player{player_id}")
        else:
            character = self.characters.get(player_id)
            char_name = character.name if character else f"Player{player_id}"
        
        responses = []
        responses.append(Dialog(char_name, message, "character"))
        
        # Generate NPC response or environmental reaction
        npc_response = self._generate_npc_response(message)
        if npc_response:
            responses.append(Dialog("NPC", npc_response, "npc"))
            
        return responses
    
    def _generate_npc_response(self, player_dialog: str) -> Optional[str]:
        """Generate appropriate NPC response to player dialog"""
        if "?" in player_dialog:
            return "The NPC considers your question carefully before responding..."
        return None
    
    def _handle_general_input(self, player_id: str, message: str) -> List[Dialog]:
        """Handle all types of questions and general input with robust error handling"""
        responses = []
        
        # Early validation to prevent exceptions
        if not self.world_controller:
            print("World controller not available for AI response")
            return [Dialog("DM", "The world is still taking shape. Please try again in a moment.", "system")]
        
        if not hasattr(self.world_controller, 'ai_system') or not self.world_controller.ai_system:
            print("AI system not available for response")
            return [Dialog("DM", "My arcane knowledge is currently unavailable. Let's focus on our adventure for now.", "system")]
        
        # Get context safely
        current_location = {}
        player_character = None
        
        try:
            if hasattr(self.world_controller, 'get_current_location_data'):
                current_location = self.world_controller.get_current_location_data() or {}
            
            if (hasattr(self.world_controller, 'characters') and 
                player_id in self.world_controller.characters):
                player_character = self.world_controller.characters[player_id]
        except Exception as e:
            print(f"Error getting context: {e}")
            # Continue without context rather than failing
        
        # Create prompt with safe context access
        location_name = current_location.get('name', 'an unknown location')
        character_name = player_character.name if player_character else 'a brave adventurer'
        
        prompt = f"""As a helpful Dungeon Master, answer this question from {character_name}: "{message}"

    We're currently at {location_name}. 

    Please provide a helpful, accurate response. If this is about game rules, be precise.
    If this is about our world, use your knowledge creatively.
    If this is general knowledge, provide a helpful answer.

    Keep your response concise and immersive."""

        # Generate response with error handling
        try:
            ai_response = self.world_controller.ai_system.generate_text(prompt)
            responses.append(Dialog("DM", ai_response, "narration"))
        except Exception as e:
            print(f"AI response generation failed: {e}")
            # Context-aware fallback without hardcoding
            fallback = self._generate_contextual_fallback(message, location_name, character_name)
            responses.append(Dialog("DM", fallback, "narration"))
        
        return responses

    def _generate_contextual_fallback(self, message: str, location_name: str, character_name: str) -> str:
        """Generate a contextual fallback response without hardcoding specific answers"""
        # Analyze the message to provide a relevant fallback
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["how", "what", "why", "when", "where", "who"]):
            # It's a question
            return f"That's an excellent question, {character_name}. The answer might reveal itself as we explore {location_name} further."
        elif any(word in message_lower for word in ["can i", "should i", "would it"]):
            # It's a request for advice
            return f"Only you can decide that, {character_name}. Trust your instincts as we navigate the challenges of {location_name}."
        else:
            # Generic statement or observation
            return f"I hear you, {character_name}. Let's see how that insight serves us here in {location_name}."
        
    def _generate_scene_description(self) -> str:
        """Generate dynamic scene description"""
        return f"You find yourself in {self.game_state.current_scene}. What catches your attention?"
    
    def add_character(self, player_id: str, character: Character):
        """Add a character to the campaign"""
        self.characters[player_id] = character
        
    def get_dialog_history(self) -> List[Dialog]:
        """Get the full dialog history"""
        return self.dialog_history
    
    def process_consequences(self):
        """Process pending consequences from past choices"""
        # This would pull from unpaid_choices and create new story complications
        # based on the three-layer approach (personal, local, ripple)
        pass

    def _continue_character_creation(self, player_id: str, message: str) -> List[Dialog]:
        """Continue character creation with direct question answering"""
        state = self.character_creation_states[player_id]
        
        # First, check if this is a question about character creation
        if self._is_question_about_creation(message):
            return self._answer_creation_question(player_id, message)
        
        # Then handle the current step
        if state["step"] == "race":
            return self._handle_race_selection(player_id, message)
        elif state["step"] == "class":
            return self._handle_class_selection(player_id, message)
        elif state["step"] == "background":
            return self._handle_background_selection(player_id, message)
        # Add more steps as needed
        
        return [Dialog("DM", "I'm not sure what you mean in the character creation process. "
                          "Would you like to continue creating your character?", "system")]

    def _is_question_about_creation(self, message: str) -> bool:
        """Detect if the message is a question about character creation"""
        question_indicators = ["what", "how", "can i", "should i", "which", "why", "?"]
        creation_terms = ["race", "class", "background", "ability", "skill", "feat", 
                         "proficiency", "equipment", "spell"]
        
        message_lower = message.lower()
        is_question = any(indicator in message_lower for indicator in question_indicators)
        is_about_creation = any(term in message_lower for term in creation_terms)
        
        return is_question and is_about_creation

    def _answer_creation_question(self, player_id: str, message: str) -> List[Dialog]:
        """Directly answer questions about character creation"""
        state = self.character_creation_states[player_id]
        current_step = state["step"]
        
        # Use AI to generate a helpful answer based on the current step
        prompt = f"""Player is creating a character and is at the {current_step} step. 
        They asked: "{message}"
        
        As a helpful Dungeon Master, provide a concise, helpful answer to their question 
        about character creation, then gently guide them back to the current step.
        
        Keep your response under 2 sentences."""
        
        try:
            answer = self.world_controller.ai_system.generate_text(prompt)
            # Add a prompt to continue the creation process
            continuation = self._get_step_prompt(current_step)
            return [Dialog("DM", f"{answer} {continuation}", "narration")]
        except:
            # Fallback if AI fails
            continuation = self._get_step_prompt(current_step)
            return [Dialog("DM", f"That's a good question! {continuation}", "narration")]

    def _get_step_prompt(self, step: str) -> str:
        """Get the appropriate prompt for the current step"""
        prompts = {
            "race": "Now, what race would you like to play?",
            "class": "What class are you considering?",
            "background": "What background story appeals to you?",
            "abilities": "How would you like to assign your ability scores?",
            "skills": "Which skills would you like to be proficient in?",
            "equipment": "What kind of equipment are you thinking about?",
            "spells": "Are you interested in any particular spells?",
            "review": "Would you like to review your character before finalizing?"
        }
        return prompts.get(step, "Let's continue with your character creation.")

    def _is_general_question(self, message: str) -> bool:
        """Detect if this is a general question about the game"""
        question_indicators = ["what", "how", "can i", "should i", "which", "why", "?"]
        game_terms = ["rule", "mechanic", "play", "game", "dungeon", "dm", "dungeon master"]
        
        message_lower = message.lower()
        is_question = any(indicator in message_lower for indicator in question_indicators)
        is_about_game = any(term in message_lower for term in game_terms)
        
        return is_question and is_about_game

    def _answer_general_question(self, message: str) -> List[Dialog]:
        """Answer general questions about the game"""
        prompt = f"""Player asked: "{message}"
        
        As a helpful Dungeon Master, provide a concise, helpful answer to their question 
        about the game. Keep your response under 2 sentences."""
        
        try:
            answer = self.world_controller.ai_system.generate_text(prompt)
            return [Dialog("DM", answer, "narration")]
        except:
            return [Dialog("DM", "That's an interesting question! As your Dungeon Master, " 
                          "I'm here to help you explore and discover the answers through play.", "narration")]


    def _detect_character_creation_intent(self, message: str) -> bool:
        """Use AI to detect if player wants to create a character"""
        prompt = f"""Determine if this player message indicates they want to create a character:
        Message: "{message}"
        
        Respond with JSON: {{"is_character_creation": true/false, "confidence": 0-1}}"""
        
        try:
            result = self.generate_structured_data(prompt, {
                "is_character_creation": "boolean",
                "confidence": "number"
            })
            return result.get("is_character_creation", False) and result.get("confidence", 0) > 0.7
        except:
            # Fallback to keyword matching if AI fails
            keywords = ["create character", "make a character", "new character", 
                       "character creation", "I want to be a", "I'd like to play as"]
            return any(keyword in message.lower() for keyword in keywords)

    def _handle_character_creation_intent(self, player_id: str, message: str) -> List[Dialog]:
        """Start character creation process"""
        self.character_creation_states[player_id] = {
            "step": "race",
            "data": {},
            "context": message
        }
        
        return [Dialog("DM", "Excellent! Let's create your character. What race would you like to play? "
                          "You could be a human, elf, dwarf, halfling, or something more exotic?", "narration")]

    def _handle_race_selection(self, player_id: str, message: str) -> List[Dialog]:
        """Process race selection and move to next step"""
        # Use AI to extract race from message
        race = self._extract_race_from_message(message)
        
        if race:
            self.character_creation_states[player_id]["data"]["race"] = race
            self.character_creation_states[player_id]["step"] = "class"
            
            return [Dialog("DM", f"A {race}, excellent choice! Now, what class would you like to play? "
                              "Fighter, wizard, rogue, cleric, or something else?", "narration")]
        else:
            return [Dialog("DM", "I didn't quite catch that. What race would you like to play? "
                              "(human, elf, dwarf, halfling, etc.)", "system")]

    def _handle_class_selection(self, player_id: str, message: str) -> List[Dialog]:
        char_class = self._extract_class_from_message(message)
        if char_class and char_class in self._get_available_classes():
            self.character_creation_states[player_id]["data"]["class"] = char_class
            self.character_creation_states[player_id]["step"] = "background"
            return [Dialog("DM", f"A {char_class}, great choice! Now, what background would you like? "
                                 "(Noble, soldier, acolyte, criminal, etc.)", "narration")]
        elif hasattr(self, 'last_class_candidates') and self.last_class_candidates:
            options = ', '.join(self.last_class_candidates)
            self.last_class_candidates = []
            return [Dialog("DM", f"I found several possible classes matching your description: {options}. "
                                 "Which one did you mean?", "system")]
        else:
            available_classes = ", ".join(self._get_available_classes())
            return [Dialog("DM", f"I didn't recognize that class. Available classes are: {available_classes}. "
                                 "Which would you like to play?", "system")]

        def _handle_background_selection(self, player_id: str, message: str) -> List[Dialog]:
            """Process background selection and move to next step"""
            # Extract background from message using AI or simple parsing
            background = self._extract_background_from_message(message)
            
            if background and background in self._get_available_backgrounds():
                self.character_creation_states[player_id]["data"]["background"] = background
                self.character_creation_states[player_id]["step"] = "abilities"
                
                return [Dialog("DM", f"A {background} background, interesting! Now, how would you like to "
                                  "determine your ability scores? (Standard array, point buy, or roll?)", "narration")]
            else:
                available_backgrounds = ", ".join(self._get_available_backgrounds())
                return [Dialog("DM", f"I didn't recognize that background. Available backgrounds are: {available_backgrounds}. "
                                  "Which would you like?", "system")]

    # Helper methods needed for the above
    def _extract_race_from_message(self, message: str) -> Optional[str]:
        """Extract race from player message"""
        # Simple implementation - can be enhanced with AI
        races = self._get_available_races()
        message_lower = message.lower()
        
        for race in races:
            if race.lower() in message_lower:
                return race
        
        return None

def _extract_class_from_message(self, message: str) -> Optional[str]:
    """Extract class from player message using AI, generic term mapping, fuzzy matching, and always guide user."""
    classes = self._get_available_classes()
    message_lower = message.lower()
    # 1. AI extraction
    try:
        prompt = f"""Extract the intended character class from this message:
        Message: '{message}'
        Available classes: {', '.join(classes)}
        Respond with JSON: {{'class': <class name or empty string>, 'confidence': 0-1, 'candidates': [<list of possible matches>]}}
        """
        if hasattr(self.world_controller, 'ai_system') and self.world_controller.ai_system:
            result = self.world_controller.ai_system.generate_structured_data(prompt, {
                "class": "string",
                "confidence": "number",
                "candidates": "list"
            })
        else:
            result = {"class": "", "confidence": 0, "candidates": []}
        ai_class = result.get("class", "")
        confidence = result.get("confidence", 0)
        candidates = result.get("candidates", [])
        if ai_class and ai_class in classes and confidence and confidence > 0.7:
            return ai_class
        if candidates and len(candidates) > 1:
            self.last_class_candidates = candidates
            return None
    except Exception:
        pass
    # 2. Generic term mapping
    generic_map = {
        "magic": ["Wizard", "Sorcerer", "Warlock", "Bard", "Druid", "Cleric"],
        "spell": ["Wizard", "Sorcerer", "Warlock", "Bard", "Druid", "Cleric"],
        "caster": ["Wizard", "Sorcerer", "Warlock", "Bard", "Druid", "Cleric"],
        "healer": ["Cleric", "Druid", "Paladin", "Bard"],
        "sneak": ["Rogue", "Bard", "Ranger"],
        "stealth": ["Rogue", "Bard", "Ranger"],
        "strong": ["Fighter", "Barbarian", "Paladin", "Ranger"],
        "tank": ["Fighter", "Barbarian", "Paladin"],
        "archer": ["Ranger", "Fighter"],
        "holy": ["Cleric", "Paladin"],
        "nature": ["Druid", "Ranger"],
        "leader": ["Paladin", "Bard"],
    }
    for key, group in generic_map.items():
        if key in message_lower:
            self.last_class_candidates = [cls for cls in group if cls in classes]
            return None
    # 3. Fuzzy matching for misspellings
    import difflib
    matches = difflib.get_close_matches(message_lower, [c.lower() for c in classes], n=2, cutoff=0.6)
    if matches:
        for cls in classes:
            if cls.lower() == matches[0]:
                return cls
        self.last_class_candidates = [cls for cls in classes if cls.lower() in matches]
        return None
    return None
    def _extract_background_from_message(self, message: str) -> Optional[str]:
        """Extract background from player message"""
        # Simple implementation - can be enhanced with AI
        backgrounds = self._get_available_backgrounds()
        message_lower = message.lower()
        
        for bg in backgrounds:
            if bg.lower() in message_lower:
                return bg
        
        return None

    def _get_available_races(self) -> List[str]:
        """Get available races from the system"""
        # This should integrate with your existing race system
        return ["Human", "Elf", "Dwarf", "Halfling", "Dragonborn", "Gnome", "Half-Elf", "Half-Orc", "Tiefling"]

    def _get_available_classes(self) -> List[str]:
        """Get available classes from the system"""
        # This should integrate with your existing class system
        return ["Barbarian", "Bard", "Cleric", "Druid", "Fighter", "Monk", 
                "Paladin", "Ranger", "Rogue", "Sorcerer", "Warlock", "Wizard"]

    def _get_available_backgrounds(self) -> List[str]:
        """Get available backgrounds from the system"""
        # This should integrate with your existing background system
        return ["Acolyte", "Charlatan", "Criminal", "Entertainer", "Folk Hero", 
                "Guild Artisan", "Hermit", "Noble", "Outlander", "Sage", 
                "Sailor", "Soldier", "Urchin"]

# Example usage and test
if __name__ == "__main__":
    # Create DM
    dm = AIDungeonMaster()
    
    # Create a character
    character = Character(
        name="Thorin",
        player_id="player1",
        backstory={"grew_up": "streets", "knows": "gang_operations"},
        traits=["street_smart", "protective"],
        goals=["help_orphans", "stop_corruption"]
    )
    dm.add_character("player1", character)
    
    # Set initial scene
    dm.game_state.current_scene = "the shadowy alley where you've tracked the gang"
    
    # Example interaction
    responses = dm.process_player_input("player1", "I want to try talking to the guard instead of fighting")
    for response in responses:
        print(response)
        
    print("\n" + "="*50 + "\n")
    
    responses = dm.process_player_input("player1", "I tell him 'I know what it's like to grow up on these streets'")
    for response in responses:
        print(response)