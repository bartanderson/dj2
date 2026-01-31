# engine/phases.py
"""
Phase System Interfaces

This module defines abstract interfaces for each phase system.
All game logic must be implemented in systems that follow these interfaces
to maintain strict phase separation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum


class PhaseError(Exception):
    """Exception raised for phase boundary violations"""
    pass


class InputPhase(ABC):
    """Input Phase System - Receives raw input from players/system"""
    
    @abstractmethod
    def receive_player_input(self, raw_input: Any, session_id: str = None) -> Dict[str, Any]:
        """
        Receive and validate raw player input
        
        Args:
            raw_input: Raw input (text, command, etc.)
            session_id: Optional session identifier
            
        Returns:
            Dictionary with validated input data
        """
        pass
    
    @abstractmethod
    def receive_system_event(self, event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receive system-generated events
        
        Args:
            event_type: Type of system event
            event_data: Event-specific data
            
        Returns:
            Dictionary with processed event data
        """
        pass
    
    @abstractmethod
    def validate_input_format(self, raw_input: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate input format (not content)
        
        Args:
            raw_input: Input to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass


class InterpretationPhase(ABC):
    """Interpretation Phase System - Determines intent from input"""
    
    @abstractmethod
    def interpret_intent(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interpret player/system intent from input
        
        Args:
            input_data: Validated input from Input Phase
            context: Game context (location, available actions, etc.)
            
        Returns:
            Dictionary with interpreted intent
        """
        pass
    
    @abstractmethod
    def disambiguate_intent(self, ambiguous_intent: Dict[str, Any], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Disambiguate when multiple interpretations are possible
        
        Args:
            ambiguous_intent: Intent with low confidence or multiple possibilities
            context: Game context for disambiguation
            
        Returns:
            Dictionary with clarified intent
        """
        pass
    
    @abstractmethod
    def suggest_action_candidates(self, intent: Dict[str, Any], 
                                 context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Suggest possible action candidates based on intent
        
        Args:
            intent: Interpreted intent
            context: Game context
            
        Returns:
            List of possible action candidates
        """
        pass


class AuthorityPhase(ABC):
    """Authority Phase System - Validates actions, rolls dice, enforces rules"""
    
    @abstractmethod
    def validate_action(self, action_candidate: Dict[str, Any], 
                       context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate action against game rules
        
        Args:
            action_candidate: Proposed action from Interpretation Phase
            context: Game context including permissions
            
        Returns:
            Dictionary with validation result
        """
        pass
    
    @abstractmethod
    def roll_dice(self, dice_expression: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Roll dice according to game rules
        
        Args:
            dice_expression: Dice expression (e.g., "2d6+3")
            context: Optional context for dice modifiers
            
        Returns:
            Dictionary with dice results
        """
        pass
    
    @abstractmethod
    def check_permissions(self, entity_id: str, action_type: str, 
                         target: Any, context: Dict[str, Any]) -> bool:
        """
        Check if entity has permission to perform action
        
        Args:
            entity_id: ID of entity attempting action
            action_type: Type of action being attempted
            target: Action target
            context: Game context
            
        Returns:
            True if permitted, False otherwise
        """
        pass
    
    @abstractmethod
    def query_dungeon_constraints(self, entity_id: str, action_type: str,
                                 location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query dungeon-specific constraints for an action
        
        Args:
            entity_id: ID of entity
            action_type: Type of action
            location_data: Current location data
            
        Returns:
            Dictionary with dungeon constraints
        """
        pass
    
    @abstractmethod
    def query_world_constraints(self, entity_id: str, action_type: str,
                               location_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query world-specific constraints for an action
        
        Args:
            entity_id: ID of entity
            action_type: Type of action
            location_data: Current location data
            
        Returns:
            Dictionary with world constraints
        """
        pass


class StateMutationPhase(ABC):
    """State Mutation Phase System - Applies authorized state changes"""
    
    @abstractmethod
    def apply_movement(self, entity_id: str, from_location: Dict[str, Any], 
                      to_location: Dict[str, Any], ruling: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply movement to game state
        
        Args:
            entity_id: ID of entity moving
            from_location: Starting location data
            to_location: Destination location data
            ruling: Authority phase ruling for this movement
            
        Returns:
            Dictionary with movement result
        """
        pass
    
    @abstractmethod
    def update_character_state(self, character_id: str, 
                             changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update character state (HP, inventory, conditions, etc.)
        
        Args:
            character_id: ID of character
            changes: State changes to apply
            
        Returns:
            Dictionary with update result
        """
        pass
    
    @abstractmethod
    def modify_world_state(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify world state (location discovery, global flags, etc.)
        
        Args:
            changes: World state changes to apply
            
        Returns:
            Dictionary with modification result
        """
        pass
    
    @abstractmethod
    def modify_dungeon_state(self, dungeon_id: str, 
                           changes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify dungeon state (room visibility, traps triggered, etc.)
        
        Args:
            dungeon_id: ID of dungeon
            changes: Dungeon state changes to apply
            
        Returns:
            Dictionary with modification result
        """
        pass
    
    @abstractmethod
    def create_entity(self, entity_type: str, 
                     entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new entity (character, item, etc.)
        
        Args:
            entity_type: Type of entity to create
            entity_data: Entity data
            
        Returns:
            Dictionary with creation result
        """
        pass


class ConsequencePhase(ABC):
    """Consequence Phase System - Generates narration, triggers encounters"""
    
    @abstractmethod
    def generate_narration(self, event: Dict[str, Any], 
                          context: Dict[str, Any]) -> str:
        """
        Generate narrative description of event
        
        Args:
            event: Event that occurred
            context: Game context for narration
            
        Returns:
            Narrative text
        """
        pass
    
    @abstractmethod
    def trigger_encounter(self, location: Dict[str, Any], 
                         party_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Trigger random or scripted encounters
        
        Args:
            location: Current location data
            party_state: Party state
            
        Returns:
            Encounter data if triggered, None otherwise
        """
        pass
    
    @abstractmethod
    def resolve_trap_effects(self, trap_id: str, 
                           victims: List[str], 
                           context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve trap effects on victims
        
        Args:
            trap_id: ID of triggered trap
            victims: List of victim entity IDs
            context: Game context
            
        Returns:
            Dictionary with trap resolution results
        """
        pass
    
    @abstractmethod
    def determine_phase_transition(self, current_state: Dict[str, Any], 
                                 event: Dict[str, Any]) -> str:
        """
        Determine if phase transition should occur
        
        Args:
            current_state: Current game state
            event: Just-processed event
            
        Returns:
            Next phase type (e.g., "combat", "exploration", "dialog")
        """
        pass
    
    @abstractmethod
    def generate_dialogue(self, npc_id: str, player_input: str, 
                         context: Dict[str, Any]) -> str:
        """
        Generate NPC dialogue response
        
        Args:
            npc_id: ID of NPC
            player_input: Player's dialogue input
            context: Dialogue context
            
        Returns:
            NPC's response text
        """
        pass


class PersistencePhase(ABC):
    """Persistence Phase System - Saves game state, logs events"""
    
    @abstractmethod
    def save_game_state(self, game_state: Dict[str, Any]) -> bool:
        """
        Save complete game state
        
        Args:
            game_state: Game state to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def append_event_log(self, event: Dict[str, Any]) -> bool:
        """
        Append event to game log
        
        Args:
            event: Event to log
            
        Returns:
            True if logged successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def snapshot_ai_memory(self, memory_data: Dict[str, Any]) -> bool:
        """
        Snapshot AI memory state
        
        Args:
            memory_data: AI memory data to snapshot
            
        Returns:
            True if snapped successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def checkpoint_game(self, game_state: Dict[str, Any]) -> str:
        """
        Create game checkpoint
        
        Args:
            game_state: Game state to checkpoint
            
        Returns:
            Checkpoint ID
        """
        pass
    
    @abstractmethod
    def load_game_state(self, save_id: str) -> Optional[Dict[str, Any]]:
        """
        Load game state from save
        
        Args:
            save_id: Save ID to load
            
        Returns:
            Loaded game state or None if failed
        """
        pass


class ViewProjectionPhase(ABC):
    """View Projection Phase System - Prepares data for UI rendering"""
    
    @abstractmethod
    def render_world_map(self, world_state: Dict[str, Any], 
                        player_view: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare world map data for UI
        
        Args:
            world_state: Complete world state
            player_view: What the player can see (fog of war, etc.)
            
        Returns:
            UI-ready world map data
        """
        pass
    
    @abstractmethod
    def render_dungeon_map(self, dungeon_state: Dict[str, Any], 
                          player_view: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare dungeon map data for UI
        
        Args:
            dungeon_state: Complete dungeon state
            player_view: What the player can see
            
        Returns:
            UI-ready dungeon map data
        """
        pass
    
    @abstractmethod
    def format_character_sheet(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format character sheet data for UI
        
        Args:
            character_data: Raw character data
            
        Returns:
            UI-ready character sheet data
        """
        pass
    
    @abstractmethod
    def format_inventory(self, inventory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format inventory data for UI
        
        Args:
            inventory_data: Raw inventory data
            
        Returns:
            UI-ready inventory data
        """
        pass
    
    @abstractmethod
    def format_combat_log(self, combat_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format combat events for UI display
        
        Args:
            combat_events: Raw combat events
            
        Returns:
            UI-ready combat log entries
        """
        pass
    
    @abstractmethod
    def format_narration(self, narration_text: str, 
                        context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format narration text for UI display
        
        Args:
            narration_text: Raw narration text
            context: Narration context
            
        Returns:
            UI-ready narration data
        """
        pass


class PhaseSystemFactory(ABC):
    """Factory for creating phase-compliant system instances"""
    
    @abstractmethod
    def create_input_system(self) -> InputPhase:
        """Create Input Phase system instance"""
        pass
    
    @abstractmethod
    def create_interpretation_system(self) -> InterpretationPhase:
        """Create Interpretation Phase system instance"""
        pass
    
    @abstractmethod
    def create_authority_system(self) -> AuthorityPhase:
        """Create Authority Phase system instance"""
        pass
    
    @abstractmethod
    def create_mutation_system(self) -> StateMutationPhase:
        """Create State Mutation Phase system instance"""
        pass
    
    @abstractmethod
    def create_consequence_system(self) -> ConsequencePhase:
        """Create Consequence Phase system instance"""
        pass
    
    @abstractmethod
    def create_persistence_system(self) -> PersistencePhase:
        """Create Persistence Phase system instance"""
        pass
    
    @abstractmethod
    def create_view_system(self) -> ViewProjectionPhase:
        """Create View Projection Phase system instance"""
        pass


# Helper function for phase validation
def validate_phase_boundary(caller_phase: str, allowed_phases: List[str]) -> bool:
    """
    Validate that a function is called from an allowed phase
    
    Args:
        caller_phase: Phase from which function is called
        allowed_phases: List of phases where function is allowed
        
    Returns:
        True if allowed, False otherwise
        
    Raises:
        PhaseError: If validation fails
    """
    if caller_phase not in allowed_phases:
        raise PhaseError(
            f"Function called from phase '{caller_phase}' "
            f"but only allowed in phases: {allowed_phases}"
        )
    return True


# Phase constants for validation
PHASE_INPUT = "input"
PHASE_INTERPRETATION = "interpretation"
PHASE_AUTHORITY = "authority"
PHASE_MUTATION = "mutation"
PHASE_CONSEQUENCE = "consequence"
PHASE_PERSISTENCE = "persistence"
PHASE_VIEW = "view"

ALL_PHASES = [
    PHASE_INPUT,
    PHASE_INTERPRETATION,
    PHASE_AUTHORITY,
    PHASE_MUTATION,
    PHASE_CONSEQUENCE,
    PHASE_PERSISTENCE,
    PHASE_VIEW
]