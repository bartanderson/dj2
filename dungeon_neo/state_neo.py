# dungeon_neo\state_neo.py: 
# WORLD SPACE: (x,y) = (horizontal,vertical)
# Stairs imported as {r,c} -> stored as x=c, y=r
# Grid access: get_cell(x,y) in world coordinates

from typing import List, Dict, Any, Tuple, Optional, Union
from dungeon_neo.grid_system import GridSystem
from dungeon_neo.constants import CELL_FLAGS, DIRECTION_VECTORS_8
from dungeon_neo.cell_neo import DungeonCellNeo
from dungeon_neo.visibility_neo import VisibilitySystemNeo
 
class DungeonStateNeo:
    NOTHING = CELL_FLAGS['NOTHING']
    BLOCKED = CELL_FLAGS['BLOCKED']
    ROOM = CELL_FLAGS['ROOM']
    CORRIDOR = CELL_FLAGS['CORRIDOR']
    PERIMETER = CELL_FLAGS['PERIMETER']
    ENTRANCE = CELL_FLAGS['ENTRANCE']
    ROOM_ID = CELL_FLAGS['ROOM_ID']
    ARCH = CELL_FLAGS['ARCH']
    DOOR = CELL_FLAGS['DOOR']
    LOCKED = CELL_FLAGS['LOCKED']
    TRAPPED = CELL_FLAGS['TRAPPED']
    SECRET = CELL_FLAGS['SECRET']
    PORTC = CELL_FLAGS['PORTC']
    STAIR_DN = CELL_FLAGS['STAIR_DN']
    STAIR_UP = CELL_FLAGS['STAIR_UP']
    LABEL = CELL_FLAGS['LABEL']

    def __init__(self, generator_result):
        self.generator_result = generator_result
        self.n_cols = generator_result['n_cols']
        self.n_rows = generator_result['n_rows']
        
        # Create grid system with proper dimensions
        self.grid_system = GridSystem(
            width=self.n_cols + 1,
            height=self.n_rows + 1
        )

        # Initialize orientation lookups before _populate_grid
        self.door_orientations = {}
        for door in generator_result.get('doors', []):
            #print(f"2a state door {door}")
            x, y = door['x'], door['y']
            orientation = door.get('orientation', 'horizontal')
            self.door_orientations[(x, y)] = orientation
            #print(f"2b state store ({x},{y}) = {orientation}")

        # print("=== STATE DOOR ORIENTATIONS ===")
        # for (x,y), orient in self.door_orientations.items():
        #     print(f"({x},{y}): {orient}")

        self.stair_orientations = {}
        self.stairs = generator_result.get('stairs', [])
        for stair in self.stairs:
            # Generator uses r=row, c=col; State uses x=col, y=row
            x = stair['c']  # column becomes x (horizontal)
            y = stair['r']  # row becomes y (vertical)
            orientation = stair.get('orientation', 'horizontal')
            self.stair_orientations[(x, y)] = orientation
            #print(f"STORED: Stair at ({x},{y}) orientation={orientation}")

        self._populate_grid(generator_result['grid'])
        
        # Initialize secret mask
        self.secret_mask = [[False] * self.grid_system.width for _ in range(self.grid_system.height)]
        
        # Initialize party position
        self._party_position = (0, 0)
        
        # Initialize visibility system
        self.visibility_system = None # Will be set later
        self.movement = None # Will be set later
        # Add party member tracking
        self.party_member_ids = []   # list of character IDs
        # Party tracking
        self.parties = {}  # party_id -> {"characters": [char_ids], "position": (x,y), "in_dungeon": True}
        self.next_party_id = 0

    def _get_entry_position(self):
        """Determine a good entry position (near stairs)."""
        # Try to find up stairs first
        if hasattr(self, 'stairs') and self.stairs:
            up_stairs = [s for s in self.stairs if s.get('key') == 'up']
            if up_stairs:
                stair = up_stairs[0]
                # ADAPTER: Generator (r,c) -> World (x,y)
                # x = column + column_delta, y = row + row_delta
                return (stair['c'] + stair.get('dc', 0), stair['r'] + stair.get('dr', 0))
        
        # Fallback to first room center
        if hasattr(self, 'rooms') and self.rooms:
            room = self.rooms[0]
            return ((room['west'] + room['east']) // 2, (room['north'] + room['south']) // 2)
        
        # Final fallback: center of grid
        return (self.width // 2, self.height // 2)

    def add_party(self, party_id: str, characters: List[dict], start_position: tuple = None):
        """Add a party to the dungeon."""
        print(f"[State] add_party called: party={party_id}, characters count={len(characters)}")
        self.parties[party_id] = {
            "characters": characters,
            "position": start_position or self._get_entry_position(),
            "in_dungeon": True
        }
        print(f"[State] Party stored with {len(self.parties[party_id]['characters'])} characters")
        # If this is the first party, also set the primary party position for movement
        if len(self.parties) == 1:
            self.party_position = self.parties[party_id]["position"]

    def get_party(self, party_id: str):
        """Get party data."""
        return self.parties.get(party_id)

    def get_parties_in_cell(self, x, y):
        """Return all parties currently in a given cell."""
        return [pid for pid, party in self.parties.items() if party["position"] == (x, y)]

    def move_party(self, party_id: str, direction: str, steps: int = 1) -> dict:
        """Move a specific party."""
        party = self.parties.get(party_id)
        if not party:
            return {"success": False, "message": "Party not found"}
        
        # After movement, check for other parties
        new_x, new_y = result['new_position']
        other_parties = self.state.get_parties_in_cell(new_x, new_y)
        
        if len(other_parties) > 1:
            # Multiple parties in same cell
            result['other_parties'] = other_parties
            result['message'] += " You see another adventuring party here."
        
        return result


    def set_party_members(self, member_ids):
        """Set the party members in this dungeon."""
        self.party_member_ids = member_ids
        print(f"[Dungeon] Party set with {len(member_ids)} members: {member_ids}")
        
    def save_debug_grid(self, filename="dungeon_debug.txt", show_blocking=True, show_types=False):
        """
        Save text-based grid representation to file
        - show_blocking: Highlight movement-blocking cells
        - show_types: Show cell type abbreviations
        """
        grid = self.get_debug_grid(show_blocking, show_types)
        try:
            with open(filename, 'w') as f:
                f.write("\n".join(grid))
            return True, f"Debug grid saved to {filename}"
        except Exception as e:
            return False, f"Error saving debug grid: {str(e)}"

    def get_debug_grid(self, show_blocking=True, show_types=True):
        """Enhanced debug view showing block fill status"""
        grid = []
        px, py = self.party_position
        
        for y in range(self.height):
            row = []
            for x in range(self.width):
                cell = self.get_cell(x, y)
                if not cell:
                    row.append('?')
                    continue
                
                # Party position
                if x == px and y == py:
                    row.append('P')
                    continue
                
                # Blocking status
                if cell.is_blocked:
                    row.append('#')  # Blocked
                elif cell.is_perimeter:
                    row.append('X')  # Perimeter
                elif cell.is_door:
                    row.append('D')  # Door
                elif cell.is_room:
                    row.append('R')  # Room
                elif cell.is_corridor:
                    row.append('C')  # Corridor
                else:
                    row.append('!')  # Unexpected type
            grid.append(''.join(row))
        
        return grid

    def _populate_grid(self, generator_grid):
        # Boundary: Converting generator row-major grid[y][x] to world-facing cells
        for door in self.generator_result.get('doors', []):
            if door['key'] != 'potential':  # Only register actual doors
                x, y = door['x'], door['y']
                self.door_orientations[(x, y)] = door['orientation']
        #print(f"POPULATE: door_orientations {self.door_orientations}")
        for y in range(self.grid_system.height):
            # Ensure row exists
            if y >= len(generator_grid):
                continue
                
            for x in range(self.grid_system.width):
                # Ensure column exists in row
                if x >= len(generator_grid[y]):
                    continue  # Skip missing columns
                    
                value = generator_grid[y][x]
                # boundary
                cell = DungeonCellNeo(value, x, y)
                
                if cell.is_door and (x, y) in self.door_orientations:
                    orientation = self.door_orientations[(x, y)]
                    cell.properties['orientation'] = orientation
                    #print(f"CELL INIT: Door at ({x},{y}) orientation={orientation}")

                self.grid_system.set_cell(x, y, cell)

    @property
    def width(self):
        return self.grid_system.width

    @property
    def height(self):
        return self.grid_system.height

    @property
    def party_position(self):
        return self._party_position

    @party_position.setter
    def party_position(self, value):
        self._party_position = value
        # Only update visibility if it exists
        if hasattr(self, 'visibility_system') and self.visibility_system:
            self.visibility_system.party_position = value

    def get_cell(self, x: int, y: int):
        """Get cell with bounds checking"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid_system.get_cell(x, y)
    
    def get_door_orientation(self, x: int, y: int):
        orientations = self.door_orientations.get((x, y), 'horizontal')
        #print(f"orientations in state: {orientations}")
        return orientations
    
    def get_stair_orientation(self, x: int, y: int):
        #print(f"RENDERER request: ({x},{y})") # this goes with "GENERATOR stair" debug print if you want to see if they match but fixed
        #print(f"Stored orientations: {list(self.stair_orientations.keys())}")
        result = self.stair_orientations.get((x, y), 'horizontal')
        #print(f"returns {result}")
        return result
    
    def reveal_secret(self, x: int, y: int):
        if self.grid_system.is_valid_position(x, y): # need to test this function
            self.secret_mask[y][x] = True
            return True
        return False
    
    def update_visibility_for_path(self, path_cells: list):
        """Update visibility for a path of cells"""
        for (x, y) in path_cells:
            self.visibility_system.mark_visibility(x, y)
        self.visibility_system.update_visibility()
