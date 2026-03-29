# core/dungeon.py - Merged Unified Version
import random
from dungeon_neo.generator_neo import DungeonGeneratorNeo
from dungeon_neo.state_neo import DungeonStateNeo
from dungeon_neo.renderer_neo import DungeonRendererNeo
from dungeon_neo.visibility_neo import VisibilitySystemNeo
from dungeon_neo.movement_service import MovementService
from dungeon_neo.ai_integration import DungeonAI

# DUNGEON SYSTEM COORDINATE CONTRACT
# ==================================
# ROLE: Adapter between generator-space (r,c) -> world-space (x,y)
# Conversion: x = c + dc, y = r + dr  (dc/dr = column/row delta to approach cell)
# WARNING: Contains intentional coordinate swaps. Do not "fix" without reading stair_ends().
# MAINTENANCE: Do not "normalize" coordinate usage without tracing full pipeline
#              See _set_initial_party_position() for stair adaptation logic

class DungeonSystem:
    """
    Unified dungeon system supporting both integrated and standalone usage.
    """
    
    DEFAULT_OPTIONS = {
        'seed': '42',
        'n_rows': 39,
        'n_cols': 39,
        'dungeon_layout': 'Standard',
        'room_min': 3,
        'room_max': 9,
        'room_layout': 'Scattered',
        'corridor_layout': 'Bent',
        'remove_deadends': 100,
        'add_stairs': 2,
        'map_style': 'Standard',
        'grid': 'Square',
        'dungeon_type': 'cave'
    }
    
    def __init__(self, options=None, enable_ai=False):
        """
        Initialize the dungeon system.
        
        Args:
            options: Dict of generation options (uses DEFAULT_OPTIONS if None)
            enable_ai: Whether to enable AI integration (lazy-loaded)
        """
        self.options = {**self.DEFAULT_OPTIONS, **(options or {})}
        self.generator = DungeonGeneratorNeo(self.options)
        self.renderer = None  # Lazy-loaded
        self.state = None
        self.visibility_system = None
        self.ai = None if not enable_ai else DungeonAI(self.state)
    
    def generate(self, dungeon_type=None):
        """
        Generate a new dungeon.
        
        Args:
            dungeon_type: Optional dungeon type override (e.g., 'cave', 'dungeon')
            
        Returns:
            bool: True if generation succeeded, False otherwise
        """
        try:
            if dungeon_type:
                self.options['dungeon_type'] = dungeon_type
            self.generator.options = self.options
            
            generator_result = self.generator.create_dungeon()
            if not generator_result:
                return False
            
            # Print diagnostics for disconnected rooms
            for diag in generator_result.get('diagnostics', []):
                if diag.get('failure_reason'):
                    print(f"Room {diag['room_id']} disconnected: {diag['failure_reason']}")
                    print(f"Rejected positions: {diag.get('rejected_sills', [])}")
            
            # Create state from generator result
            self.state = DungeonStateNeo(generator_result)
            
            # Set initial party position
            self._set_initial_party_position()
            
            # Initialize visibility system with actual position
            self.state.visibility_system = VisibilitySystemNeo(
                self.state.grid_system, 
                self.state.party_position
            )
            self.state.visibility_system.update_visibility()
            
            # Initialize movement service
            self.state.movement = MovementService(self.state)
            
            return True
            
        except Exception as e:
            print(f"Dungeon generation failed: {str(e)}")
            return False
    
    def _set_initial_party_position(self):
        """Set initial party position near first up stair, with fallbacks."""
        # 1. Try stairs first (most common case)
        if hasattr(self.state, 'stairs') and self.state.stairs:
            up_stairs = [s for s in self.state.stairs if s.get('key') == 'up']
            if up_stairs:
                stair = up_stairs[0]
                
                # ADAPTER SEAM: Convert generator-space (r,c) to world-space (x,y)
                # Generator: r=row (vertical), c=column (horizontal)
                # World: x=column (horizontal), y=row (vertical)
                # Party should stand in approach cell: (c + dc, r + dr)
                
                world_x = stair['c'] + stair.get('dc', 0)  # column + col_delta = horizontal
                world_y = stair['r'] + stair.get('dr', 0)  # row + row_delta = vertical
                
                # SAFETY CHECK: Ensure we're placing in passable space, not a wall
                cell = self.state.get_cell(world_x, world_y)
                if cell and (cell.is_corridor or cell.is_room):
                    self.state.party_position = (world_x, world_y)
                    return
                else:
                    # Fallback: search for any adjacent open space to the stair
                    # Try all 4 directions in world-space
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        check_x = stair['c'] + dx
                        check_y = stair['r'] + dy
                        check_cell = self.state.get_cell(check_x, check_y)
                        if check_cell and (check_cell.is_corridor or check_cell.is_room):
                            self.state.party_position = (check_x, check_y)
                            return
        
        # 2. Fallback to first room center
        if hasattr(self.state, 'rooms') and self.state.rooms:
            room = self.state.rooms[0]
            self.state.party_position = (
                (room['west'] + room['east']) // 2,
                (room['north'] + room['south']) // 2
            )
            return
        
        # 3. Final fallback: find nearest open space to center (spiral search)
        center_x = self.state.grid_system.width // 2
        center_y = self.state.grid_system.height // 2
        max_dim = max(self.state.width, self.state.height)
        
        for radius in range(max_dim):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    x, y = center_x + dx, center_y + dy
                    if not (0 <= x < self.state.width and 0 <= y < self.state.height):
                        continue
                    cell = self.state.get_cell(x, y)
                    if cell and not cell.is_blocked:
                        self.state.party_position = (x, y)
                        return
    
    def is_blocked_for_movement(self, cell):
        """
        Check if a cell blocks movement.
        
        Args:
            cell: The cell to check
            
        Returns:
            bool: True if movement is blocked
        """
        if cell.is_blocked:
            return True
        if cell.is_perimeter and not cell.is_door:
            return True
        if cell.is_door and not cell.is_arch:
            return True
        return False
    
    def get_image(self, debug=False):
        """
        Render the dungeon as an image.
        
        Args:
            debug: If True, show entire dungeon regardless of visibility
            
        Returns:
            Rendered image or None if rendering failed
        """
        try:
            # Lazy-load renderer
            if self.renderer is None:
                self.renderer = DungeonRendererNeo()
            
            return self.renderer.render(
                self.state, 
                debug_show_all=debug,
                visibility_system=self.state.visibility_system if self.state else None
            )
        except Exception as e:
            print(f"Rendering error: {str(e)}")
            return None
    
    def process_ai_command(self, command):
        """
        Process an AI command (lazy-loads AI if needed).
        
        Args:
            command: The command string to process
            
        Returns:
            Result of AI processing
        """
        if not self.ai:
            self.ai = DungeonAI(self.state)
        return self.ai.process_command(command)
    
    def reset_dungeon(self, dungeon_type=None):
        """
        Reset and regenerate the dungeon.
        
        Args:
            dungeon_type: Optional dungeon type for regeneration
            
        Returns:
            bool: True if regeneration succeeded
        """
        return self.generate(dungeon_type)