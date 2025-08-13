class NarrativeGuide:
    def __init__(self, narrative_engine):
        self.narrative = narrative_engine
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