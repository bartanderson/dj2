
# world\narrative_system.py
from world.ai_dungeon_master import AIDungeonMaster, Character, GameState

class NarrativeSystem:
    def __init__(self, world_state, ai_system):
        self.world = world_state
        self.ai = ai_system

        # Initialize the AI Dungeon Master only if AI system is available
        if ai_system:
            self.dm = AIDungeonMaster()
        else:
            self.dm = None

        self.game_state = GameState()
        
        # Initialize characters from world state
        self._initialize_characters()
        
    def _initialize_characters(self):
        """Load characters from world state into the DM system"""
        
        # Safely handle missing characters attribute
        if not hasattr(self.world, 'characters') or not self.world.characters:
            return

        for player_id, character_data in self.world.characters.items():
            character = Character(
                name=character_data['name'],
                player_id=player_id,
                backstory={
                    'race': character_data['race'],
                    'class': character_data['class'],
                    'background': character_data['background']
                },
                traits=[
                    character_data['personality'],
                    character_data['ideals'],
                    character_data['bonds'],
                    character_data['flaws']
                ]
            )
            self.dm.add_character(player_id, character)
    
    def process_player_action(self, player_id: str, message: str):
        """Process player input through the AI Dungeon Master"""

        # If no DM system, return simple response
        if not self.dm:
            return {
                "responses": [{
                    "speaker": "DM",
                    "content": "Narrative system is not fully initialized",
                    "type": "system"
                }],
                "dialog_history": []
            }

        # Update game state with current scene
        self.game_state.current_scene = self.world.get_current_scene()
        
        # Process through DM system
        dialogs = self.dm.process_player_input(player_id, message)
        
        # Extract responses
        responses = []
        for dialog in dialogs:
            responses.append({
                "speaker": dialog.speaker,
                "content": dialog.content,
                "type": dialog.dialog_type
            })
        
        # Process consequences periodically
        if random.random() < 0.3:  # 30% chance to trigger consequences
            self.dm.process_consequences()
        
        return {
            "responses": responses,
            "dialog_history": [str(d) for d in self.dm.get_dialog_history()]
        }
    
    def set_current_scene(self, scene_description: str):
        """Update the current scene for narrative context"""
        self.game_state.current_scene = scene_description
        self.dm.game_state.current_scene = scene_description