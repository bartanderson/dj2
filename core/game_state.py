from .dungeon import DungeonSystem

class GameState:
    def __init__(self):
        self.dungeon = DungeonSystem()
        self.dungeon.generate()  # Generate initial dungeon
    
    def move(self, direction):
        self.dungeon.move_party(direction)
    
    def get_dungeon_image(self, debug=False):
        img = self.dungeon.get_image(debug)
        
        if img.mode == 'RGBA':
            return img.convert('RGB')
        return img
    
    def get_current_room(self):
        return self.dungeon.get_current_room_description()

    def reset(self):
        self.dungeon.generate()