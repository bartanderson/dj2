#dungeon_standalone.py
from dungeon_neo.grid_system import GridSystem
from dungeon_neo.state_neo import DungeonStateNeo
from dungeon_neo.movement_service import MovementService
from dungeon_neo.visibility_neo import VisibilitySystemNeo
from dungeon_neo.generator_neo import DungeonGeneratorNeo
from dungeon_neo.ai_integration import DungeonAI
import random

class DungeonSystem:
    def __init__(self):
        self.options = {
            'seed': str(random.randint(1, 10000)),
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
            # Update generator options
            self.options['dungeon_type'] = dungeon_type
            self.generator.options = self.options
            
            # Generate dungeon
            generator_result = self.generator.create_dungeon()
            if not generator_result:
                print("Generator returned empty result")
                return False
            
            # Create state
            self.state = DungeonStateNeo(generator_result)
            
            # Set initial position
            self._set_initial_party_position()
            
            # Initialize systems
            self.state.visibility_system = VisibilitySystemNeo(
                self.state.grid_system, 
                self.state.party_position
            )
            self.state.visibility_system.update_visibility()
            self.state.movement = MovementService(self.state)
            
            # Initialize AI
            self.ai = DungeonAI(self.state)
            
            print(f"Generated {dungeon_type} dungeon: {self.state.width}x{self.state.height}")
            print(f"Party starts at: {self.state.party_position}")
            return True
        except Exception as e:
            print(f"Dungeon generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _set_initial_party_position(self):
        # Place party near first up stair
        if hasattr(self.state, 'stairs') and self.state.stairs:
            for stair in self.state.stairs:
                if stair.get('key') == 'up':
                    self.state.party_position = (
                        stair['x'] + stair.get('dx', 0),
                        stair['y'] + stair.get('dy', 1)
                    )
                    print(f"Placed party at stairs position: {self.state.party_position}")
                    return
        
        # Fallback to center of first room
        if hasattr(self.state, 'rooms') and self.state.rooms:
            room = self.state.rooms[0]
            self.state.party_position = (
                (room['north'] + room['south']) // 2,
                (room['west'] + room['east']) // 2
            )
            print(f"Placed party in room center: {self.state.party_position}")
            return
        
        # Final fallback to dungeon center
        self.state.party_position = (
            self.state.grid_system.width // 2,
            self.state.grid_system.height // 2
        )
        print(f"Placed party at dungeon center: {self.state.party_position}")
    
    def get_image(self, debug=False):
        from dungeon_neo.renderer_neo import DungeonRendererNeo
        renderer = DungeonRendererNeo()
        try:
            return renderer.render(
                self.state, 
                debug_show_all=debug,
                visibility_system=self.state.visibility_system
            )
        except Exception as e:
            print(f"Rendering error: {str(e)}")
            return None
    
    def process_ai_command(self, command):
        if not self.ai:
            return {"success": False, "message": "AI not initialized"}
        try:
            return self.ai.process_command(command)
        except Exception as e:
            return {
                "success": False,
                "message": f"AI command processing failed: {str(e)}"
            }
    
    def reset_dungeon(self, dungeon_type="cave"):
        return self.generate(dungeon_type)