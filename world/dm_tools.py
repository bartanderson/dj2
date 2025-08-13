#from dungeon_neo.constants import CELL_FLAGS
from .entity import Entity
from .overlay import Overlay
from .tool_system import tool
import random
import json

class DMTools:
    def __init__(self, state):
        self.state = state

    #     # Directly import all flags from constants
    #     self.NOTHING = CELL_FLAGS['NOTHING']
    #     self.BLOCKED = CELL_FLAGS['BLOCKED']
    #     self.ROOM = CELL_FLAGS['ROOM']
    #     self.CORRIDOR = CELL_FLAGS['CORRIDOR']
    #     self.PERIMETER = CELL_FLAGS['PERIMETER']
    #     self.ENTRANCE = CELL_FLAGS['ENTRANCE']
    #     self.ROOM_ID = CELL_FLAGS['ROOM_ID']
    #     self.ARCH = CELL_FLAGS['ARCH']
    #     self.DOOR = CELL_FLAGS['DOOR']
    #     self.LOCKED = CELL_FLAGS['LOCKED']
    #     self.TRAPPED = CELL_FLAGS['TRAPPED']
    #     self.SECRET = CELL_FLAGS['SECRET']
    #     self.PORTC = CELL_FLAGS['PORTC']
    #     self.STAIR_DN = CELL_FLAGS['STAIR_DN']
    #     self.STAIR_UP = CELL_FLAGS['STAIR_UP']
    #     self.LABEL = CELL_FLAGS['LABEL']
    #     self.DOORSPACE = CELL_FLAGS['DOORSPACE']
    #     self.STAIRS = CELL_FLAGS['STAIRS']

    # # Helper functions
    # def success(self, message):
    #     return {"success": True, "message": message}
    
    # def fail(self, message):
    #     return {"success": False, "message": message}

    # @tool(
    #     name="move_party",
    #     description="Move the player party in a direction",
    #     direction="Direction to move (north, south, east, west, northeast, etc.)",
    #     steps="Number of steps (default=1)"
    # )
    # def move_party(self, direction: str, steps: int = 1) -> dict:
    #     """Move party with proper validation"""
    #     return self.state.movement.move_party(direction, steps)
    
    # def set_property(self, x, y, prop, value):
    #     cell = self.state.get_cell(x, y)
    #     if cell: cell.properties[prop] = value


    # # CELL TYPE MANAGEMENT
    # @tool(
    #     name="set_cell_type",
    #     description=("""
    #     1. USE 'create_door' FOR DOORS - NOT 'set_cell_type'
    #        - 'set_cell_type' only sets base types (room/corridor/blocked)
    #        - 'create_door' handles full door setup (position+orientation+type)

    #     2. DOOR CREATION STEPS:
    #        a) "Create arch at (5,5)" → create_door(5,5,arch)
    #        b) "Make door at (3,4) vertical" → create_door(3,4,vertical,normal)

    #     3. NEVER USE 'set_cell_type' FOR DOORS:
    #        - It cannot configure door-specific properties
    #        - Use 'create_door' or 'set_door_properties' instead

    #     4. EXAMPLE COMMANDS:
    #        - "Create secret door at (7,2)"
    #        - "Convert door at (5,8) to portcullis"
    #        - "Make vertical arch at (3,4)"
    #             ),
    #             x="X coordinate (number)",
    #             y="Y coordinate (number)",
    #             cell_type="room, corridor, blocked, door, stairs"
    #     """)
    # )
    # def set_cell_type(self, x: int, y: int, cell_type: str) -> dict:
    #     cell = self.state.get_cell(x, y)
    #     if not cell:
    #         return self.fail("Invalid coordinates")
        
    #     cell_type = cell_type.lower()
        
    #     # Validate type-specific rules
    #     if cell_type == "stairs":
    #         if not (cell.is_room or cell.is_corridor):
    #             return self.fail("Stairs can only replace room/corridor cells")
    #         if not self._is_at_corridor_end(x, y):
    #             return self.fail("Stairs must be at corridor dead ends")
        
    #     elif cell_type == "door":
    #         if not self._has_adjacent_open_space(x, y):
    #             return self.fail("Doors require adjacent open spaces")
        
    #     # Clear existing type flags
    #     cell.base_type &= ~(
    #         self.ROOM | 
    #         self.CORRIDOR | 
    #         self.BLOCKED | 
    #         self.DOORSPACE | 
    #         self.STAIRS
    #     )
        
    #     # Set new type
    #     type_map = {
    #         'room': self.ROOM,
    #         'corridor': self.CORRIDOR,
    #         'blocked': self.BLOCKED,
    #         'door': self.DOORSPACE,
    #         'stairs': self.STAIRS
    #     }
    #     cell.base_type |= type_map.get(cell_type, self.BLOCKED)
        
    #     # Special handling for stairs
    #     if cell_type == "stairs":
    #         self.state.stair_orientations[(x, y)] = 'horizontal'
        
    #     return self.success(f"Cell set to {cell_type} at ({x}, {y})")



    # # CREATE DOOR
    # @tool(
    #     name="create_door",
    #     description=(
    #         "CREATE a new door. Steps:"
    #         "1. Converts cell to door space"
    #         "2. Sets door properties"
    #         "3. Handles orientation"
    #         "Rules:"
    #         "• Requires adjacent open spaces (N/S/E/W must be room/corridor)"
    #         "• Secret doors start hidden"
    #         "• Arch doors are always passable"
    #     ),
    #     x="X coordinate (number)",
    #     y="Y coordinate (number)",
    #     orientation="horizontal or vertical",
    #     door_type="arch, normal, locked, trapped, secret, portc"
    # )
    # def create_door(self, x: int, y: int, orientation: str, door_type: str) -> dict:
    #     # First convert cell to door space
    #     cell_result = self.set_cell_type(x, y, "door")
    #     if not cell_result["success"]:
    #         return cell_result
        
    #     # Then set door properties
    #     return self.set_door_properties(x, y, orientation, door_type)

    # # DOOR PROPERTIES
    # @tool(
    #     name="set_door_properties",
    #     description=(
    #         "SET properties for EXISTING doors. Use after set_cell_type:"
    #         "1. 'arch': Open passage"
    #         "2. 'normal': Standard door"
    #         "3. 'locked': Requires key"
    #         "4. 'trapped': Contains trap"
    #         "5. 'secret': Hidden door"
    #         "6. 'portc': Portcullis gate"
    #         "Rules:"
    #         "• Only works on door cells"
    #         "• Orientation must match corridor direction"
    #     ),
    #     x="X coordinate (number)",
    #     y="Y coordinate (number)",
    #     orientation="horizontal or vertical",
    #     door_type="arch, normal, locked, trapped, secret, portc"
    # )
    # def set_door_properties(self, x: int, y: int, orientation: str, door_type: str) -> dict:
    #     cell = self.state.get_cell(x, y)
    #     if not cell:
    #         return self.fail("Invalid coordinates")
    #     if not cell.is_door:
    #         return self.fail("Only door cells can have door properties")
    #     if orientation not in ["horizontal", "vertical"]:
    #         return self.fail("Orientation must be horizontal or vertical")
        
    #     # Set orientation in state and cell
    #     self.state.door_orientations[(x, y)] = orientation
    #     cell.properties['orientation'] = orientation  # Add this line
        
    #     # Clear existing door flags
    #     cell.base_type &= ~(
    #         self.ARCH | 
    #         self.DOOR | 
    #         self.LOCKED | 
    #         self.TRAPPED | 
    #         self.SECRET | 
    #         self.PORTC
    #     )
        
    #     # Set new door type
    #     type_map = {
    #         'arch': self.ARCH,
    #         'normal': self.DOOR,
    #         'locked': self.LOCKED,
    #         'trapped': self.TRAPPED,
    #         'secret': self.SECRET,
    #         'portc': self.PORTC
    #     }
    #     if door_type not in type_map:
    #         return self.fail(f"Invalid door type: {door_type}")
        
    #     cell.base_type |= type_map[door_type]
        
    #     # Handle secret state
    #     if door_type == "secret":
    #         self.state.secret_mask[y][x] = False  # Start hidden
    #     else:
    #         self.state.secret_mask[y][x] = True  # Make visible
        
    #     return self.success(f"Set door to {door_type} ({orientation}) at ({x}, {y})")

    # # REVEAL SECRET (Fixed Implementation)
    # @tool(
    #     name="reveal_secret",
    #     description=(
    #         "Reveal a secret door. Rules: "
    #         "• Only works on cells with secret flag "
    #         "• Makes door visible and passable "
    #         "• Converts secret door to arch"
    #     ),
    #     x="X coordinate (number)",
    #     y="Y coordinate (number)"
    # )
    # def reveal_secret(self, x: int, y: int) -> dict:
    #     cell = self.state.get_cell(x, y)
    #     if not cell:
    #         return self.fail("Invalid coordinates")
    #     if not cell.is_secret:
    #         return self.fail("No secret door at this location")
        
    #     state = self.state.__class__
        
    #     # Update secret mask to reveal door
    #     self.state.secret_mask[y][x] = True
        
    #     # Convert to arch (passable)
    #     cell.base_type &= ~state.SECRET
    #     cell.base_type |= state.ARCH
        
    #     return self.success(f"Secret door revealed at ({x}, {y})")

    # # STAIRS ORIENTATION
    # @tool(
    #     name="set_stairs_orientation",
    #     description=(
    #         "Set stairs orientation. Rules: "
    #         "• Only valid for stairs at corridor ends "
    #         "• Orientation must match corridor direction "
    #         "• Up stairs face upward, down stairs face downward"
    #     ),
    #     x="X coordinate (number)",
    #     y="Y coordinate (number)",
    #     direction="up or down",
    #     orientation="horizontal or vertical"
    # )
    # def set_stairs_orientation(self, x: int, y: int, direction: str, orientation: str) -> dict:
    #     cell = self.state.get_cell(x, y)
    #     if not cell:
    #         return self.fail("Invalid coordinates")
    #     if not cell.is_stairs:
    #         return self.fail("Only stairs cells can have orientation set")
    #     if not self._is_at_corridor_end(x, y):
    #         return self.fail("Stairs must be at corridor dead ends")
    #     if orientation not in ["horizontal", "vertical"]:
    #         return self.fail("Orientation must be horizontal or vertical")
    #     if direction not in ["up", "down"]:
    #         return self.fail("Direction must be up or down")
        
    #     # Update stairs properties
    #     state = self.state.__class__
    #     if direction == "up":
    #         cell.base_type |= state.STAIR_UP
    #         cell.base_type &= ~state.STAIR_DN
    #     else:
    #         cell.base_type |= state.STAIR_DN
    #         cell.base_type &= ~state.STAIR_UP
            
    #     self.state.stair_orientations[(x, y)] = orientation
    #     return self.success(f"Set {direction} stairs to {orientation} at ({x}, {y})")

    # # HELPER METHODS
    # def _has_adjacent_open_space(self, x, y):
    #     """Check adjacent cells for room/corridor (door requirement)"""
    #     for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
    #         nx, ny = x + dx, y + dy
    #         cell = self.state.get_cell(nx, ny)
    #         if cell and (cell.is_room or cell.is_corridor):
    #             return True
    #     return False

    # def _is_at_corridor_end(self, x, y):
    #     """Check if position is at corridor end (stairs requirement)"""
    #     open_count = 0
    #     for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
    #         nx, ny = x + dx, y + dy
    #         cell = self.state.get_cell(nx, ny)
    #         if cell and not cell.is_blocked:
    #             open_count += 1
    #     return open_count == 1  # Dead end


    # @tool(
    #     name="modify_cell_flag",
    #     description=(
    #         "MODIFY specific cell flags. For advanced use:"
    #         "• Properties: arch, door, locked, trapped, secret, portc, stairs_up, stairs_down"
    #         "• Use 'true' to enable, 'false' to disable"
    #         "Example: Make a door trapped"
    #     ),
    #     x="X coordinate (number)",
    #     y="Y coordinate (number)",
    #     property="Specific property to modify",
    #     value="true or false"
    # )
    # def modify_cell_flag(self, x: int, y: int, property: str, value: str) -> dict:
    #     cell = self.state.get_cell(x, y)
    #     if not cell:
    #         return {"success": False, "message": "Invalid coordinates"}

    #     # Handle boolean values
    #     if value.lower() not in ['true', 'false']:
    #         return {"success": False, "message": "Value must be 'true' or 'false'"}
        
    #     bool_value = value.lower() == 'true'
        
    #     # Map property names to flags
    #     prop_to_flag = {
    #         'arch': self.ARCH,
    #         'door': self.DOOR,
    #         'locked': self.LOCKED,
    #         'trapped': self.TRAPPED,
    #         'secret': self.SECRET,
    #         'portc': self.PORTC,
    #         'stairs_up': self.STAIR_UP,
    #         'stairs_down': self.STAIR_DN
    #     }
        
    #     if property not in prop_to_flag:
    #         return {"success": False, "message": f"Invalid property: {property}"}
        
    #     flag = prop_to_flag[property]
        
    #     if bool_value:
    #         cell.base_type |= flag
    #     else:
    #         cell.base_type &= ~flag
            
    #     return {"success": True, "message": f"Set {property} to {value} at ({x}, {y})"}

    @tool(
        name="add_entity",
        description="Add an entity to a dungeon cell",
        x="X coordinate (number)",
        y="Y coordinate (number)",
        entity_type="Type of entity (npc, monster, item, trap, portal, chest, etc.)"
    )
    def add_entity(self, x: int, y: int, entity_type: str) -> dict:
        """Add entity to specified cell"""
        cell = self.state.get_cell(x, y)
        if not cell:
            return {"success": False, "message": "Invalid coordinates"}
            
        # Create entity with type
        entity = Entity(entity_type)
        cell.entities.append(entity)
        return {"success": True, "message": f"Added {entity_type} at ({x}, {y})"}
        
    @tool(
        name="describe_cell",
        description="Add a text description to a dungeon cell",
        x="X coordinate (number)",
        y="Y coordinate (number)",
        text="Description text"
    )
    def describe_cell(self, x: int, y: int, text: str) -> dict:
        """Add description to cell"""
        cell = self.state.get_cell(x, y)
        if not cell:
            return {"success": False, "message": "Invalid coordinates"}
        
        cell.description = text
        return {"success": True, "message": f"Added description to ({x}, {y})"}

    @tool(
        name="add_overlay",
        description="Add a primitive overlay to a cell",
        x="X coordinate (number)",
        y="Y coordinate (number)",
        primitive="Primitive type (circle, square, triangle, line, text, polygon)",
        color_r="Red component (0-255)",
        color_g="Green component (0-255)",
        color_b="Blue component (0-255)",
        parameters="JSON string of additional parameters (optional)"
    )
    def add_overlay(self, x: int, y: int, primitive: str, color_r: int, color_g: int, color_b: int, parameters: str = "{}") -> dict:
        """Add a primitive overlay to a cell"""
        import json
        cell = self.state.get_cell(x, y)
        if not cell:
            return {"success": False, "message": "Invalid coordinates"}
        
        try:
            # Parse additional parameters
            params = json.loads(parameters) if parameters else {}
        except json.JSONDecodeError:
            return {"success": False, "message": "Invalid parameters format"}
        
        # Create color tuple
        color = (color_r, color_g, color_b)
        
        # Create overlay with all parameters
        overlay_params = {"color": color, **params}
        cell.overlays.append(Overlay(primitive, **overlay_params))
        
        return {"success": True, "message": f"Added {primitive} overlay to ({x}, {y})"}
    
    # @tool(
    #     name="reset_dungeon",
    #     description="Generate a new dungeon"
    # )
    # def reset_dungeon(self) -> dict:
    #     """Reset the dungeon"""
    #     self.state.dungeon.generate()
    #     return {"success": True, "message": "Generated new dungeon"}

    # @tool(
    #     name="get_debug_grid",
    #     description="Get a text-based debug view of the dungeon"
    # )
    # def get_debug_grid(self) -> dict:
    #     """Get debug grid view"""
    #     grid = self.state.get_debug_grid()
    #     grid_str = "\n".join(grid)
        
    #     # Save to file
    #     filename = "dungeon_debug_grid.txt"
    #     with open(filename, 'w') as f:
    #         f.write(grid_str)
            
    #     return {
    #         "success": True,
    #         "message": f"Debug Grid saved to {filename}",
    #         "grid": grid,
    #         "filename": filename  # Return filename for download
    #     }