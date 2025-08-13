from abc import ABC, abstractmethod
from dungeon.state import EnhancedDungeonState

class BaseRenderer(ABC):
    def __init__(self, state: EnhancedDungeonState):
        self.state = state
        
    @abstractmethod
    def render(self, **kwargs):
        pass