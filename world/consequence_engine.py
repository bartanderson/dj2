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