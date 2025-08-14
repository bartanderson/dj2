#tobeadded.py
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from abc import ABC, abstractmethod
import random
import time

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
    def __init__(self):
        self.characters = {}
        self.game_state = GameState()
        self.consequence_tracker = ConsequenceTracker()
        self.response_generator = ResponseGenerator()
        self.dialog_history = []
        self.choice_timer = 0  # For respecting choice timing
        
    def process_player_input(self, player_id: str, message: str) -> List[Dialog]:
        """Main method to process any player input and generate appropriate responses"""
        responses = []
        
        # Determine if this is an action, dialog, or question
        if self._is_action_attempt(message):
            action = self._parse_action(player_id, message)
            responses.extend(self._handle_action(action))
        elif self._is_character_dialog(message):
            responses.extend(self._handle_character_dialog(player_id, message))
        else:
            responses.extend(self._handle_general_input(player_id, message))
            
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
        char_name = character.name if character else f"Player{player_id}"
        
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
        return f"Your {action.action_description} succeeds! Here's what happens next..."
    
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
        """Handle general questions, OOC comments, etc."""
        responses = []
        
        if "what do I see" in message.lower():
            scene_description = self._generate_scene_description()
            responses.append(Dialog("DM", scene_description, "narration"))
        elif "help" in message.lower():
            help_text = "You can describe actions, speak in character, or ask questions about the scene."
            responses.append(Dialog("DM", help_text, "system"))
        else:
            responses.append(Dialog("DM", "I'm listening. What would you like to do?", "narration"))
            
        return responses
    
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