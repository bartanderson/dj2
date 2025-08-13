from typing import Literal
PacingPhase = Literal['exploration', 'downtime', 'tension', 'climax']

# class PacingManager:
#     def __init__(self):
#         self.pace_state = "exploration"
#         self.tension_level = 0  # 0-100 scale
#         self.pace_history = []
    
#     def adjust_pace(self, player_actions):
#         """Dynamically adjust narrative pacing based on player behavior"""
#         if "rest" in player_actions:
#             self._transition_to_downtime()
#         elif "combat" in player_actions:
#             self._transition_to_action()
#         elif "investigate" in player_actions:
#             self._transition_to_mystery()
    
#     def _transition_to_downtime(self):
#         self.pace_state = "downtime"
#         self.tension_level = max(0, self.tension_level - 30)
#         return "A moment of calm allows you to reflect and prepare"
    
#     def _transition_to_action(self):
#         self.pace_state = "action"
#         self.tension_level = min(100, self.tension_level + 40)
#         return "Suddenly, danger erupts all around you!"
    
#     def _transition_to_mystery(self):
#         self.pace_state = "mystery"
#         self.tension_level += 20
#         return "You uncover clues that deepen the central mystery"

class PacingManager:
    def __init__(self):
        self.current_phase: PacingPhase = 'exploration'
        self.phase_progress = 0  # 0-100 scale
        self.player_actions = 0
    
    def on_player_action(self, action_type: str):
        self.player_actions += 1
        
        # Pacing adjustments based on action
        if action_type in ['combat', 'discovery']:
            self._increase_tension(10)
        elif action_type in ['rest', 'dialogue']:
            self._decrease_tension(5)
    
    def on_discovery_event(self):
        self._increase_tension(15)
    
    def on_dungeon_complete(self, success: bool):
        if success:
            self.current_phase = 'downtime'
            self.phase_progress = 0
        else:
            self._increase_tension(25)
    
    def _increase_tension(self, amount: int):
        self.phase_progress = min(100, self.phase_progress + amount)
        
        # Phase transitions
        if self.phase_progress >= 75 and self.current_phase != 'climax':
            self.current_phase = 'climax'
        elif self.phase_progress >= 50 and self.current_phase not in ['tension', 'climax']:
            self.current_phase = 'tension'
    
    def _decrease_tension(self, amount: int):
        self.phase_progress = max(0, self.phase_progress - amount)
        
        # Phase transitions
        if self.phase_progress < 25 and self.current_phase != 'exploration':
            self.current_phase = 'exploration'
        elif self.phase_progress < 50 and self.current_phase == 'tension':
            self.current_phase = 'exploration'
    
    def get_pacing_recommendation(self) -> str:
        if self.current_phase == 'exploration':
            return "Introduce new locations or NPCs"
        elif self.current_phase == 'downtime':
            return "Provide roleplaying opportunities"
        elif self.current_phase == 'tension':
            return "Hint at upcoming dangers"
        elif self.current_phase == 'climax':
            return "Trigger major story event or boss battle"
        return "Maintain current pacing"