# src/adapters.py
from src.interfaces import IGameState, IDungeonCell
from dungeon.state import EnhancedDungeonState

class CellAdapter(IDungeonCell):
    def __init__(self, cell):
        self._cell = cell
        
    @property
    def base_type(self) -> int:
        return self._cell.base_type
        
    @property
    def features(self) -> list:
        return self._cell.features
        
    # ... implement other IDungeonCell properties

class DungeonStateAdapter(IGameState):
    def __init__(self, state: EnhancedDungeonState):
        self._state = state
        
    def get_cell(self, x: int, y: int) -> IDungeonCell:
        return CellAdapter(self._state.get_cell(x, y))
        
    def get_visible_cells(self) -> List[Tuple[int, int]]:
        return self._state.visibility.get_visible_cells()
        
    @property
    def party_position(self) -> Tuple[int, int]:
        return self._state.party_position
        
    @property
    def width(self) -> int:
        return self._state.width
        
    @property
    def height(self) -> int:
        return self._state.height