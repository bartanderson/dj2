#core\dungeon_standalone.py
#import random
from dungeon_neo.generator_neo import DungeonGeneratorNeo
from dungeon_neo.state_neo import DungeonStateNeo
#from dungeon_neo.renderer_neo import DungeonRendererNeo # below
from dungeon_neo.visibility_neo import VisibilitySystemNeo
from dungeon_neo.movement_service import MovementService
from dungeon_neo.ai_integration import DungeonAI

class DungeonSystem:
    def __init__(self):
        self.options = {
            #'seed': str(random.randint(1, 10000)),
            'seed': '123',#'None',
            'n_rows': 39,
            'n_cols': 39,
            'dungeon_layout': 'Standard',
            'room_min': 3,
            'room_max': 9,
            'room_layout': 'Scattered',
            'corridor_layout': 'Bent',
            'remove_deadends': 50,
            'add_stairs': 2,
            'map_style': 'Standard',
            'grid': 'Square'
        }
        self.generator = DungeonGeneratorNeo(self.options)
        self.state = None
        self.ai = None
    
    def generate(self, dungeon_type="cave"):
        try:
            self.options['dungeon_type'] = dungeon_type
            self.generator.options = self.options
            
            generator_result = self.generator.create_dungeon()
            if not generator_result:
                return False
            
            self.state = DungeonStateNeo(generator_result)
            self._set_initial_party_position()
            
            # CORE FIX: Initialize visibility system
            self.state.visibility_system = VisibilitySystemNeo(
                self.state.grid_system, 
                self.state.party_position
            )
            self.state.visibility_system.update_visibility()
            
            # CORE FIX: Initialize movement service
            self.state.movement = MovementService(self.state)
            
            return True
        except Exception as e:
            print(f"Dungeon generation failed: {str(e)}")
            return False

    def _set_initial_party_position(self):
        # 1. Try stairs with corrected offset
        if hasattr(self.state, 'stairs') and self.state.stairs:
            for stair in self.state.stairs:
                if stair.get('key') == 'up':
                    # NEGATIVE offset to move AWAY from stair
                    self.state.party_position = (
                        stair['y'] + stair.get('dy'),
                        stair['x'] + stair.get('dx')
                    )
                    return
        
        # 2. Try first room center
        if hasattr(self.state, 'rooms') and self.state.rooms:
            room = self.state.rooms[0]
            self.state.party_position = (
                (room['west'] + room['east']) // 2,
                (room['north'] + room['south']) // 2
            )
            return
        
        # 3. Fallback: find nearest open space to center
        center_x = self.state.grid_system.width // 2
        center_y = self.state.grid_system.height // 2
        for radius in range(0, max(self.state.width, self.state.height)):
            for dx in range(-radius, radius+1):
                for dy in range(-radius, radius+1):
                    x, y = center_x + dx, center_y + dy
                    if not (0 <= x < self.state.width and 0 <= y < self.state.height):
                        continue
                    cell = self.state.get_cell(x, y)
                    if cell and not cell.is_blocked:
                        self.state.party_position = (x, y)
                        return
    
    def get_image(self, debug=False):
        from dungeon_neo.renderer_neo import DungeonRendererNeo
        renderer = DungeonRendererNeo()
        try:
            # CORE FIX: Visibility system now always available
            return renderer.render(
                self.state, 
                debug_show_all=debug,
                visibility_system=self.state.visibility_system
            )
        except Exception as e:
            print(f"Rendering error: {str(e)}")
            return None
    
    def process_ai_command(self, command):
        # FIX: Lazy-load AI to avoid unnecessary dependencies
        if not self.ai:
            self.ai = DungeonAI(self.state)
        return self.ai.process_command(command)
    
    def reset_dungeon(self, dungeon_type="cave"):
        return self.generate(dungeon_type)