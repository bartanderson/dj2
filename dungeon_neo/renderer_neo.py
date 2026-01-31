from PIL import Image, ImageDraw, ImageFont
from dungeon_neo.state_neo import DungeonStateNeo
from dungeon_neo.generator_neo import DungeonGeneratorNeo
from dungeon_neo.constants import CELL_FLAGS, DIRECTION_VECTORS, OPPOSITE_DIRECTIONS
from dungeon_neo.cell_neo import DungeonCellNeo
from dungeon_neo.overlay import Overlay

class DungeonRendererNeo:
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

    # Composite flags
    DOORSPACE = CELL_FLAGS['DOORSPACE']
    ESPACE = CELL_FLAGS['ESPACE']
    STAIRS = CELL_FLAGS['STAIRS']
    BLOCK_ROOM = CELL_FLAGS['BLOCK_ROOM']
    BLOCK_CORR = CELL_FLAGS['BLOCK_CORR']
    BLOCK_DOOR = CELL_FLAGS['BLOCK_DOOR']

    COLORS = {
        'room': (255, 255, 255),
        'corridor': (200, 200, 200),
        'blocked': (52, 73, 94),    # blocked
        'door': (101, 67, 33),      # Darker brown
        'arch': (160, 120, 40),     # Light brown
        'secret': (101, 67, 33),    # Darker brown
        'locked': (101, 67, 33),    # Darker brown
        'trapped': (101, 67, 33),   # Darker brown
        'portc': (10, 10, 10),      # Dark gray
        'stairs_up': (10, 10, 10),
        'stairs_down': (10, 10, 10),
        'grid': (100, 100, 100),
        'legend_bg': (25, 25, 25),
        'legend_text': (255, 255, 255)
    }

    @property
    def cell_size(self):
        return self._cell_size

    @cell_size.setter
    def cell_size(self, value):
        self._cell_size = max(5, value)  # Minimum 5px

    @property
    def colors(self):
        return self._colors

    @colors.setter
    def colors(self, value):
        self._colors = {**self.COLORS, **value}
    
    def __init__(self, cell_size=18):
        self.cell_size = cell_size
        
    def render(self, state: DungeonStateNeo, debug_show_all=False, include_legend=True, visibility_system=None):
        # Pass visibility_system to _render_dungeon
        dungeon_img = self._render_dungeon(state, debug_show_all, visibility_system)
        print(f"Render in render_neo.py")
        if include_legend:
            icons = self.generate_legend_icons()
            return self.create_composite_image(dungeon_img, icons)
        return dungeon_img

    def _render_dungeon(self, state: DungeonStateNeo, debug_show_all=False, visibility_system=None):
        width = state.width * self.cell_size
        height = state.height * self.cell_size
        base_img = Image.new('RGB', (width, height), self.COLORS['blocked'])
        base_draw = ImageDraw.Draw(base_img)
        cs = self.cell_size
        
        # Draw grid first (will be covered by cells but provides background structure)
        self._draw_grid(base_draw, width, height)
        
        # Draw all cells and their features
        for x in range(state.width):
            for y in range(state.height):
                cell = state.get_cell(x, y)
                if not cell:
                    continue
                    
                x_pix = x * cs
                y_pix = y * cs
                
                # Handle secret doors first - they have special visibility rules
                if cell.is_secret:
                    if not state.secret_mask[y][x] and not debug_show_all:
                        # Undiscovered secret - draw as blocked unless in debug mode
                        self._draw_blocked_cell(base_draw, x_pix, y_pix, cs)
                        continue
                    else:
                        # Discovered secret or debug mode - draw as corridor base
                        base_draw.rectangle([x_pix, y_pix, x_pix+cs, y_pix+cs], 
                                           fill=self.COLORS['corridor'])
                
                # Draw base cell for non-secret cells
                if not cell.is_secret:
                    self._draw_base_cell(base_draw, cell, x_pix, y_pix, cs)
                
                # Draw special features
                if cell.is_door:
                    orientation = state.get_door_orientation(x, y)
                    self._draw_door(base_draw, cell, orientation, int(x_pix), int(y_pix), int(cs))
                
                if cell.is_stairs:
                    orientation = state.get_stair_orientation(x, y)
                    stair_type = 'up' if cell.is_stair_up else 'down'
                    self._draw_stairs(base_draw, stair_type, orientation, x_pix, y_pix, cs)
                
                if cell.has_label:
                    self._draw_label(base_draw, cell, x_pix, y_pix, cs)
                
                # Draw entities
                for entity in cell.entities:
                    self._draw_entity(base_draw, entity, cell, x_pix, y_pix, cs)
                
                # Draw overlays
                for overlay in cell.overlays:
                    self._draw_overlay(base_draw, overlay, x_pix, y_pix, cs)
                
                # Debug outline for secret doors
                if cell.is_secret and debug_show_all:
                    base_draw.rectangle(
                        [x_pix, y_pix, x_pix+cs, y_pix+cs],
                        outline="red",
                        width=2
                    )
        
        # Draw grid on top of cells
        self._draw_grid(base_draw, width, height)
        
        # Draw party icon
        party_x, party_y = state.party_position
        self._draw_party_icon(base_draw, party_x, party_y, cs)
        
        # Apply fog layer if needed
        if not debug_show_all and visibility_system:
            fog_img = Image.new('RGBA', (width, height), (0, 0, 0, 255))
            fog_draw = ImageDraw.Draw(fog_img)
            
            # Cut holes for visible cells
            for y in range(state.height):
                for x in range(state.width):
                    if visibility_system.is_visible(x, y):
                        fog_draw.rectangle(
                            [x*cs, y*cs, (x+1)*cs, (y+1)*cs],
                            fill=(0, 0, 0, 0)  # Fully transparent
                        )
            
            base_rgba = base_img.convert('RGBA')
            composite = Image.alpha_composite(base_rgba, fog_img)
            result_img = composite.convert('RGB')
        else:
            result_img = base_img
        
        return result_img
    
    def _draw_blocked_cell(self, draw, x_pix, y_pix, cell_size):
        """Draw blocked cell (used for undiscovered secrets)"""
        draw.rectangle([x_pix, y_pix, x_pix+cell_size, y_pix+cell_size], 
                      fill=self.COLORS['blocked'])
    
    def _draw_base_cell(self, draw, cell, x_pix, y_pix, cell_size):
        """Draw the base cell (room, corridor, or blocked)"""
        if cell.is_room:
            draw.rectangle([x_pix, y_pix, x_pix+cell_size, y_pix+cell_size], 
                           fill=self.COLORS['room'])
        elif cell.is_corridor:
            draw.rectangle([x_pix, y_pix, x_pix+cell_size, y_pix+cell_size], 
                           fill=self.COLORS['corridor'])
        elif cell.is_blocked:
            draw.rectangle([x_pix, y_pix, x_pix+cell_size, y_pix+cell_size], 
                           fill=self.COLORS['blocked'])

    def _draw_entity(self, draw, entity, cell, x_pix, y_pix, cell_size):
        """Draw entity symbol with proper contrast"""
        # Determine background color for contrast
        if cell.is_room:
            bg_color = self.COLORS['room']
        elif cell.is_corridor:
            bg_color = self.COLORS['corridor']
        else:
            bg_color = (0, 0, 0)  # Default to black
            
        text_color = (0, 0, 0)  # Black for light backgrounds
        if sum(bg_color) < 382:  # Dark background
            text_color = (255, 255, 255)  # White for dark backgrounds
        
        # Draw entity symbol
        symbol = entity.get_symbol()
        try:
            font = ImageFont.truetype("arial.ttf", int(cell_size * 0.7))
        except:
            font = ImageFont.load_default()
        
        # Center the symbol in the cell
        text_x = x_pix + cell_size // 2
        text_y = y_pix + cell_size // 2
        draw.text(
            (text_x, text_y), 
            symbol, 
            fill=text_color,
            font=font,
            anchor="mm"  # Middle center alignment
        )
    
    def _draw_overlay(self, draw, overlay, x_pix, y_pix, cell_size):
        """Draw overlay primitive"""
        primitive = overlay.primitive
        params = overlay.params
        
        if primitive == "circle":
            size = params.get("size", 0.8) * cell_size
            color = params.get("color", (0, 255, 0))
            draw.ellipse([
                x_pix + (cell_size - size)//2, 
                y_pix + (cell_size - size)//2,
                x_pix + (cell_size + size)//2,
                y_pix + (cell_size + size)//2
            ], fill=color)
        
        elif primitive == "square":
            size = params.get("size", 0.8) * cell_size
            color = params.get("color", (0, 255, 0))
            rotation = params.get("rotation", 0)
            center_x = x_pix + cell_size // 2
            center_y = y_pix + cell_size // 2
            half_size = size/2
            
            if rotation:
                # Create rotated rectangle
                points = [
                    (-half_size, -half_size),
                    (half_size, -half_size),
                    (half_size, half_size),
                    (-half_size, half_size)
                ]
                rad = math.radians(rotation)
                rotated_points = []
                for px, py in points:
                    rx = px * math.cos(rad) - py * math.sin(rad)
                    ry = px * math.sin(rad) + py * math.cos(rad)
                    rotated_points.append((center_x + rx, center_y + ry))
                draw.polygon(rotated_points, fill=color)
            else:
                draw.rectangle([
                    center_x - half_size, center_y - half_size,
                    center_x + half_size, center_y + half_size
                ], fill=color)
        
        elif primitive == "triangle":
            size = params.get("size", 0.8) * cell_size
            color = params.get("color", (0, 255, 0))
            rotation = params.get("rotation", 0)
            center_x = x_pix + cell_size // 2
            center_y = y_pix + cell_size // 2
            
            # Calculate points for equilateral triangle
            height = size * math.sqrt(3)/2
            points = [
                (0, -size/2),           # Top vertex
                (-size/2, height/2),     # Bottom left
                (size/2, height/2)       # Bottom right
            ]
            
            # Apply rotation
            rad = math.radians(rotation)
            rotated_points = []
            for px, py in points:
                rx = px * math.cos(rad) - py * math.sin(rad)
                ry = px * math.sin(rad) + py * math.cos(rad)
                rotated_points.append((center_x + rx, center_y + ry))
            
            draw.polygon(rotated_points, fill=color)
        
        elif primitive == "line":
            start_x = params.get("start_x", 0.1) * cell_size
            start_y = params.get("start_y", 0.1) * cell_size
            end_x = params.get("end_x", 0.9) * cell_size
            end_y = params.get("end_y", 0.9) * cell_size
            color = params.get("color", (0, 255, 0))
            width = params.get("width", max(1, cell_size//10))
            draw.line([
                x_pix + start_x, y_pix + start_y,
                x_pix + end_x, y_pix + end_y
            ], fill=color, width=width)
        
        elif primitive == "text":
            content = params.get("content", "?")
            color = params.get("color", (255, 255, 255))
            font_size = int(params.get("size", 12) * cell_size / 12)
            
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            text_x = x_pix + cell_size // 2
            text_y = y_pix + cell_size // 2
            draw.text(
                (text_x, text_y), 
                content, 
                fill=color,
                font=font,
                anchor="mm"  # Middle center alignment
            )
        
        elif primitive == "polygon":
            points = params.get("points", [])
            color = params.get("color", (0, 255, 0))
            absolute_points = []
            for px, py in points:
                absolute_points.append((
                    x_pix + px * cell_size,
                    y_pix + py * cell_size
                ))
            draw.polygon(absolute_points, fill=color)
  
    def _draw_party_icon(self, draw, x, y, cell_size):
        """Draw party icon at position"""
        center_x = x * cell_size + cell_size // 2
        center_y = y * cell_size + cell_size // 2
        radius = cell_size // 4
        draw.ellipse([
            center_x - radius, center_y - radius,
            center_x + radius, center_y + radius
        ], fill="#FF0000")  # Red circle

    def _draw_label(self, draw, cell, x_pix, y_pix, cell_size):
        """Draw room label"""
        char_code = (cell.base_type & self.LABEL) >> 24
        if char_code:
            char = chr(char_code)
            try:
                font = ImageFont.truetype("arial.ttf", cell_size // 2)
            except:
                font = ImageFont.load_default()
            
            text_x = x_pix + cell_size // 2
            text_y = y_pix + cell_size // 2
            draw.text(
                (text_x, text_y), 
                char, 
                fill=(0, 0, 0),
                font=font,
                anchor="mm"
            )

    def _draw_stairs(self, draw, stair_type, orientation, x_pix, y_pix, cell_size):
        """Draw stairs with proper orientation"""
        color = self.COLORS['stairs_up'] if stair_type == 'up' else self.COLORS['stairs_down']
        step_count = 5
        spacing = cell_size / (step_count + 1)
        max_length = cell_size * 0.7
        
        if orientation == 'horizontal':
            center_y = y_pix + cell_size // 2
            for i in range(1, step_count + 1):
                length = max_length * (i / step_count) if stair_type == 'down' else max_length
                x_pos = x_pix + i * spacing
                draw.line([
                    x_pos, center_y - length//2,
                    x_pos, center_y + length//2
                ], fill=color, width=2)
        else:
            center_x = x_pix + cell_size // 2
            for i in range(1, step_count + 1):
                length = max_length * (i / step_count) if stair_type == 'down' else max_length
                y_pos = y_pix + i * spacing
                draw.line([
                    center_x - length//2, y_pos,
                    center_x + length//2, y_pos
                ], fill=color, width=2)

    def _draw_door(self, draw, cell, orientation, x_pix, y_pix, cell_size):
        """Draw door with proper orientation"""
        color = self.COLORS['door']
        center_x = x_pix + cell_size // 2
        center_y = y_pix + cell_size // 2
        door_width = cell_size // 3
        arch_height = cell_size // 6
        
        # Draw door slab
        if not cell.is_arch and not cell.is_portc:  # Don't draw slab for arch/portc
            if orientation == 'horizontal':
                draw.rectangle([
                    center_x - door_width//2, y_pix,
                    center_x + door_width//2, y_pix + cell_size
                ], fill=color)
            else:
                draw.rectangle([
                    x_pix, center_y - door_width//2,
                    x_pix + cell_size, center_y + door_width//2
                ], fill=color)
        
        # Draw arch for all doors
        if orientation == 'horizontal':
            # Top arch
            draw.rectangle([
                center_x - door_width//2, y_pix,
                center_x + door_width//2, y_pix + arch_height
            ], fill=self.COLORS['arch'])
            # Bottom arch
            draw.rectangle([
                center_x - door_width//2, y_pix + cell_size - arch_height,
                center_x + door_width//2, y_pix + cell_size
            ], fill=self.COLORS['arch'])
        else:
            # Left arch
            draw.rectangle([
                x_pix, center_y - door_width//2,
                x_pix + arch_height, center_y + door_width//2
            ], fill=self.COLORS['arch'])
            # Right arch
            draw.rectangle([
                x_pix + cell_size - arch_height, center_y - door_width//2,
                x_pix + cell_size, center_y + door_width//2
            ], fill=self.COLORS['arch'])
        
        # Add special symbols
        if cell.is_locked:
            # Diamond lock symbol
            lock_size = cell_size // 6
            diamond = [
                (center_x, center_y - lock_size//2),
                (center_x + lock_size//2, center_y),
                (center_x, center_y + lock_size//2),
                (center_x - lock_size//2, center_y)
            ]
            draw.polygon(diamond, fill=(100, 100, 100))
        elif cell.is_portc:
            # Portcullis vertical bars
            bar_count = 5
            bar_radius = max(1, cell_size // 20)
            bar_spacing = cell_size / (bar_count + 1)
            
            if orientation == 'horizontal':
                # Horizontal portcullis - bars vertical
                bar_x = center_x
                for i in range(1, bar_count + 1):
                    bar_y = y_pix + i * bar_spacing
                    draw.ellipse([
                        bar_x - bar_radius, bar_y - bar_radius,
                        bar_x + bar_radius, bar_y + bar_radius
                    ], fill=color)
            else:
                # Vertical portcullis - bars horizontal
                bar_y = center_y
                for i in range(1, bar_count + 1):
                    bar_x = x_pix + i * bar_spacing
                    draw.ellipse([
                        bar_x - bar_radius, bar_y - bar_radius,
                        bar_x + bar_radius, bar_y + bar_radius
                    ], fill=color)
            
    def _draw_grid(self, draw, width, height):
        # Horizontal lines
        for y in range(0, height, self.cell_size):
            draw.line([(0, y), (width, y)], fill=self.COLORS['grid'], width=1)
        # Vertical lines
        for x in range(0, width, self.cell_size):
            draw.line([(x, 0), (x, height)], fill=self.COLORS['grid'], width=1)
    
    def _draw_block(self, draw, x, y, size=None):
        """Draw block icon for legend"""
        if size is None:
            size = self.cell_size
        draw.rectangle([x, y, x + size, y + size], fill=self.COLORS['blocked'])
    
    def _draw_room(self, draw, x, y):
        draw.rectangle([
            x, y, 
            x + self.cell_size, y + self.cell_size
        ], fill=self.COLORS['room'])
    
    def _draw_corridor(self, draw, x, y):
        draw.rectangle([
            x, y, 
            x + self.cell_size, y + self.cell_size
        ], fill=self.COLORS['corridor'])

    def has_open_space(self, r, c):
        """Check if coordinates contain open space"""
        if not hasattr(self, 'state') or not self.state:
            return False
        if r < 0 or r >= self.state.height or c < 0 or c >= self.state.width:
            return False
        cell = self.state.grid[r][c]
        return cell and (cell.is_room or cell.is_corridor)
    
    def _get_door_type(self, cell_flags):
        if cell_flags & self.ARCH:
            return 'arch'
        elif cell_flags & self.DOOR:
            return 'door'
        elif cell_flags & self.LOCKED:
            return 'locked'
        elif cell_flags & self.TRAPPED:
            return 'trapped'
        elif cell_flags & self.SECRET:
            return 'secret'
        elif cell_flags & self.PORTC:
            return 'portc'
        return 'door'

    def generate_legend_icons(self, icon_size=20):
        elements = [
            ('room', 'Room'),
            ('corridor', 'Corridor'),
            ('arch', 'Archway'),
            ('door', 'Open Door'),
            ('locked', 'Locked Door'),
            ('trapped', 'Trapped Door'),
            ('secret', 'Secret Door'),
            ('secret_debug', 'Secret Door (Debug)'),
            ('portc', 'Portcullis'),
            ('stairs_up', 'Stairs Up'),
            ('stairs_down', 'Stairs Down')
        ]
        
        icons = {}
        for element, label in elements:
            img = Image.new('RGB', (icon_size, icon_size), self.COLORS['legend_bg'])
            draw = ImageDraw.Draw(img)
            
            # Reduced margin for better fitting
            margin = 1
            cell_size = icon_size - 2 * margin
            
            # Draw element with proper background
            if element == 'room':
                self._draw_base_cell(draw, 
                    type('MockCell', (object,), {'is_room': True, 'is_corridor': False, 'is_blocked': False}),
                    margin, margin, cell_size
                )
            elif element == 'corridor':
                self._draw_base_cell(draw, 
                    type('MockCell', (object,), {'is_room': False, 'is_corridor': True, 'is_blocked': False}),
                    margin, margin, cell_size
                )
            elif element in ['arch', 'door', 'locked', 'trapped', 'portc']:
                # Create mock cell
                mock_cell = type('MockCell', (object,), {
                    'is_arch': element == 'arch',
                    'is_door': True,
                    'is_door_unlocked': element == 'door',
                    'is_locked': element == 'locked',
                    'is_trapped': element == 'trapped',
                    'is_portc': element == 'portc',
                    'is_secret': False,
                    'x': 0,
                    'y': 0
                })
                # Draw on corridor background
                self._draw_base_cell(draw, 
                    type('MockCell', (object,), {'is_room': False, 'is_corridor': True, 'is_blocked': False}),
                    margin, margin, cell_size
                )
                # FIXED: Correct parameter order for _draw_door
                self._draw_door(draw, mock_cell, 'horizontal', margin, margin, cell_size)
            
            elif element == 'secret':
                # Normal secret door - just a blocked cell
                self._draw_base_cell(draw, 
                    type('MockCell', (object,), {'is_room': False, 'is_corridor': False, 'is_blocked': True}),
                    margin, margin, cell_size
                )
            
            elif element == 'secret_debug':
                # Debug secret door: blocked base + door overlay
                # Draw blocked background
                self._draw_base_cell(draw, 
                    type('MockCell', (object,), {'is_room': False, 'is_corridor': False, 'is_blocked': True}),
                    margin, margin, cell_size
                )
                # Create mock cell for door
                mock_cell = type('MockCell', (object,), {
                    'is_arch': False,
                    'is_door': True,
                    'is_door_unlocked': True,
                    'is_locked': False,
                    'is_trapped': False,
                    'is_portc': False,
                    'is_secret': True,
                    'x': 0,
                    'y': 0
                })
                # FIXED: Correct parameter order for _draw_door
                self._draw_door(draw, mock_cell, 'horizontal', margin, margin, cell_size)
                # Add red outline
                draw.rectangle(
                    [margin, margin, margin+cell_size, margin+cell_size],
                    outline="red",
                    width=1
                )
            
            elif 'stairs' in element:
                stair_type = element.split('_')[1]
                # Draw on corridor background
                self._draw_base_cell(draw, 
                    type('MockCell', (object,), {'is_room': False, 'is_corridor': True, 'is_blocked': False}),
                    margin, margin, cell_size
                )
                # FIXED: Correct parameter order for _draw_stairs
                self._draw_stairs(draw, stair_type, 'horizontal', margin, margin, cell_size)
            
            icons[element] = (img, label)
        
        return icons


    def create_composite_image(self, dungeon_img, icons, position='right', padding=20):
        """Create image with dungeon on left and legend on right"""
        # Calculate dimensions
        icon_size = next(iter(icons.values()))[0].size[0] if icons else 30
        legend_width = 200
        total_width = dungeon_img.width + legend_width + padding * 3
        total_height = max(dungeon_img.height, 400)
        
        # Create composite image
        composite = Image.new('RGB', (total_width, total_height), self.COLORS['legend_bg'])
        draw = ImageDraw.Draw(composite)
        
        # Paste dungeon
        composite.paste(dungeon_img, (padding, padding))
        
        # Draw legend title
        font = ImageFont.load_default()
        draw.text((dungeon_img.width + padding * 2, padding), "LEGEND", 
                 fill=self.COLORS['legend_text'], font=font)
        
        # Draw legend items
        y_offset = padding + 30
        for element, (icon, label) in icons.items():
            composite.paste(icon, (dungeon_img.width + padding * 2, y_offset))
            draw.text((dungeon_img.width + padding * 2 + icon_size + 10, y_offset + icon_size//2 - 5), 
                     label, fill=self.COLORS['legend_text'], font=font)
            y_offset += icon_size + 10
        
        return composite

    def _draw_room(self, draw, x, y, size=None):
        """Draw room icon, works for both grid and legend"""
        if size is None:
            size = self.cell_size
        draw.rectangle([x, y, x + size, y + size], fill=self.COLORS['room'])

    def _draw_corridor(self, draw, x, y, size=None):
        """Draw corridor icon, works for both grid and legend"""
        if size is None:
            size = self.cell_size
        draw.rectangle([x, y, x + size, y + size], fill=self.COLORS['corridor'])