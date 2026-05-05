# world\aidungeon_master.py
# coding=utf-8
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
from world.dm_chat_handler import DialogResponse

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

class PlayerAction: # legacy and will be refactored.
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

class ResponseGenerator: # legacy and will be refactored.
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
    
    def create_micro_recognition(self, character: 'Character', detail: str) -> str:
        """Build on small character details players reveal"""
        return f"Your character's {detail} becomes relevant here because..."

class AIDungeonMaster:
    def __init__(self, world_controller=None, dm_chat_ai=None, character_builder=None, 
             character_manager=None, players=None):
        # Store both for backward compatibility and new architecture
        self.world_controller = world_controller
        
        # Use provided dm_chat_ai or try to get it from world_controller
        if dm_chat_ai:
            self.dm_chat_ai = dm_chat_ai
        elif world_controller and hasattr(world_controller, 'dm_chat_ai'):
            self.dm_chat_ai = world_controller.dm_chat_ai
        else:
            self.dm_chat_ai = None

        # Store other dependencies
        self.character_builder = character_builder
        self.character_manager = character_manager
        self.players = players

        # Initialize other attributes    
        self.game_state = GameState()
        self.consequence_tracker = ConsequenceTracker()
        self.response_generator = ResponseGenerator()
        self.dialog_history = []
        self.world_id = None  # Current world ID

        # Debug logging
        if self.dm_chat_ai:
            print(f"[OK] AIDungeonMaster initialized with DMChatAI")
        else:
            print(f"[OK] AIDungeonMaster initialized without DMChatAI (using legacy AI)")


    def set_world(self, world_id):
        self.world_id = world_id

    def log_context(self, world_id, player_id, context_type, content):
        embedding = None
        if hasattr(self, 'dm_chat_ai') and self.dm_chat_ai:
            content_str = json.dumps(content) if isinstance(content, dict) else str(content)
            embedding = self.dm_chat_ai.generate_embedding(content_str)
        
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

    def process_player_input(self, player_id: str, message: str, character_context: Dict = None) -> List[DialogResponse]:
        """
        Process player input by first classifying intent via DMChatAI.
        For character creation intents, delegate to DMChatHandler.
        For other intents, produce narrative responses (Consequence phase).
        """
        if not self.dm_chat_ai:
            return [DialogResponse(speaker="DM", content="I'm not ready to converse yet.", dialog_type="system")]

        # Build context for intent classification
        context = {
            "player_id": player_id,
            "character_context": character_context or {},
            "has_character": bool(character_context),
            "recent_dialogs": [str(d) for d in self.dialog_history[-3:]],
        }
        intent_result = self.dm_chat_ai.classify_intent(message, context)
        intent = intent_result.get("intent", "unknown")
        confidence = intent_result.get("confidence", 0.0)

        # If it's a character creation intent and no active character, delegate to DMChatHandler
        if intent == "character_creation" and not character_context:
            # Note: for character creation, dialog history is managed by SessionSystem, not by the DM’s internal list.
            if self.world_controller and hasattr(self.world_controller, 'dm_chat_handler'):
                # Forward the message to the session-based handler
                # We need a session_id – for simplicity, use player_id as session_id
                handler_result = self.world_controller.dm_chat_handler.process_message(
                    session_id=player_id, # TODO: Replace with actual session_id from request
                    message=message,
                    character_id=None
                )
                # Convert handler's narrative Dialog objects into our Dialog list
                return handler_result.get("narrative", [])
            else:
                return [DialogResponse(speaker="DM", content="Character creation is not available right now.", dialog_type="system")]

        # For other intents, generate narrative responses (the original consequence logic)
        # We'll keep the existing consequence generation (the 7 forces), but we should
        # simplify it – for now, just call a method that returns generic responses.
        # (In a full migration, this would become the ConsequenceEngine.)
        self.dialog_history.append(Dialog("Player", message, "character"))
        # For all other intents, generate narrative
        narrative = self._generate_narrative_response(intent, message, character_context)
        self.dialog_history.extend(narrative)
        return narrative

    def _generate_narrative_response(self, intent: str, message: str, character_context: dict) -> List[DialogResponse]:
        """Simplified narrative generation – to be expanded later."""
        # Placeholder – eventually this will use the response generator and track consequences.
        return [DialogResponse(speaker="DM", content=f"(You said: {message}) The world responds...", dialog_type="narration")]
    
    # Remains in ConsequenceEngine    
    def get_dialog_history(self) -> List[DialogResponse]:
        """Get the full dialog history"""
        return self.dialog_history
    
    # Remains (or moves to a tracker)
    def process_consequences(self):
        """Process pending consequences from past choices"""
        # This would pull from unpaid_choices and create new story complications
        # based on the three-layer approach (personal, local, ripple)
        pass