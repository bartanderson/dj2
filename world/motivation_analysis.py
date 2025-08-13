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