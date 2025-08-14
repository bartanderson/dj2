# world\narrative_system.py
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from abc import ABC, abstractmethod
import random
import time

class NarrativeSystem:
    def __init__(self, world_state, ai_system):
        self.world = world_state
        self.ai = ai_system
        self.guide = NarrativeGuide()
        self.consequences = ConsequenceSystem(world_state)
        self.motivation = MotivationTracker()
        self.choices = ChoiceArchitect()
        self.pacing = PacingController()
        
    def process_player_action(self, action):
        # Analyze motivation
        motivation = self.motivation.analyze_action(action)
        
        # Apply consequences
        self.consequences.log_action(action, motivation)
        
        # Get narrative guidance
        guidance = self.guide.get_gentle_nudge({
            'action': action,
            'motivation': motivation,
            'pacing': self.pacing.current_pace
        })
        
        # Generate AI response
        response = self.ai.generate_response(action)
        
        # Update pacing
        self.pacing.update_pace(action)
        
        return {
            "response": response,
            "guidance": guidance,
            "motivation": motivation,
            "pacing": self.pacing.current_pace
        }

class NarrativeGuide:
    def __init__(self):
        self.fallback_hooks = [
            "A mysterious stranger approaches you with urgent news",
            "You overhear a conversation about strange occurrences nearby",
            "A sudden environmental change demands attention"
        ]
    
    def get_gentle_nudge(self, player_actions):
        """Provide subtle narrative guidance based on player behavior"""
        if player_actions.get('distracted', False):
            return self._create_distraction_resolution()
        if player_actions.get('off_track', False):
            return self._redirect_to_storyline()
        return None
    
    def _create_distraction_resolution(self):
        """Resolve player distractions by tying them to main plot"""
        return "As you investigate the side path, you discover evidence connecting it to the main quest"
    
    def _redirect_to_storyline(self):
        """Redirect players without breaking immersion"""
        return "Your exploration leads you back to the main path, where new developments await"
    
    def emergency_nudge(self):
        """Forceful but narratively justified redirection"""
        hook = random.choice(self.fallback_hooks)
        return f"Suddenly, {hook} - demanding your immediate attention"

class ConsequenceSystem:
    def __init__(self, world_state):
        self.world = world_state
        self.action_registry = []
    
    def log_action(self, action, significance):
        """Track player actions and their narrative weight"""
        self.action_registry.append({
            "action": action,
            "significance": significance,
            "resolved": False
        })
    
    def apply_delayed_consequences(self):
        """Apply consequences for past actions at dramatically appropriate moments"""
        unresolved = [a for a in self.action_registry if not a['resolved']]
        for action in unresolved:
            if self._is_appropriate_moment(action):
                consequence = self._generate_consequence(action)
                self.world.add_event(consequence)
                action['resolved'] = True
    
    def _generate_consequence(self, action):
        consequence_map = {
            "save_npc": "The NPC you saved returns to aid you in a critical moment",
            "kill_important": "Allies of the fallen seek vengeance against you",
            "steal_artifact": "The artifact's original owners track you down",
            "ignore_quest": "The ignored problem has now grown beyond control"
        }
        return consequence_map.get(action['action'], "Your past actions have unexpected consequences")

class MotivationTracker:
    def __init__(self):
        self.player_profiles = {}
        self.session_tendencies = []
    
    def analyze_action(self, action, character):
        """Categorize player actions into motivation types"""
        if "explore" in action.lower():
            return "curiosity"
        if "fight" in action.lower() or "attack" in action.lower():
            return "combat"
        if "loot" in action.lower() or "take" in action.lower():
            return "acquisition"
        if "talk" in action.lower() or "ask" in action.lower():
            return "social"
        return "unknown"
    
    def get_narrative_leverage(self, motivation):
        """Suggest story elements that appeal to player motivations"""
        leverage_map = {
            "curiosity": "You notice something strange that begs investigation",
            "combat": "Dangerous foes appear, blocking your path forward",
            "acquisition": "A glint of treasure catches your eye nearby",
            "social": "An NPC approaches with potentially valuable information"
        }
        return leverage_map.get(motivation, "New developments unfold around you")

class ChoiceArchitect:
    def __init__(self):
        self.decision_points = {}
    
    def create_branching_path(self, key_point):
        """Create narrative branches that converge at key points"""
        branches = {
            "path_a": f"If you choose path A: {self._create_path_description('a')}",
            "path_b": f"If you choose path B: {self._create_path_description('b')}"
        }
        convergence = self._create_convergence_point(key_point)
        return {"branches": branches, "convergence": convergence}
    
    def _create_path_description(self, path):
        return {
            "a": "You take the mountain path, encountering harsh weather but finding ancient ruins",
            "b": "You follow the river, facing dangerous rapids but discovering hidden caves"
        }.get(path, "You journey through challenging terrain")
    
    def _create_convergence_point(self, key_point):
        return f"Both paths lead to {key_point}, where the next phase of your adventure awaits"

class PacingController:
    PACING_LEVELS = ["downtime", "exploration", "tension", "climax"]
    
    def __init__(self):
        self.current_pace = "exploration"
        self.transition_timer = 0
        self.transition_threshold = 5  # Actions before pacing change
    
    def update_pace(self, action):
        self.transition_timer += 1
        
        if "fight" in action or "danger" in action:
            self._escalate_pace()
        elif "rest" in action or "shop" in action:
            self._deescalate_pace()
        
        if self.transition_timer >= self.transition_threshold:
            self._random_transition()
            self.transition_timer = 0
    
    def _escalate_pace(self):
        current_index = self.PACING_LEVELS.index(self.current_pace)
        if current_index < len(self.PACING_LEVELS) - 1:
            self.current_pace = self.PACING_LEVELS[current_index + 1]
    
    def _deescalate_pace(self):
        current_index = self.PACING_LEVELS.index(self.current_pace)
        if current_index > 0:
            self.current_pace = self.PACING_LEVELS[current_index - 1]
    
    def _random_transition(self):
        # Random but logical progression
        transitions = {
            "downtime": ["exploration"],
            "exploration": ["tension", "downtime"],
            "tension": ["climax", "exploration"],
            "climax": ["downtime"]
        }
        self.current_pace = random.choice(transitions.get(self.current_pace, ["exploration"]))