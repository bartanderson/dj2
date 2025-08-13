#dungeon\state.py
from dungeon.renderer import DungeonRenderer
from dungeon.generator import DungeonGenerator
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageDraw
import math

class DungeonColors:
    ROOM = (255, 255, 255)        # White
    CORRIDOR = (220, 220, 220)    # Light gray
    WALL = (50, 50, 50)           # Dark gray
    DOOR = (139, 69, 19)          # Brown
    ARCH = (160, 120, 40)         # Light brown
    STAIRS = (0, 0, 0)            # Black
    SECRET = (52, 73, 94)         # Dark blue-gray
    GRID = (200, 200, 200)        # Light gray
    BACKGROUND = (52, 73, 94)     # Dark blue-gray

class DungeonCell:
    def __init__(self, base_type, x, y):
        self.base_type = base_type  # Original generated type
        self.current_type = base_type  # Current visible type
        self.x = x  # Store row position
        self.y = y  # Store column position
        self.features = []  # List of features (water, rubble, etc.)
        self.objects = []  # Interactive objects
        self.npcs = []  # NPCs present in this cell
        self.items = []  # Items in this cell
        self.visibility = {
            'explored': False,
            'visible': False,
            'light_source': False
        }
        self.search_difficulty = 10  # DC for finding hidden items
        self.searched = False
        self.metadata = {}  # Custom DM data
        self.discovered = False  # For secret doors
        self.modifications = []  # Player/DM changes
        self.temporary_effects = []  # Visual effects

    @property
    def position(self):
        """Return position as tuple (x, y)"""
        return (self.x, self.y)

    def reveal_secret(self, discovery_type="search"):
        """Reveal hidden elements in this cell"""
        if self.base_type == DungeonGenerator.SECRET:
            self.current_type = DungeonGenerator.DOOR
            self.discovered = True
            return True
        return False

    def add_modification(self, mod_type, data=None):
        self.dynamic_features.append({
            'type': mod_type,
            'data': data or {},
            'permanent': True
        })
        
    def add_effect(self, effect_type, duration):
        self.temporary_effects.append({
            'type': effect_type,
            'duration': duration,
            'elapsed': 0
        })

    def add_npc(self, npc_id):
        if npc_id not in self.npcs:
            self.npcs.append(npc_id)
    
    def remove_npc(self, npc_id):
        if npc_id in self.npcs:
            self.npcs.remove(npc_id)

    def add_item(self, item_id):
        if item_id not in self.items:
            self.items.append(item_id)
    
    def remove_item(self, item_id):
        if item_id in self.items:
            self.items.remove(item_id)

    def transform(self, new_type):
        """Permanently change cell type"""
        self.current_type = new_type
        
    def add_feature(self, feature_type, data=None):
        """Add environmental feature"""
        self.features.append({
            'type': feature_type,
            'data': data or {}
        })
        
    def break_door(self):
        """Convert door to archway"""
        if self.current_type in [DungeonGenerator.DOOR, DungeonGenerator.LOCKED]:
            self.current_type = DungeonGenerator.ARCH

    def add_puzzle(self, puzzle_id: str, description: str, success_effect: str, hints: List[str] = None):
        """Add a puzzle to this cell with hints"""
        puzzle_obj = {
            'type': 'puzzle',
            'puzzle_id': puzzle_id,
            'description': description,
            'success_effect': success_effect,
            'hints': []
        }
        
        # Add hints with default level
        if hints:
            for i, hint_text in enumerate(hints):
                puzzle_obj['hints'].append({
                    'text': hint_text,
                    'level': i  # Default level based on order
                })
                
        self.objects.append(puzzle_obj)

    def get_puzzle_hints(self, puzzle_id: str) -> List[Dict[str, Any]]:
        """Get hints for a specific puzzle"""
        for obj in self.objects:
            if obj.get('type') == 'puzzle' and obj.get('puzzle_id') == puzzle_id:
                return obj.get('hints', [])
        return []

