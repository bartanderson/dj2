class ChoiceArchitect:
    def __init__(self, narrative_engine):
        self.narrative = narrative_engine
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