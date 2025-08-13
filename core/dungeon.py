# core\dungeon.py
import random
from dungeon_neo.generator_neo import DungeonGeneratorNeo
from dungeon_neo.state_neo import DungeonStateNeo
from dungeon_neo.renderer_neo import DungeonRendererNeo
from dungeon_neo.visibility_neo import VisibilitySystemNeo
from dungeon_neo.movement_service import MovementService

class DungeonSystem:
    
    DEFAULT_OPTIONS = {
            #'seed': str(random.randint(1, 10000)),
            'seed': '1',#'None',
            'n_rows': 39,
            'n_cols': 39,
            'dungeon_layout': 'None',
            'room_min': 3,
            'room_max': 9,
            'room_layout': 'Scattered',
            'corridor_layout': 'Bent',
            'remove_deadends': 100,
            'add_stairs': 2,
            'map_style': 'Standard',
            #'cell_size': 18, handled in renderer options
            'grid': 'Square'
        }
    
    def __init__(self, options=None):
        self.options = options or self.DEFAULT_OPTIONS
        self.generator = DungeonGeneratorNeo(self.options)
        self.renderer = DungeonRendererNeo()
        self.state = None  # Will be initialized after generation
        self.visibility_system = None  # Will be initialized after generation
    
    def generate(self):
        # Generate dungeon and get the result
        generator_result = self.generator.create_dungeon()
        
        for diag in generator_result['diagnostics']:
            if diag['failure_reason']:
                print(f"Room {diag['room_id']} disconnected: {diag['failure_reason']}")
                print(f"Rejected positions: {diag['rejected_sills']}")
        
        # Create state from generator result
        self.state = DungeonStateNeo(generator_result)
        
        # Set final party position FIRST
        self._set_initial_party_position()
        
        # THEN create visibility system with actual position
        self.state.visibility_system = VisibilitySystemNeo(
            self.state.grid_system, 
            self.state.party_position
        )
        
        # Update visibility immediately
        self.state.visibility_system.update_visibility()
        
        # Finally create movement service
        self.state.movement = MovementService(self.state)
        
        #print(f"Generated dungeon: {self.state.width}x{self.state.height}")
        #print(f"Initial party position: {self.state.party_position}")

    def _set_initial_party_position(self):
        """Set initial party position near first up stair"""
        # Find first up stair
        up_stairs = [stair for stair in self.state.stairs if stair.get('key') == 'up'] # find all the up stairs. You would come down them to be here.
        
        if not up_stairs:
            # Fallback to first room center
            if self.state.rooms:
                room = self.state.rooms[0]
                center_x = (room['north'] + room['south']) // 2
                center_y = (room['west'] + room['east']) // 2
                self.state.party_position = (center_x, center_y)
                return
            
            # Final fallback to dungeon center
            center_x = self.state.height // 2
            center_y = self.state.width // 2
            self.state.party_position = (center_x, center_y)
            return
        else:
            stair = up_stairs[0]
            party_y = stair['y'] + stair['dy']
            party_x = stair['x'] + stair['dx']
            self.state.party_position = (party_y, party_x)
                    
    def is_blocked_for_movement(self, cell):
        """Simplified blocking logic"""
        # Block all BLOCKED cells
        if cell.is_blocked:
            return True
            
        # Block all perimeter cells that aren't doors
        if cell.is_perimeter and not cell.is_door:
            return True
            
        # Block non-arch doors
        if cell.is_door and not cell.is_arch:
            return True
            
        return False
        
    def get_image(self, debug=False):
        # Simply pass the state directly to the renderer
        return self.renderer.render(
            self.state, 
            debug_show_all=debug,
            visibility_system=self.state.visibility_system
        )