class VisibilitySystem:
    def __init__(self, dungeon, party_position):
        self.dungeon = dungeon
        self.party_position = party_position
        self.light_sources = [party_position] if party_position else []
        self.reveal_all = False  # Debug flag
        self.true_state = {}  # Persistent exploration progress
        self.view_state = {}  # Temporary view overrides
        self.init_true_state()

    def set_reveal_all(self, reveal: bool):
        """Set global reveal state"""
        self.reveal_all = reveal
        self.update_visibility()
        
    def init_true_state(self):
        """Initialize true exploration state"""
        for x, row in enumerate(self.dungeon):
            for y, cell in enumerate(row):
                self.true_state[(x, y)] = {
                    'explored': False,
                    'visible': False
                }
    
    def calculate_visible_cells(self, max_distance=8):
        """Calculate visible cells using recursive shadowcasting"""
        visible = set()
        if not self.party_position:
            return visible
            
        start_x, start_y = self.party_position
        visible.add((start_x, start_y))
        
        # Process each octant around the player
        for octant in range(8):
            self._cast_light(start_x, start_y, octant, 1, 1.0, 0.0, max_distance, visible)
            
        return visible

    def _cast_light(self, cx, cy, octant, row, start_slope, end_slope, max_distance, visible):
        """Recursive light casting for one octant"""
        if row > max_distance:
            return
            
        # Calculate start and end columns for this row
        start_col = max(0, -row)
        end_col = min(row, max_distance)

        # Initialize was_blocked for this row
        was_blocked = False
        
        # Process columns in this row
        for col in range(start_col, end_col + 1):
            # Skip the center cell
            if col == 0 and row == 0:
                continue
                
            # Calculate slopes of current cell
            left_slope = (col - 0.5) / (row + 0.5)
            right_slope = (col + 0.5) / (row - 0.5)
            
            # Skip if beyond our slope range
            if right_slope <= start_slope:
                continue
            if left_slope >= end_slope:
                break
                
            # Transform to grid coordinates
            grid_x, grid_y = self._transform_octant(cx, cy, octant, col, row)
            
            # Only process cells that are within bounds
            if not (0 <= grid_x < len(self.dungeon) and (0 <= grid_y < len(self.dungeon[0]))):
                continue
                
            # Add to visible
            visible.add((grid_x, grid_y))
            
            # Check if cell blocks visibility
            cell = self.dungeon[grid_x][grid_y]
            is_blocked = cell.base_type & DungeonGenerator.BLOCKED
            if cell.base_type == DungeonGenerator.SECRET and not cell.discovered:
                is_blocked = True
                
            if is_blocked:
                # If previous cell wasn't blocked, cast new rays
                if col > start_col and not was_blocked:
                    self._cast_light(cx, cy, octant, row + 1, start_slope, left_slope, max_distance, visible)
                    
                # Update end slope
                end_slope = right_slope
                was_blocked = True
            else:
                # If previous cell was blocked, cast new ray
                if was_blocked:
                    self._cast_light(cx, cy, octant, row + 1, start_slope, left_slope, max_distance, visible)
                was_blocked = False
                
        # Continue casting if not blocked at end of row
        if not was_blocked:
            self._cast_light(cx, cy, octant, row + 1, start_slope, end_slope, max_distance, visible)

    def _transform_octant(self, cx, cy, octant, col, row):
        """Transform octant coordinates to grid coordinates"""
        if octant == 0: return cx + col, cy - row  # E
        if octant == 1: return cx + row, cy - col  # SE
        if octant == 2: return cx + row, cy + col  # S
        if octant == 3: return cx + col, cy + row  # SW
        if octant == 4: return cx - col, cy + row  # W
        if octant == 5: return cx - row, cy + col  # NW
        if octant == 6: return cx - row, cy - col  # N
        if octant == 7: return cx - col, cy - row  # NE
        return cx, cy

    def reset_visibility(self):
        """Reset visibility to initial state"""
        self.init_true_state()
        self.update_visibility()

    def clear_view(self):
        """Clear temporary view overrides"""
        self.view_state = {}
    
    def get_visibility(self, pos):
        """Get effective visibility with view state overrides"""
        if self.reveal_all:
            return {'explored': True, 'visible': True}
        if pos in self.view_state:
            return self.view_state[pos]
        return self.true_state.get(pos, {'explored': False, 'visible': False})

    def get_visible_cells(self):
        """Return list of currently visible positions"""
        visible = []
        for x, row in enumerate(self.dungeon):
            for y, cell in enumerate(row):
                if cell.visibility['visible']:
                    visible.append((x, y))
        return visible
        
    def update_visibility(self):
        """Update visibility based on current state"""
        if self.reveal_all:
            # Set all cells to visible in true state
            for pos in self.true_state:
                self.true_state[pos] = {'explored': True, 'visible': True}
        else:
            # Normal visibility calculation
            visible_cells = self.calculate_visible_cells()
            for pos in self.true_state:
                # Preserve exploration status
                explored = self.true_state[pos]['explored']
                visible = pos in visible_cells
                self.true_state[pos] = {
                    'explored': explored or visible,
                    'visible': visible
                }
                
        # Apply to cells
        for pos, state in self.true_state.items():
            x, y = pos
            if 0 <= x < len(self.dungeon) and 0 <= y < len(self.dungeon[0]):
                cell = self.dungeon[x][y]
                cell.visibility['explored'] = state['explored']
                cell.visibility['visible'] = state['visible']

    def has_line_of_sight(self, from_pos, to_pos):
        x0, y0 = from_pos
        x1, y1 = to_pos
        
        # If same position, always visible
        if from_pos == to_pos:
            return True
            
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        # Use float for more precise calculation
        steps = max(dx, dy)
        if steps == 0:
            return True
            
        # Use a set to track visited positions
        visited = set()
        
        while True:
            # Check if we've reached the target
            if (x0, y0) == to_pos:
                return True
                
            # Add current position to visited
            visited.add((x0, y0))
            
            # Get current cell
            cell = self.dungeon[x0][y0]
            
            # Check if cell blocks vision
            if cell.base_type & DungeonGenerator.BLOCKED:
                print(f"Vision blocked at ({x0}, {y0}) with type {cell.base_type}")
                return False
                
            # Check for secret doors
            if (cell.base_type == DungeonGenerator.SECRET and 
                not cell.metadata.get('discovered', False)):
                print(f"Secret door blocks vision at ({x0}, {y0})")
                return False
                
            # Update position using Bresenham's algorithm
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
                
            # Check if we've visited this position before (infinite loop prevention)
            if (x0, y0) in visited:
                print(f"Loop detected in LOS from {from_pos} to {to_pos}")
                return False
                
            # Check bounds
            if not (0 <= x0 < len(self.dungeon) and 0 <= y0 < len(self.dungeon[0])):
                return False
        
    def add_light_source(self, position):
        self.light_sources.append(position)
        
    def remove_light_source(self, position):
        if position in self.light_sources:
            self.light_sources.remove(position)
            

