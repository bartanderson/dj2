from dungeon_neo.constants import DIRECTION_VECTORS_8
from .state_neo import DungeonStateNeo

class CharacterMovementService:
    def __init__(self, state: DungeonStateNeo):
        self.state = state
        
    def move_character(self, char, direction, steps=1):
        """Move individual character using core movement logic"""
        # Get character position
        x0, y0 = char.position
        
        # Calculate movement
        result = self.movement.calculate_movement(x0, y0, direction, steps)
        
        if result['success']:
            # Update character position
            char.position = result['new_position']
        
        return result

class MovementService:
    def __init__(self, state):
        self.state = state
        self.visibility = state.visibility_system if hasattr(state, 'visibility_system') else None
    
    @property
    def dungeon_state(self):
        return self.state

    @property
    def grid_system(self):
        """Access grid system through the proper path"""
        # For world map, use world_map.grid_system
        if hasattr(self.state, 'world_map'):
            return self.state.world_map.grid_system
        # For dungeon, use state.grid_system
        return self.state.grid_system

    def move(self, direction, steps=1):
        """Alias for move_party"""
        return self.move_party(direction, steps)

    def calculate_movement(self, start_x, start_y, direction, steps=1):
        """Core movement calculation without side effects - pure function"""
        dx, dy = DIRECTION_VECTORS_8.get(direction.lower(), (0, 0))
        if dx == 0 and dy == 0:
            return {
                "success": False,
                "message": f"Invalid direction: {direction}",
                "old_position": (start_x, start_y),
                "new_position": (start_x, start_y),
                "steps_moved": 0
            }
        
        x, y = start_x, start_y
        actual_steps = 0
        messages = []
        
        # Execute movement step-by-step
        for step in range(steps):
            new_x, new_y = x + dx, y + dy
            
            # Check if position is valid
            if not self.dungeon_state.grid_system.is_valid_position(new_x, new_y):
                messages.append(f"Cannot move to ({new_x}, {new_y}) - out of bounds")
                break
                
            # Get cell and check if passable
            cell = self.dungeon_state.get_cell(new_x, new_y)
            if not cell:
                messages.append(f"Invalid cell at ({new_x}, {new_y})")
                break
                
            if not self.is_passable(new_x, new_y):
                if cell.is_door or cell.is_secret or cell.is_trapped or cell.is_portc:
                    messages.append(f"Blocked by door at ({new_x}, {new_y})") 
                elif cell.is_stairs:
                    messages.append(f"Do you wish to take stairs at ({new_x}, {new_y})")
                else:
                    messages.append(f"Blocked at ({new_x}, {new_y})")
                break
                
            # Validate diagonal paths
            if direction in ['northeast', 'northwest', 'southeast', 'southwest']:
                # Check horizontal and vertical components
                if not (self.is_passable(x + dx, y) and self.is_passable(x, y + dy)):
                    messages.append(f"Diagonal path blocked to ({new_x}, {new_y})")
                    break
            
            # Move to next cell
            x, y = new_x, new_y
            actual_steps += 1
            messages.append(f"Moved {direction} to ({x}, {y})")
        
        return {
            "success": actual_steps > 0,
            "message": "\n".join(messages),
            "old_position": (start_x, start_y),
            "new_position": (x, y),
            "steps_moved": actual_steps
        }
    
    def move_party(self, direction, steps=1):
        """Move party with proper validation and visibility updates"""
        # Validate input
        if steps <= 0:
            return {"success": False, "message": "Invalid steps value"}
            
        if direction not in DIRECTION_VECTORS_8:
            return {"success": False, "message": f"Invalid direction: {direction}"}

        # Access the dungeon state
        dungeon_state = self.state
        
        # Get current position
        x0, y0 = dungeon_state.party_position
        
        # Validate current position
        if not dungeon_state.grid_system.is_valid_position(x0, y0):
            return {"success": False, "message": "Invalid starting position"}
        
        # Update visibility along the path BEFORE moving
        if dungeon_state.visibility_system:
            dungeon_state.visibility_system.update_visibility_directional(direction, steps)
        
        # Calculate movement
        result = self.calculate_movement(x0, y0, direction, steps)
        
        if result['success']:
            new_x, new_y = result['new_position']
            
            # Validate new position
            if not dungeon_state.grid_system.is_valid_position(new_x, new_y):
                return {"success": False, "message": "Movement would go out of bounds"}
            
            # Update final position
            dungeon_state.party_position = (new_x, new_y)
            
            # Update visibility system with new position
            if dungeon_state.visibility_system:
                dungeon_state.visibility_system.party_position = (new_x, new_y)
                dungeon_state.visibility_system.update_visibility()
        
        return result

    def is_passable(self, x: int, y: int) -> bool:
        """Check if a cell is passable for movement"""
        if not self.grid_system.is_valid_position(x, y):  # CHANGED
            return False
            
        cell = self.grid_system.get_cell(x, y)  # CHANGED
        if not cell:
            return False
            
        # Special cases
        if cell.is_stairs:
            return False
        if cell.is_secret and not self.state.secret_mask[y][x]:
            return False
        if cell.is_door:
            return cell.is_arch
            
        # Default passability
        return not (cell.is_blocked or cell.is_perimeter)
    
    def get_cell_type(self, x: int, y: int) -> str:
        """Get descriptive cell type"""
        if not self.grid_system.is_valid_position(x, y):  # CHANGED
            return "boundary"
            
        cell = self.grid_system.get_cell(x, y)  # CHANGED
        if not cell:
            return "void"
            
        if cell.is_blocked: return "blocked"
        if cell.is_perimeter: return "perimeter"
        if cell.is_room: return "room"
        if cell.is_corridor: return "corridor"
        if cell.is_door: 
            if cell.is_arch: return "archway"
            if cell.is_portc: return "portcullis"
            if cell.is_trapped: return "trapped door"
            if cell.is_locked: return "locked door"
            if cell.is_secret: return "secret door"
            else: return "unlocked door"
        if cell.is_stairs: return "stairs"
        return "unknown"