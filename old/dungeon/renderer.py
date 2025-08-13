from PIL import Image, ImageDraw
import math
import random

class DungeonRenderer:
    def __init__(self, cell_size=20):
        self.cell_size = cell_size
        self.colors = {
            'door': (139, 69, 19),      # Brown
            'arch': (160, 120, 40),     # Light brown
            'secret': (52, 73, 94),     # Dark blue-gray
            'locked': (101, 67, 33),    # Darker brown
            'trapped': (150, 10, 10),   # Blood red
            'portc': (80, 80, 80),      # Dark gray
            'stairs_up': (27, 174, 96), # Green
            'stairs_down': (231, 76, 60) # Red
        }
    
    def draw_door(self, draw, x, y, door_type, orientation):
        """Draw any door type with consistent styling"""
        is_horizontal = (orientation == 'horizontal')
        center_x = x + self.cell_size // 2
        center_y = y + self.cell_size // 2
        door_width = self.cell_size // 3
        arch_height = self.cell_size // 6
        outline_color = (0, 0, 0)
        
        # Draw arch for all visible doors except secrets
        if door_type != 'secret':
            if is_horizontal:
                draw.rectangle([
                    center_x - door_width//2, y,
                    center_x + door_width//2, y + arch_height
                ], fill=self.colors['arch'], outline=outline_color)
                draw.rectangle([
                    center_x - door_width//2, y + self.cell_size - arch_height,
                    center_x + door_width//2, y + self.cell_size
                ], fill=self.colors['arch'], outline=outline_color)
            else:
                draw.rectangle([
                    x, center_y - door_width//2,
                    x + arch_height, center_y + door_width//2
                ], fill=self.colors['arch'], outline=outline_color)
                draw.rectangle([
                    x + self.cell_size - arch_height, center_y - door_width//2,
                    x + self.cell_size, center_y + door_width//2
                ], fill=self.colors['arch'], outline=outline_color)

        # Draw door slab for appropriate types
        door_color = self.colors.get(door_type, self.colors['door'])
        if door_type in ['door', 'locked', 'trapped', 'portc']:
            if is_horizontal:
                draw.rectangle([
                    center_x - door_width//2, y + arch_height,
                    center_x + door_width//2, y + self.cell_size - arch_height
                ], fill=door_color, outline=outline_color)
            else:
                draw.rectangle([
                    x + arch_height, center_y - door_width//2,
                    x + self.cell_size - arch_height, center_y + door_width//2
                ], fill=door_color, outline=outline_color)

        # Add special symbols
        if door_type == 'locked':
            # Diamond lock symbol
            lock_size = self.cell_size // 6
            diamond = [
                (center_x, center_y - lock_size//2),
                (center_x + lock_size//2, center_y),
                (center_x, center_y + lock_size//2),
                (center_x - lock_size//2, center_y)
            ]
            draw.polygon(diamond, fill=(100, 100, 100), outline=outline_color)
        
        elif door_type == 'portc':
            # Portcullis bars
            bar_thickness = max(2, self.cell_size // 12)
            bar_count = 3
            bar_spacing = self.cell_size / (bar_count + 1)
            
            if is_horizontal:
                for i in range(1, bar_count + 1):
                    bar_y = y + i * bar_spacing
                    draw.rectangle([
                        center_x - door_width//2, bar_y - bar_thickness//2,
                        center_x + door_width//2, bar_y + bar_thickness//2
                    ], fill=(40, 40, 40))
            else:
                for i in range(1, bar_count + 1):
                    bar_x = x + i * bar_spacing
                    draw.rectangle([
                        bar_x - bar_thickness//2, center_y - door_width//2,
                        bar_x + bar_thickness//2, center_y + door_width//2
                    ], fill=(40, 40, 40))
        
        elif door_type == 'secret':
            # Cover with wall color
            draw.rectangle([x, y, x+self.cell_size, y+self.cell_size], 
                          fill=self.colors['secret'])
            # Add subtle indicator
            draw.line([
                (x + self.cell_size//4, y + self.cell_size//2),
                (x + 3*self.cell_size//4, y + self.cell_size//2)
            ], fill=(150, 150, 200), width=2)

    def draw_stairs(self, draw, x, y, stair_type, orientation):
        """Draw stairs with consistent styling"""
        step_count = 5
        spacing = self.cell_size / (step_count + 1)
        max_length = self.cell_size * 0.7
        step_color = (80, 80, 80)
        
        if orientation == 'horizontal':
            center_y = y + self.cell_size // 2
            for i in range(1, step_count + 1):
                if stair_type == 'down':
                    # Tapered for down stairs
                    length = max_length * (i / step_count)
                else:  # Up stairs
                    length = max_length
                
                x_pos = x + i * spacing
                draw.line([
                    x_pos, center_y - length//2,
                    x_pos, center_y + length//2
                ], fill=step_color, width=2)
        else:
            center_x = x + self.cell_size // 2
            for i in range(1, step_count + 1):
                if stair_type == 'down':
                    length = max_length * (i / step_count)
                else:  # Up stairs
                    length = max_length
                
                y_pos = y + i * spacing
                draw.line([
                    center_x - length//2, y_pos,
                    center_x + length//2, y_pos
                ], fill=step_color, width=2)
                
        # Add directional indicator
        arrow_size = self.cell_size // 8
        if stair_type == 'down':
            if orientation == 'horizontal':
                points = [
                    (x + self.cell_size - arrow_size, center_y),
                    (x + self.cell_size - arrow_size*2, center_y - arrow_size),
                    (x + self.cell_size - arrow_size*2, center_y + arrow_size)
                ]
            else:
                points = [
                    (center_x, y + self.cell_size - arrow_size),
                    (center_x - arrow_size, y + self.cell_size - arrow_size*2),
                    (center_x + arrow_size, y + self.cell_size - arrow_size*2)
                ]
            draw.polygon(points, fill=(200, 0, 0))
    
    def generate_legend_icon(self, element_type, icon_size=30):
        """Generate consistent legend icon"""
        img = Image.new('RGB', (icon_size, icon_size), (52, 73, 94))
        draw = ImageDraw.Draw(img)
        
        # Draw cell background
        margin = 1
        draw.rectangle([margin, margin, icon_size-margin-1, icon_size-margin-1], 
                      fill=(255, 255, 255))
        
        # Draw element
        if element_type == 'arch':
            self.draw_door(draw, 0, 0, 'arch', 'horizontal')
        elif element_type == 'open_door':
            self.draw_door(draw, 0, 0, 'door', 'horizontal')
        elif element_type == 'locked_door':
            self.draw_door(draw, 0, 0, 'locked', 'horizontal')
        elif element_type == 'trapped_door':
            self.draw_door(draw, 0, 0, 'trapped', 'horizontal')
        elif element_type == 'secret_door':
            self.draw_door(draw, 0, 0, 'secret', 'horizontal')
        elif element_type == 'portcullis':
            self.draw_door(draw, 0, 0, 'portc', 'horizontal')
        elif element_type == 'stairs_up':
            self.draw_stairs(draw, 0, 0, 'up', 'horizontal')
        elif element_type == 'stairs_down':
            self.draw_stairs(draw, 0, 0, 'down', 'horizontal')
            
        return img
    
    def generate_legend_icons(self, icon_size=30):
        """Generate all legend icons"""
        elements = [
            'arch', 'open_door', 'locked_door', 'trapped_door',
            'secret_door', 'portcullis', 'stairs_up', 'stairs_down'
        ]
        return {e: self.generate_legend_icon(e, icon_size) for e in elements}