class DungeonState:
    def __init__(self, generator: DungeonGenerator):
        print("Initializing DungeonState")
        self.grid = self._convert_generator_output(generator)
        print(f"Grid initialized: {len(self.grid)}x{len(self.grid[0])}")
        self.rooms = generator.room
        self.doors = generator.doorList
        # Convert stairs to use position tuples
        self.stairs = [{
            'position': (stair['row'], stair['col']),
            'next_position': (stair['next_row'], stair['next_col']),
            'key': stair['key']
        } for stair in generator.stairs]
        print(f"Found {len(self.stairs)} stairs")
        
        # Initialize start position
        start_position = self.determine_start_position()
        
        # Set visibility and party position
        self.visibility = VisibilitySystem(self.grid, start_position)
        self.visibility.update_visibility()
        self.party_position = start_position
        print(f"DungeonState initialized with grid size: {len(self.grid)}x{len(self.grid[0])}")

        # Mark starting cell as explored
        start_cell = self.get_cell(*start_position)
        if start_cell:
            start_cell.visibility['explored'] = True
            start_cell.visibility['visible'] = True

    def get_cell(self, x: int, y: int) -> DungeonCell:
        """Get cell at position (x, y)"""
        if self.is_valid_position((x, y)):
            return self.grid[x][y]
        return None

    @property
    def height(self):
        return len(self.grid)

    @property
    def width(self):
        return len(self.grid[0]) if self.grid else 0

    def discover_secrets(self, position, discovery_type="search"):
        """Discover secrets at a position"""
        x, y = position
        if self.is_valid_position(position):
            return self.grid[x][y].reveal_secret(discovery_type)
        return False

    def determine_start_position(self):
        """Find the best starting position based on stairs"""
        # Find first down stair in our new stair format
        start_position = None
        for stair in self.stairs:
            if stair['key'] == 'down':
                start_position = stair['position']
                break
        
        # If no down stairs, use first stairs
        if not start_position and self.stairs:
            start_position = self.stairs[0]['position']
        
        # Default to center if no stairs
        if not start_position:
            return (len(self.grid)//2, len(self.grid[0])//2)
        
        # Position just beyond stairs if possible
        for stair in self.stairs:  # Use self.stairs here!
            if stair['position'] == start_position:
                # Use next_position from our new stair structure
                next_pos = stair['next_position']
                if self.is_valid_position(next_pos):
                    return next_pos
                break
        
        print(f"Final start position: {start_position}")
        return start_position

    def is_valid_position(self, position: Tuple[int, int]) -> bool:
        """Check if position is traversable"""
        try:
            x, y = position
            # Check bounds
            if x < 0 or x >= len(self.grid) or y < 0 or y >= len(self.grid[0]):
                return False
                
            # Check cell type
            cell = self.grid[x][y]
            return bool(cell.current_type & (DungeonGenerator.ROOM | DungeonGenerator.CORRIDOR))
        except Exception as e:
            print(f"Position validation error at {position}: {str(e)}")
            return False


    def search_cell(self, position, search_skill=0):
        """Search a cell with chance-based discovery"""
        if not self.is_valid_position(position):
            return False, "Invalid position", []
        
        cell = self.grid[position[0]][position[1]]
        
        # Can only search once per cell
        if cell.searched:
            return False, "Already searched this area", []
        
        cell.searched = True
        found_items = []
        
        # Base chance to find obvious items
        for item_id in cell.items:
            found_items.append(item_id)
        
        # Chance to find hidden items
        if random.randint(1, 20) + search_skill >= cell.search_difficulty:
            # Add hidden items if any
            pass
        
        # Clear found items from cell
        for item_id in found_items:
            cell.remove_item(item_id)
        
        # Generate discovery message
        if found_items:
            items_desc = ", ".join([self.game_state.items[item_id]['name'] for item_id in found_items])
            return True, f"You found: {items_desc}", found_items
        return True, "You find nothing of interest", []

    def move_party(self, direction: str) -> Tuple[bool, str]:
        """Move party in specified direction with validation"""
        try:
            # Initialize party position if needed
            if not hasattr(self, 'party_position'):
                if self.stairs:
                    self.set_party_position(self.stairs[0]['position'])
                    return True, "Party positioned at entrance"
                return False, "No starting position available"
            
            x, y = self.party_position
            new_position = None
            
            # Calculate new position based on direction
            direction = direction.lower()
            if direction == 'north': new_position = (x-1, y)
            elif direction == 'south': new_position = (x+1, y)
            elif direction == 'west': new_position = (x, y-1)
            elif direction == 'east': new_position = (x, y+1)
            else:
                return False, f"Invalid direction: {direction}"
            
            # Validate movement
            if not self.is_valid_position(new_position):
                return False, f"Cannot move to {new_position}"
            
            cell = self.grid[new_position[0]][new_position[1]]
            
            # Check if cell is blocked
            if cell.current_type & (DungeonGenerator.BLOCKED | DungeonGenerator.PERIMETER):
                return False, "Path blocked"
            
            # Handle doors
            if cell.current_type & DungeonGenerator.DOORSPACE:
                door_type = self.get_door_type(cell.current_type)
                if door_type in ['locked', 'secret']:
                    return False, f"{door_type.capitalize()} door blocks your path"
            
            # Update position and visibility
            self.set_party_position(new_position)
            
            # Mark as explored
            cell.visibility['explored'] = True
            
            return True, f"Moved {direction} to {self.get_room_description(new_position)}"
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Movement error: {str(e)}"
        
    def set_party_position(self, new_position):
        """Update party position and visibility"""
        print(f"Moving party to {new_position}")
        self.party_position = new_position
        if hasattr(self, 'visibility') and self.visibility:
            self.visibility.party_position = new_position
            self.visibility.light_sources = [new_position]
            self.visibility.update_visibility()       # Update cell flags
            
        # Mark new position as explored
        new_cell = self.get_cell(*new_position)
        if new_cell:
            new_cell.visibility['explored'] = True
            new_cell.visibility['visible'] = True

    def get_door_type(self, cell_value):
        if cell_value & self.LOCKED: return 'locked'
        if cell_value & self.SECRET: return 'secret'
        if cell_value & self.TRAPPED: return 'trapped'
        if cell_value & self.ARCH: return 'arch'
        return 'door'
        
    def _convert_generator_output(self, generator):
        """Convert generator output to enhanced cells with validation"""
        grid = []
        for x in range(len(generator.cell)):
            row = []
            for y in range(len(generator.cell[0])):
                # Add validation during cell creation
                cell_value = generator.cell[x][y]
                if not isinstance(cell_value, int):
                    print(f"WARNING: Invalid cell value at ({x},{y}): {cell_value}")
                    cell_value = DungeonGenerator.NOTHING
                    
                cell = DungeonCell(cell_value, x, y)
                
                # Verify initialization
                if not hasattr(cell, 'current_type'):
                    print(f"CRITICAL: DungeonCell at ({x},{y}) has no current_type!")
                    cell.current_type = DungeonGenerator.NOTHING

                # Store door information
                if cell.base_type & DungeonGenerator.DOORSPACE:
                    door_type = self.get_door_type(cell.base_type)
                    #print(f"Door at ({x},{y}): {door_type}")
                    
                row.append(cell)
            grid.append(row)
        return grid

    def get_room_description(self, position: Tuple[int, int]) -> str:
        """Get description of a room at given position"""
        room_id = self.get_current_room_id(position)
        if room_id and room_id in self.rooms:
            return self.rooms[room_id].get('description', 'A mysterious room')
        
        # Fallback description
        cell_type = self.grid[position[0]][position[1]].base_type
        if cell_type == DungeonGenerator.ROOM:
            return "A stone chamber"
        elif cell_type == DungeonGenerator.CORRIDOR:
            return "A narrow passageway"
        return "An unknown area"
        
    def add_feature(self, position, feature_type, data=None):
        x, y = position
        self.grid[x][y].add_feature(feature_type, data)
        self.modification_history.append(('add_feature', position, feature_type))
        
    def transform_cell(self, position, new_type):
        x, y = position
        self.grid[x][y].transform(new_type)
        self.modification_history.append(('transform', position, new_type))
        
    def reveal_secrets(self, position):
        x, y = position
        self.grid[x][y].reveal_secret()
        self.modification_history.append(('reveal', position))

    def get_puzzle_hints(self, puzzle_id: str) -> List[Dict[str, Any]]:
        """Get hints for a puzzle across the entire dungeon"""
        hints = []
        for row in self.grid:
            for cell in row:
                for obj in cell.objects:
                    if obj.get('type') == 'puzzle' and obj.get('puzzle_id') == puzzle_id:
                        hints.extend(obj.get('hints', []))
        return hints

    def get_puzzle_data(self, puzzle_id: str) -> Dict[str, Any]:
        """Get complete puzzle data including hints"""
        for row in self.grid:
            for cell in row:
                for obj in cell.objects:
                    if obj.get('type') == 'puzzle' and obj.get('puzzle_id') == puzzle_id:
                        return {
                            'description': obj['description'],
                            'success_effect': obj['success_effect'],
                            'hints': obj.get('hints', [])
                        }
        return {
            'description': f"Unknown puzzle {puzzle_id}",
            'success_effect': "Something happens",
            'hints': []
        }

# Enhanced with AI integration
class EnhancedDungeonState(DungeonState):
    def __init__(self, generator):
        print("Initializing EnhancedDungeonState")
        self.generator = generator
        self.theme = generator.opts.get('theme', 'dungeon')
        self.dynamic_features = {}
        self.quest_items = {}
        self.ai_notes = {}  # For DM's private notes about areas
        self.puzzles = {}   # Add this line to initialize puzzles dictionary

        # Manually initialize what we need
        self.grid = generator.cell
        self.rooms = generator.room
        self.doors = generator.doorList
        self.stairs = generator.stairList
        start_position = self.determine_start_position()
        
        # Initialize visibility system
        self.visibility = VisibilitySystem(self.grid, start_position)
        self.visibility.update_visibility()
        self.party_position = start_position
        
        # DEBUG: Verify grid content
        print(f"EnhancedDungeonState initialized with grid size: {len(self.grid)}x{len(self.grid[0]) if self.grid else 'N/A'}")
        self.validate_grid()

    def get_cell_appearance(self, cell, debug_show_all=False):
        """Determine how a cell should appear based on state"""
        if debug_show_all:
            return cell.base_type, True, True
            
        # Handle secret doors - return BLOCKED if undiscovered
        if (cell.base_type == DungeonGenerator.SECRET and 
            not getattr(cell, 'discovered', False)):
            effective_type = DungeonGenerator.BLOCKED
        else:
            effective_type = cell.current_type
            
        visibility = cell.visibility
        return effective_type, visibility['explored'], visibility['visible']

    def update_effect_timers(self):
        """Update effect durations (called on each render)"""
        for row in self.grid:
            for cell in row:
                new_effects = []
                for effect in cell.temporary_effects:
                    # Simplified without animation for now
                    if 'duration' in effect:
                        effect['duration'] -= 0.1
                        if effect['duration'] > 0:
                            new_effects.append(effect)
                    else:
                        new_effects.append(effect)
                cell.temporary_effects = new_effects

    def break_door(self, position):
        x, y = position
        cell = self.get_cell(x, y)
        if cell and cell.base_type in [DungeonGenerator.DOOR, DungeonGenerator.LOCKED]:
            cell.add_modification('broken_door')
            cell.current_type = DungeonGenerator.ARCH
            
    def reveal_secret(self, position):
        x, y = position
        cell = self.get_cell(x, y)
        if cell and cell.base_type == DungeonGenerator.SECRET:
            cell.discovered = True
            
    def add_rubble(self, position):
        x, y = position
        cell = self.get_cell(x, y)
        if cell:
            cell.add_modification('rubble')
            
    def add_bloodstain(self, position):
        x, y = position
        cell = self.get_cell(x, y)
        if cell:
            cell.add_modification('bloodstain')
            
    def add_shiny_spot(self, position):
        x, y = position
        cell = self.get_cell(x, y)
        if cell:
            cell.add_effect('shiny_spot', 10)  # 10-second effect

    def get_cell(self, x: int, y: int) -> DungeonCell:
        """Get cell at position (x, y)"""
        if self.is_valid_position((x, y)):
            return self.grid[x][y]
        return None

    @property
    def height(self):
        return len(self.grid)

    @property
    def width(self):
        return len(self.grid[0]) if self.grid else 0

    def validate_grid(self):
        """Check all cells for required attributes"""
        errors = []
        for x in range(len(self.grid)):
            for y in range(len(self.grid[0])):
                cell = self.grid[x][y]
                if not hasattr(cell, 'current_type'):
                    errors.append(f"Cell ({x},{y}) missing current_type")
                elif not isinstance(cell.current_type, int):
                    errors.append(f"Cell ({x},{y}) has invalid current_type: {type(cell.current_type)}")
        
        if errors:
            print(f"GRID VALIDATION FAILED: {len(errors)} errors")
            for e in errors[:5]:  # Print first 5 errors
                print(e)
        else:
            print("Grid validation passed")
            
        return not errors

    def render_to_web(self, visible_only=True) -> dict:
        """Render dungeon for web interface with visibility control"""
        grid_data = []
        visible_cells = self.visibility.get_visible_cells() if visible_only else None
        
        for x in range(len(self.grid)):
            row = []
            for y in range(len(self.grid[0])):
                cell = self.grid[x][y]
                visibility = self.visibility.get_visibility((x, y))
                
                # Only show visible cells if enabled
                if visible_only:
                    if not visibility['visible'] and not visibility['explored']:
                        continue  # Skip completely hidden cells
                    
                cell_data = {
                    'x': x,
                    'y': y,
                    'base_type': cell.base_type,
                    'current_type': cell.current_type,
                    'explored': visibility['explored'],
                    'visible': visibility['visible'],
                    'features': cell.features,
                    'room_id': self.get_current_room_id((x, y))
                }
                row.append(cell_data)
            grid_data.append(row)
        
        # Create legend
        legend = {
            'room': 'Room',
            'corridor': 'Corridor',
            'door': 'Door',
            'stairs': 'Stairs',
            'wall': 'Wall'
        }
        
        return {
            'grid': grid_data,
            'party_position': self.party_position,
            'legend': legend,
            'width': len(self.grid[0]),
            'height': len(self.grid)
        }

    def render_to_image(self, cell_size=18, grid_color=DungeonColors.GRID, debug_show_all=False):
        """Render dungeon with visibility control"""
        print(f"Starting render: reveal_all={debug_show_all}")
        print("Render to image method called here........................")
        try:
            # Calculate dimensions
            width = len(self.grid[0]) * cell_size
            height = len(self.grid) * cell_size
            img = Image.new('RGB', (width, height), DungeonColors.BACKGROUND)
            draw = ImageDraw.Draw(img)
            
            # Debug: Count different cell types
            cell_type_counts = {
                "NOTHING": 0,
                "ROOM": 0,
                "CORRIDOR": 0,
                "DOOR": 0,
                "STAIRS": 0,
                "OTHER": 0
            }

            # Analytics counters
            stats = {
                'total': 0,
                'explored': 0,
                'visible': 0,
                'drawn_visible': 0,
                'drawn_explored': 0,
                'not_drawn': 0
            }

            for x in range(len(self.grid)):
                for y in range(len(self.grid[0])):
                    cell = self.grid[x][y]
                    pos = (x, y)
                    stats['total'] += 1
                    # Always count cell types for debugging
                    if cell.base_type & DungeonGenerator.STAIRS:
                        cell_type_counts["STAIRS"] += 1
                    elif cell.base_type & DungeonGenerator.DOORSPACE:
                        cell_type_counts["DOOR"] += 1
                    elif cell.base_type & DungeonGenerator.ROOM:
                        cell_type_counts["ROOM"] += 1
                    elif cell.base_type & DungeonGenerator.CORRIDOR:
                        cell_type_counts["CORRIDOR"] += 1
                    elif cell.base_type == DungeonGenerator.NOTHING:
                        cell_type_counts["NOTHING"] += 1
                    else:
                        cell_type_counts["OTHER"] += 1

                    # Get cell appearance based on state
                    effective_type, explored, visible = self.get_cell_appearance(cell, debug_show_all)

                    # Calculate drawing positions
                    x_pos = y * cell_size
                    y_pos = x * cell_size
                    
                    # handle visibility
                    if visible or debug_show_all:
                        # Draw with full detail using effective_type
                        self.draw_visible_cell(draw, x_pos, y_pos, cell_size, cell, effective_type)
                    elif explored:
                        # Draw as explored (grayed out)
                        self.draw_explored_cell(draw, x_pos, y_pos, cell_size, cell)
                    else:
                        # Unexplored - skip or draw as void
                        pass

            # Print analytics
            print("\n==== RENDERING ANALYTICS ====")
            print(f"Total cells: {stats['total']}")
            print(f"Explored cells: {stats['explored']} ({stats['explored']/stats['total']:.1%})")
            print(f"Visible cells: {stats['visible']} ({stats['visible']/stats['total']:.1%})")
            print(f"Drawn as visible: {stats['drawn_visible']}")
            print(f"Drawn as explored: {stats['drawn_explored']}")
            print(f"Not drawn: {stats['not_drawn']}")
            print("============================\n")
            
            # Print summary of cell types
            print("\n==== CELL TYPE SUMMARY ====")
            for k, v in cell_type_counts.items():
                print(f"{k}: {v}")
            print(f"Total cells: {len(self.grid)*len(self.grid[0])}")
            print("===========================\n")
            
            # Add grid lines
            if grid_color:
                self.draw_grid(draw, width, height, cell_size, grid_color)
                
            return img

        except Exception as e:
            # Create error image with diagnostic information
            error_img = Image.new('RGB', (800, 600), (255, 200, 200))
            draw = ImageDraw.Draw(error_img)
            print(f"Rendering Error {str(e)}")
            draw.text((10, 10), f"Rendering Error: {str(e)}", fill=(0, 0, 0))
            
            debug_info = [
                f"Grid size: {len(self.grid)}x{len(self.grid[0]) if self.grid else 'N/A'}",
                f"First cell type: {type(self.grid[0][0]) if self.grid and self.grid[0] else 'N/A'}",
                f"First cell has 'current_type': {hasattr(self.grid[0][0], 'current_type') if self.grid and self.grid[0] else 'N/A'}",
                f"Stairs count: {len(self.stairs)}",
                f"First stair: {self.stairs[0] if self.stairs else 'N/A'}"
            ]
            
            y_pos = 40
            for info in debug_info:
                draw.text((10, y_pos), info, fill=(0, 0, 0))
                y_pos += 20
                
            return error_img

    def get_door_type_from_cell(self, cell):
        """Get door type directly from cell's current_type"""
        if cell.current_type & DungeonGenerator.ARCH: return 'arch'
        if cell.current_type & DungeonGenerator.LOCKED: return 'locked'
        if cell.current_type & DungeonGenerator.TRAPPED: return 'trapped'
        if cell.current_type & DungeonGenerator.SECRET: return 'secret'
        if cell.current_type & DungeonGenerator.PORTC: return 'portc'
        return 'door'

    def draw_visible_cell(self, draw, x, y, size, cell, effective_type):
        renderer = DungeonRenderer(cell_size=size)
        try:
            #print(f"🐛 DEBUG: Drawing door at ({cell.x},{cell.y})")
            # Base cell drawing (WORKS FINE)

            if effective_type & DungeonGenerator.ROOM:
                draw.rectangle([x, y, x+size, y+size], fill=DungeonColors.ROOM)  # White for rooms
            elif effective_type & DungeonGenerator.CORRIDOR:
                draw.rectangle([x, y, x+size, y+size], fill=DungeonColors.CORRIDOR)  # Light gray for corridors
            elif effective_type & DungeonGenerator.BLOCKED:
                draw.rectangle([x, y, x+size, y+size], fill=DungeonColors.WALL)     # Dark gray for walls
            if effective_type & DungeonGenerator.DOORSPACE:
                door_type = self.get_door_type_from_cell(cell)
                orientation = self.get_door_orientation(x//size, y//size)
                renderer.draw_door(draw, x, y, door_type, orientation)

            # ADD MODIFICATION RENDERING HERE (AFTER BASE, BEFORE FEATURES)
            for mod in cell.modifications:
                self.draw_modification(draw, x, y, size, mod)
                
            # Existing feature drawing
            if cell.features:
                self.draw_features(draw, x, y, size, cell.features)
            
            # Add effect rendering here
            for effect in cell.temporary_effects:
                self.draw_effect(draw, x, y, size, effect)                

            # Draw other features (water, rubble, etc.)
            if cell.features:
                self.draw_features(draw, x, y, size, cell.features)
            
            if effective_type & DungeonGenerator.STAIRS:
                for stair in self.stairs:
                    if (cell.x, cell.y) == stair['position']:
                        dr = stair['next_position'][0] - cell.x
                        dc = stair['next_position'][1] - cell.y
                        orientation = 'horizontal' if abs(dc) > abs(dr) else 'vertical'
                        renderer.draw_stairs(draw, x, y, stair['key'], orientation)

            # Draw labels LAST so they're on top
            if cell.current_type & DungeonGenerator.LABEL:
                self.draw_label(draw, x, y, size, cell)
            
        except Exception as e:
            print(f"Error drawing cell at ({cell.x},{cell.y}): {str(e)}")
            draw.rectangle([x, y, x+size, y+size], fill=(255, 0, 0))
            draw.text((x+5, y+5), "ERR", fill=(0, 0, 0))


    def draw_label(self, draw, x, y, size, cell):
        """Draw cell label if present"""
        char = self.cell_label(cell.current_type)
        if char:
            # Use a basic font
            try:
                from PIL import ImageFont
                font = ImageFont.load_default()
            except ImportError:
                font = None
            
            text_x = x + size // 2
            text_y = y + size // 2
            draw.text((text_x, text_y), char, fill=DungeonColors.STAIRS, 
                     font=font, anchor="mm")

    def cell_label(self, cell_value):
        """Extract character label from cell"""
        char_code = (cell_value >> 24) & 0xFF
        return chr(char_code) if 32 <= char_code <= 126 else None

    def draw_explored_cell(self, draw, x, y, size, cell): # I don't understand what this is doing. If it is explored, shouldn't it be visible?
        """Draw an explored but not currently visible cell"""
        print(f"Drawing explored cell at grid position: ({x//size}, {y//size})")
        # Grayed out version
        draw.rectangle([x, y, x+size, y+size], fill=(100, 100, 100))
        
        # Add subtle indicators
        if cell.current_type & DungeonGenerator.STAIRS:
            # Small stair indicator
            center_x = x + size // 2
            center_y = y + size // 2
            draw.rectangle([center_x-2, center_y-2, center_x+2, center_y+2], fill=(100, 100, 100))
        elif cell.current_type & DungeonGenerator.DOOR:
            # Small door indicator
            center_x = x + size // 2
            center_y = y + size // 2
            draw.rectangle([center_x-4, center_y-1, center_x+4, center_y+1], fill=(100, 100, 100))

    def draw_grid(self, draw, width, height, cell_size, color):
        """Draw grid lines"""
        # Horizontal lines
        for r in range(0, len(self.grid) + 1):
            y_pos = r * cell_size
            draw.line([0, y_pos, width, y_pos], fill=color, width=1)
        
        # Vertical lines
        for c in range(0, len(self.grid[0]) + 1):
            x_pos = c * cell_size
            draw.line([x_pos, 0, x_pos, height], fill=color, width=1)

    def draw_modification(self, draw, x, y, size, mod):
        if mod['type'] == 'broken_door':
            # Draw broken door fragments
            center_x = x + size//2
            center_y = y + size//2
            for i in range(5):
                px = center_x + random.randint(-6, 6)
                py = center_y + random.randint(-6, 6)
                draw.rectangle([px, py, px+3, py+3], fill=(101, 67, 33))
                
        elif mod['type'] == 'rubble':
            # Draw rubble pieces
            for i in range(8):
                rx = x + random.randint(2, size-6)
                ry = y + random.randint(2, size-6)
                draw.rectangle([rx, ry, rx+4, ry+4], fill=(120,120,120))
                
        elif mod['type'] == 'bloodstain':
            # Draw blood splatter
            center_x, center_y = x+size//2, y+size//2
            for i in range(5):
                angle = random.uniform(0, 6.28)
                dist = random.randint(2, size//4)
                px = int(center_x + math.cos(angle)*dist)
                py = int(center_y + math.sin(angle)*dist)
                radius = random.randint(2,4)
                draw.ellipse([px-radius, py-radius, px+radius, py+radius],
                            fill=(150,10,10))
    
    def draw_effect(self, draw, x, y, size, effect):
        if effect['type'] == 'shiny_spot':
            # Draw static shiny effect (no animation for now)
            center_x, center_y = x+size//2, y+size//2
            for i in range(3):
                draw.ellipse([center_x-3-i, center_y-3-i,
                             center_x+3+i, center_y+3+i],
                             outline=(255,255,200))

    def get_door_type(self, cell_value):
        """Get door type from cell flags"""
        if cell_value & DungeonGenerator.ARCH: return 'arch'
        if cell_value & DungeonGenerator.LOCKED: return 'locked'
        if cell_value & DungeonGenerator.TRAPPED: return 'trapped'
        if cell_value & DungeonGenerator.SECRET: return 'secret'
        if cell_value & DungeonGenerator.PORTC: return 'portc'
        return 'door'

    def is_open_space(self, x, y):
        """Check if cell is open space"""
        if not self.is_valid_position((x, y)):
            return False
        cell = self.grid[x][y]
        return bool(self.current_type & (DungeonGenerator.ROOM | DungeonGenerator.CORRIDOR))


    def generate_legend_icons(self, icon_size=30):
        """Generate consistent legend icons using our drawing methods"""
        icons = {}
        elements = [
            'room', 'corridor', 'arch', 'open_door', 'locked_door',
            'trapped_door', 'secret_door', 'portcullis', 
            'stairs_up', 'stairs_down'
        ]
        
        for element in elements:
            icons[element] = self.create_legend_icon(element, icon_size)
        
        return icons

    def create_legend_icon(self, element_type, size):
        """Create a single legend icon"""
        img = Image.new('RGB', (size, size), (52, 73, 94))
        draw = ImageDraw.Draw(img)
        
        # Draw cell background
        margin = 1
        draw.rectangle([margin, margin, size-margin-1, size-margin-1], 
                      fill=(255, 255, 255))
        
        # Calculate centered drawing area
        scale_factor = 0.8
        scaled_size = int(size * scale_factor)
        x_offset = (size - scaled_size) // 2
        y_offset = (size - scaled_size) // 2
        
        # Draw element using our unified drawing methods
        if element_type == 'room':
            # Simple room representation
            draw.rectangle([
                x_offset + scaled_size//4, 
                y_offset + scaled_size//4,
                x_offset + 3*scaled_size//4,
                y_offset + 3*scaled_size//4
            ], outline=(0, 0, 0))
        
        elif element_type == 'corridor':
            # Simple corridor line
            draw.line([
                x_offset + scaled_size//4, 
                y_offset + scaled_size//2,
                x_offset + 3*scaled_size//4,
                y_offset + scaled_size//2
            ], fill=(0, 0, 0), width=2)
        
        elif element_type == 'arch':
            self.draw_door(draw, x_offset, y_offset, scaled_size, 'arch', 'horizontal')
        elif element_type == 'open_door':
            self.draw_door(draw, x_offset, y_offset, scaled_size, 'door', 'horizontal')
        elif element_type == 'locked_door':
            self.draw_door(draw, x_offset, y_offset, scaled_size, 'locked', 'horizontal')
        elif element_type == 'trapped_door':
            self.draw_door(draw, x_offset, y_offset, scaled_size, 'trapped', 'horizontal')
        elif element_type == 'secret_door':
            self.draw_door(draw, x_offset, y_offset, scaled_size, 'secret', 'horizontal')
        elif element_type == 'portcullis':
            self.draw_door(draw, x_offset, y_offset, scaled_size, 'portc', 'horizontal')
        elif element_type == 'stairs_up':
            self.draw_stairs(draw, x_offset, y_offset, scaled_size, 'up', 'horizontal')
        elif element_type == 'stairs_down':
            self.draw_stairs(draw, x_offset, y_offset, scaled_size, 'down', 'horizontal')
        
        return img

    def draw_features(self, draw, x, y, size, features):
        """Draw cell features (water, rubble, etc.)"""
        for feature in features:
            ftype = feature['type']
            if ftype == 'water':
                self.draw_water(draw, x, y, size)
            elif ftype == 'rubble':
                self.draw_rubble(draw, x, y, size)
            # Add more feature types as needed

    def draw_water(self, draw, x, y, size):
        """Draw water feature"""
        center_x = x + size // 2
        center_y = y + size // 2
        radius = size // 3
        draw.ellipse([
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius
        ], fill=(100, 100, 255), outline=(0, 0, 100))

    def draw_rubble(self, draw, x, y, size):
        """Draw rubble feature"""
        for i in range(5):
            rx = x + size * 0.2 + (i * size * 0.15)
            ry = y + size * 0.2 + (i * size * 0.15) % (size * 0.6)
            draw.rectangle([rx, ry, rx+size//8, ry+size//8], fill=(150, 150, 150))

    def draw_cell(self, draw, x, y, size, cell):
        """Draw a single cell based on its state"""
        # Calculate position
        x_pos = y * size
        y_pos = x * size
        
        # Determine color based on visibility
        if cell.visibility['visible']:
            fill = (255, 255, 255)  # Visible - white
        else:
            fill = (150, 150, 150)  # Explored but not visible - gray
        
        # Draw cell background
        draw.rectangle([x_pos, y_pos, x_pos+size, y_pos+size], fill=fill)
        
        # Draw cell features (doors, stairs, etc.)
        if cell.current_type & DungeonGenerator.DOOR:
            self.draw_door(draw, x_pos, y_pos, size)
        elif cell.current_type & DungeonGenerator.STAIRS:
            self.draw_stairs(draw, x_pos, y_pos, size, cell)
    
    def convert_to_generator_grid(self):
        """Convert state grid back to generator format with visibility"""
        grid = []
        for x in range(len(self.grid)):
            row = []
            for y in range(len(self.grid[0])):
                cell = self.grid[x][y]
                # Apply visibility masking
                if not cell.visibility['explored']:
                    row.append(DungeonGenerator.BLOCKED)
                elif not cell.visibility['visible']:
                    row.append(DungeonGenerator.PERIMETER)
                else:
                    row.append(cell.current_type)
            grid.append(row)
        return grid

    def add_puzzle(self, position, puzzle_data):
        """Register a puzzle created by the generator"""
        if not self.is_valid_position(position):
            return False
            
        self.puzzles[position] = puzzle_data
        return True
        
    def get_puzzle_at_position(self, position):
        """Get puzzle at a specific position, if any"""
        return self.puzzles.get(position)

    def get_current_room(self, position):
        """Get the room object at the given position"""
        room_id = self.get_current_room_id(position)
        if room_id is None:
            return None
            
        # Find the room by ID
        for room in self.rooms:
            if room['id'] == room_id:
                return room
        return None

    def get_current_room_id(self, position):
        """Get the ID of the room containing the given position"""
        x, y = position
        for room in self.rooms:
            if (room['north'] <= x <= room['south'] and 
                room['west'] <= y <= room['east']):
                return room['id']
        return None  # Position not in any room

    def get_room_description(self, position):
        """Get a description of the area at the given position"""
        room = self.get_current_room(position)
        if room:
            size = f"{room['width']}x{room['height']}"
            description = f"room {room['id']} ({size} feet)"
        else:
            # Describe corridor or other area
            cell = self.grid[position[0]][position[1]]
            if cell.base_type & DungeonGenerator.ROOM:
                description = "a mysterious chamber"
            elif cell.base_type & DungeonGenerator.CORRIDOR:
                description = "a stone corridor"
            elif cell.base_type & DungeonGenerator.STAIRS:
                description = "a stairwell"
            else:
                description = "an unknown area"
                
        # Check for puzzle
        if self.get_puzzle_at_position(position):
            description += " with a puzzling feature"
            
        return description
        
    def is_valid_position(self, position):
        """Check if position is within grid bounds"""
        x, y = position
        return (0 <= x < len(self.grid)) and (0 <= y < len(self.grid[0]))

    def add_feature(self, position, feature_type, data):
        if not self.is_valid_position(position):
            return False
            
        cell = self.grid[position[0]][position[1]]
        if not hasattr(cell, 'features'):
            cell.features = []
            
        cell.features.append({
            'type': feature_type,
            'data': data
        })
        return True
        
    def get_cell_features(self, position):
        """Get features at a specific position"""
        if not self.is_valid_position(position):
            return []
            
        cell = self.grid[position[0]][position[1]]
        return getattr(cell, 'features', [])
        
    def transform_cell(self, position, new_type):
        if not self.is_valid_position(position):
            return False
            
        self.grid[position[0]][position[1]]['base_type'] = new_type
        self.grid[position[0]][position[1]]['current_type'] = new_type
        return True
        
    def add_ai_note(self, position, note):
        """Add DM's private note about a location"""
        self.ai_notes[position] = note
        
    def populate_with_ai_content(self, ai_agent):
        """Use AI to populate dungeon with content"""
        # Add descriptive notes to special rooms
        for room in self.rooms:
            if room['id'] % 3 == 0:  # Every 3rd room gets special treatment
                note = ai_agent.generate_room_lore(room)
                self.add_ai_note(room['center'], note)
                
        # Place quest items
        for quest in self.game_state.active_quests.values():
            if quest['type'] == "fetch":
                item_room = random.choice(self.rooms)
                self.quest_items[item_room['id']] = quest['item_id']
        
    def break_door(self, position):
        x, y = position
        self.grid[x][y].break_door()
        self.modification_history.append(('break_door', position))
    
    def get_visible_area(self):
        """Get currently visible cells based on party position"""
        return self.visibility.get_visible_cells()