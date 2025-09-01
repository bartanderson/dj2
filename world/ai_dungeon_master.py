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
from psycopg2.extras import Json

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

class CharacterCreationState:
    def __init__(self, world_controller):
        self.world_controller = world_controller
        self.active = False
        self.concept_description = ""
        self.collected_info = {}
        self.conversation_history = []
        self.ready_for_creation = False
        self.missing_info = {"race", "class", "background", "abilities", "personality"}
        
    def update_from_conversation(self, message: str, dm_response: str):
        """Extract character information from natural conversation"""
        prompt = f"""
        Extract character creation information from this exchange:
        Player: {message}
        DM: {dm_response}
        
        Extract any mentioned: race, class, background, abilities, personality traits.
        Return as JSON with any found information.
        """
        
        try:
            new_info = self.world_controller.ai_system.generate_structured_data(prompt, {
                "race": "string", "class": "string", "background": "string", 
                "abilities": "list", "personality": "string"
            })
            
            # Update collected information
            for key, value in new_info.items():
                if value and value not in ["", "unknown", "none"]:
                    self.collected_info[key] = value
                    self.missing_info.discard(key)
                    
        except:
            pass  # Silently fail - we'll gather info through direct questions
            
    def should_suggest_creation(self):
        """Check if we have enough information to suggest finalizing"""
        # Require at least race, class, and some abilities/personality
        required_fields = ["race", "class"]
        has_required = all(field in self.collected_info and 
                          self.collected_info[field] not in [None, ""] 
                          for field in required_fields)
        
        # Also need some descriptive elements
        has_description = any(field in self.collected_info and 
                             self.collected_info[field] not in [None, ""]
                             for field in ["abilities", "personality", "magic_type"])
        
        return has_required and has_description
        
    def get_character_summary(self):
        """Generate a natural language summary of the character"""
        prompt = f"""
        Create a compelling character summary based on these details:
        {json.dumps(self.collected_info, indent=2)}
        
        Make it engaging and highlight what makes this character unique and interesting.
        """
        
        try:
            return self.world_controller.ai_system.generate_text(prompt)
        except:
            # Fallback summary
            parts = []
            if "race" in self.collected_info:
                parts.append(f"a {self.collected_info['race']}")
            if "class" in self.collected_info:
                parts.append(self.collected_info['class'])
            if "abilities" in self.collected_info:
                parts.append(f"with {self.collected_info['abilities']}")
                
            return " ".join(parts) if parts else "this character"


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
        # Use the AI system to generate embedding if available
        embedding = None
        if self.world_controller and hasattr(self.world_controller, 'ai_system'):
            text = f"{context_type}: {json.dumps(content)}"
            embedding = self.world_controller.ai_system.generate_embedding(text)
        
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                # Convert string player_id to UUID if needed
                try:
                    player_uuid = uuid.UUID(player_id) if player_id else None
                except ValueError:
                    player_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, player_id)
                
                # Handle world_id similarly if needed
                world_uuid = None
                if world_id:
                    try:
                        world_uuid = uuid.UUID(world_id)
                    except ValueError:
                        world_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, world_id)
                
                # Update to include embedding if available
                if embedding:
                    cur.execute(
                        "INSERT INTO narrative_context "
                        "(world_id, player_id, context_type, content, embedding) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (world_uuid, player_uuid, context_type, Json(content), embedding)
                    )
                else:
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
        try:
            # Convert IDs to UUID format
            try:
                player_uuid = uuid.UUID(player_id) if player_id else None
            except ValueError:
                player_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, player_id)
                
            world_uuid = None
            if world_id:
                try:
                    world_uuid = uuid.UUID(world_id)
                except ValueError:
                    world_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, world_id)
                    
            conn = Database.get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM narrative_context "
                    "WHERE world_id = %s AND player_id = %s "
                    "ORDER BY timestamp DESC LIMIT %s",
                    (world_uuid, player_uuid, limit))
                return [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting recent context: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def process_player_input(self, player_id: str, message: str, character_context: Dict = None) -> List[Dialog]:
        """Main method to process any player input and generate appropriate responses"""
        responses = []

        if character_context:
            self.character_context = character_context

        # Check if we're in an active character creation
        if player_id in self.character_creation_states:
            state = self.character_creation_states[player_id]
            
            if state.ready_for_creation:
                return self._handle_creation_confirmation(player_id, message)
            elif state.active:
                return self._continue_character_creation(player_id, message)
        
        # Check if this describes a character concept
        recent_dialogs = self.dialog_history[-5:] if hasattr(self, 'dialog_history') else []
        if self._detect_character_concept(message, recent_dialogs):
            return self._suggest_character_creation(player_id, message)
        
        # Original processing for other types of messages
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
        # This method remains exactly as it was before
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

    def _answer_creation_question(self, player_id: str, message: str, topic: str) -> List[Dialog]:
        """Answer questions about character creation in a conversational way"""
        state = self.character_creation_states[player_id]
        
        prompt = f"""
        During our character creation discussion, the player said: "{message}"
        We're currently exploring: {topic}

        What we've discussed so far:
        {json.dumps(state.collected_info, indent=2)}

        Provide a helpful, engaging response that:
        1. Addresses their comment or question about {topic}
        2. Asks a natural follow-up question to continue developing their character concept
        3. Keeps the process feeling like a natural conversation, not an interrogation

        Make it sound like a collaborative world-building discussion.
        """
        
        try:
            response = self.world_controller.ai_system.generate_text(prompt)
            state.conversation_history.append(f"DM: {response}")
            return [Dialog("DM", response, "narration")]
        except:
            return [Dialog("DM", 
                          "That's an interesting aspect to consider for your character. " +
                          "What else would you like to explore about them?",
                          "narration")]

    def _continue_character_creation(self, player_id: str, message: str) -> List[Dialog]:
        """Continue character creation with the new organic approach"""
        state = self.character_creation_states[player_id]
        state.conversation_history.append(f"Player: {message}")
        
        # Use AI to understand what information we're discussing
        prompt = f"""
        We're in the middle of character creation. The player said: "{message}"
        
        Previous conversation:
        {state.conversation_history[-3:]}
        
        What aspect of character creation is the player talking about?
        Options: race, class, background, abilities, personality, appearance, or other.
        
        Also extract any specific information mentioned about that aspect.
        
        Respond with JSON: {{"topic": "string", "information": "string"}}
        """
        
        try:
            analysis = self.world_controller.ai_system.generate_structured_data(
                prompt, {"topic": "string", "information": "string"}
            )
            
            # Store the information
            if analysis["topic"] and analysis["information"]:
                state.collected_info[analysis["topic"]] = analysis["information"]
                
            # Check if we have enough information to suggest finalizing
            if self._has_sufficient_character_info(state):
                return self._suggest_finalizing_creation(player_id)
                
            # Continue the natural conversation
            return self._answer_creation_question(player_id, message, analysis["topic"])
            
        except Exception as e:
            print(f"Error in character creation: {e}")
            return [Dialog("DM", "Tell me more about your character concept.", "narration")]

    # todo cleanup lists of words with AI intent replacement like in world_controller

    def _is_general_question(self, message: str) -> bool:
        """Detect if this is a general question about the game"""
        question_indicators = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can you', 'can i', 'could you', 'could i', 'would you', 'would i', 'is there', 'are there', "?"]
        game_terms = ["rule", "mechanic", "play", "game", "dungeon", "dm", "dungeon master", 'adventure', 'adventurer', 'player', 'character', 'race', 'class', 'turn', 'roll', 'initiative', 'advantage']
        
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

    def _has_sufficient_character_info(self, state) -> bool:
        """Check if we have enough information to create a character"""
        # We need at least race, class, and some defining characteristics
        required = ["race", "class"]
        has_required = all(field in state.collected_info and 
                          state.collected_info[field] not in [None, ""] 
                          for field in required)
        
        # Also need some descriptive elements
        has_description = any(field in state.collected_info and 
                             state.collected_info[field] not in [None, ""]
                             for field in ["abilities", "personality", "background"])
        
        return has_required and has_description

    def _suggest_finalizing_creation(self, player_id: str) -> List[Dialog]:
        """Suggest finalizing the character creation"""
        state = self.character_creation_states[player_id]
        
        prompt = f"""
        Based on our discussion, we've developed this character concept:
        {json.dumps(state.collected_info, indent=2)}

        Create a compelling summary of this character concept and suggest moving to the final creation step.
        Explain the different ability score generation methods in a conversational way:
        - Standard array (balanced pre-set scores)
        - Point buy (custom allocation within a point budget)
        - Rolling (traditional random generation)

        Make it inviting and offer to explain any of the options in more detail.
        """
        
        try:
            response = self.world_controller.ai_system.generate_text(prompt)
            state.ready_for_creation = True
            state.conversation_history.append(f"DM: {response}")
            return [Dialog("DM", response, "narration")]
        except:
            character_desc = f"{state.collected_info.get('race', '')} {state.collected_info.get('class', '')}"
            return [Dialog("DM",
                          f"Based on our conversation, we have a great {character_desc} concept. " +
                          "Would you like to finalize this character? " +
                          "We can use different methods for ability scores.",
                          "narration")]

    def _detect_character_concept(self, message: str, conversation_history: list) -> bool:
        """Use AI to detect if the player is describing a character concept"""
        prompt = f"""
        Analyze this player message and conversation history to determine if the player
        is describing a character concept that could lead to character creation.
        
        Player message: "{message}"
        Recent conversation: {[str(d) for d in conversation_history[-3:]]}
        
        Look for descriptions of:
        - Character abilities, powers, or skills
        - Race, species, or ancestry details
        - Class, profession, or occupation
        - Background stories or origins
        - Personality traits or motivations
        
        Respond with JSON: 
        {{"is_character_concept": boolean, "confidence": 0.0-1.0, "concept_type": "string"}}
        """
        
        try:
            result = self.world_controller.ai_system.generate_structured_data(
                prompt,
                {"is_character_concept": "boolean", "confidence": "number", "concept_type": "string"}
            )
            return result.get("is_character_concept", False) and result.get("confidence", 0) > 0.6
        except:
            return False

    def _suggest_character_creation(self, player_id: str, message: str) -> List[Dialog]:
        """Suggest character creation based on a described concept"""
        prompt = f"""
        The player has described something that sounds like a character concept: "{message}"

        Create a natural, engaging response that:
        1. Acknowledges their interesting idea
        2. Gently suggests exploring this as a character concept
        3. Asks if they'd like to develop this into a playable character

        Keep it conversational and let them guide the direction.
        """
        
        try:
            suggestion = self.world_controller.ai_system.generate_text(prompt)
            
            # Initialize character creation state
            if player_id not in self.character_creation_states:
                self.character_creation_states[player_id] = CharacterCreationState(self.world_controller)
            
            state = self.character_creation_states[player_id]
            state.active = True
            state.concept_description = message
            state.conversation_history.append(f"Player: {message}")
            
            return [Dialog("DM", suggestion, "narration")]
        except:
            return [Dialog("DM", 
                          "That sounds like an interesting character concept! " +
                          "Would you like to create a character based on this idea?",
                          "narration")]


    def _finalize_character_creation(self, player_id: str) -> List[Dialog]:
        """Finalize the character creation process"""
        state = self.character_creation_states[player_id]
        
        # Generate character summary
        character_summary = state.get_character_summary()
        
        prompt = f"""
        Based on our conversation, we've developed this character concept:
        {json.dumps(state.collected_info, indent=2)}
        
        Create a compelling summary of this character and then explain the different
        ways we can generate their attributes:
        
        1. Standard Array: Balanced pre-set scores (15, 14, 13, 12, 10, 8)
        2. Point Buy: Custom allocation with 27 points to distribute
        3. Rolling: Traditional 4d6 drop lowest for each ability
        
        Explain these options conversationally and ask if they'd like to create this character.
        """
        
        try:
            final_message = self.world_controller.ai_system.generate_text(prompt)
            state.ready_for_creation = True
            state.conversation_history.append(f"DM: {final_message}")
            return [Dialog("DM", final_message, "narration")]
        except:
            return [Dialog("DM",
                          f"Based on our conversation, we've created a concept for {character_summary}. " +
                          "Would you like me to create this character for you? " +
                          "We can use different methods for ability scores: standard array, point buy, or rolling.",
                          "narration")]

    def _handle_creation_confirmation(self, player_id: str, message: str) -> List[Dialog]:
        """Handle the player's response to the creation suggestion"""
        state = self.character_creation_states[player_id]
        
        prompt = f"""
        The player has responded to our character creation suggestion: "{message}"
        
        Determine if they want to proceed with creation or have questions about the process.
        If they want to proceed, determine which attribute generation method they prefer.
        
        Respond with JSON:
        {{
            "should_create": boolean,
            "method": "standard_array|point_buy|rolling|null",
            "needs_more_info": boolean,
            "response": "string"
        }}
        """
        
        try:
            result = self.world_controller.ai_system.generate_structured_data(prompt, {
                "should_create": "boolean",
                "method": "string",
                "needs_more_info": "boolean",
                "response": "string"
            })
            
            if result.get("should_create", False):
                # Create the character
                return self._create_character(player_id, result.get("method", "standard_array"))
            elif result.get("needs_more_info", False):
                # Provide more information
                return [Dialog("DM", result.get("response", "Let me explain the options..."), "narration")]
            else:
                # Continue conversation
                return [Dialog("DM", result.get("response", "Tell me more about what you'd like."), "narration")]
                
        except:
            return [Dialog("DM", "I'm not sure I understand. Would you like to create this character?", "narration")]

    def _create_character(self, player_id: str, method: str) -> List[Dialog]:
        """Actually create the character using the collected information"""
        state = self.character_creation_states[player_id]
        
        # Prepare character data
        char_data = {
            "name": state.collected_info.get("name", "Unnamed Character"),
            "race": state.collected_info.get("race", "Human"),
            "class": state.collected_info.get("class", "Adventurer"),
            "background": state.collected_info.get("background", "Unknown"),
            "personality": state.collected_info.get("personality", ""),
            "method": method
        }
        
        # Use the existing character creation system
        try:
            character = self.world_controller.character_builder.create_character(player_id, char_data)
            response = f"Excellent! I've created {character.name}, a {character.race} {character.classs.name}. "

            # Add some flavor based on the creation method
            if method == "standard_array":
                response += "The standard array provides a balanced foundation for your adventures."
            elif method == "point_buy":
                response += "Point buy allows you to tailor your character's strengths to your play style."
            elif method == "rolling":
                response += "The traditional rolling method captures the randomness of natural talent!"
                        
            # Clean up the creation state
            del self.character_creation_states[player_id]
            
            return [Dialog("DM", response, "narration")]
        except Exception as e:
            print(f"Error creating character: {e}")
            return [Dialog("DM", 
                          "I encountered a problem creating your character. Let's try again.",
                          "system")]


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