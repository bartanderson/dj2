# File: overlay.py
import math

class Overlay:
    PRIMITIVE_TYPES = ['circle', 'square', 'triangle', 'line', 'text', 'polygon']
    
    def __init__(self, primitive, **params):
        if primitive not in self.PRIMITIVE_TYPES:
            raise ValueError(f"Invalid primitive type: {primitive}")
        
        self.primitive = primitive
        self.params = params
        
    def render(self, draw, x, y, cell_size):
        x_pix = x * cell_size
        y_pix = y * cell_size
        
        if self.primitive == "circle":
            size = self.params.get("size", 0.8) * cell_size
            color = self.params.get("color", (0, 255, 0))
            draw.ellipse([
                x_pix + (cell_size - size)//2, 
                y_pix + (cell_size - size)//2,
                x_pix + (cell_size + size)//2,
                y_pix + (cell_size + size)//2
            ], fill=color)
            
        elif self.primitive == "square":
            size = self.params.get("size", 0.8) * cell_size
            color = self.params.get("color", (0, 255, 0))
            rotation = self.params.get("rotation", 0)
            
            # Create rotated rectangle
            center = (x_pix + cell_size//2, y_pix + cell_size//2)
            half_size = size/2
            points = [
                (-half_size, -half_size),
                (half_size, -half_size),
                (half_size, half_size),
                (-half_size, half_size)
            ]
            
            # Apply rotation
            if rotation:
                rad = math.radians(rotation)
                rotated_points = []
                for px, py in points:
                    rx = px * math.cos(rad) - py * math.sin(rad)
                    ry = px * math.sin(rad) + py * math.cos(rad)
                    rotated_points.append((center[0] + rx, center[1] + ry))
                draw.polygon(rotated_points, fill=color)
            else:
                draw.rectangle([
                    center[0] - half_size, 
                    center[1] - half_size,
                    center[0] + half_size,
                    center[1] + half_size
                ], fill=color)
            
        elif self.primitive == "triangle":
            size = self.params.get("size", 0.8) * cell_size
            color = self.params.get("color", (0, 255, 0))
            rotation = self.params.get("rotation", 0)  # Rotation in degrees
            
            # Calculate points for equilateral triangle
            height = size * math.sqrt(3)/2
            points = [
                (0, -size/2),           # Top vertex
                (-size/2, height/2),     # Bottom left
                (size/2, height/2)       # Bottom right
            ]
            
            # Apply rotation
            center = (x_pix + cell_size//2, y_pix + cell_size//2)
            rad = math.radians(rotation)
            rotated_points = []
            for px, py in points:
                rx = px * math.cos(rad) - py * math.sin(rad)
                ry = px * math.sin(rad) + py * math.cos(rad)
                rotated_points.append((center[0] + rx, center[1] + ry))
            
            draw.polygon(rotated_points, fill=color)
            
        elif self.primitive == "line":
            start_x = self.params.get("start_x", 0.1) * cell_size
            start_y = self.params.get("start_y", 0.1) * cell_size
            end_x = self.params.get("end_x", 0.9) * cell_size
            end_y = self.params.get("end_y", 0.9) * cell_size
            color = self.params.get("color", (0, 255, 0))
            width = self.params.get("width", max(1, cell_size//10))
            
            draw.line([
                x_pix + start_x,
                y_pix + start_y,
                x_pix + end_x,
                y_pix + end_y
            ], fill=color, width=width)
            
        elif self.primitive == "text":
            content = self.params.get("content", "?")
            color = self.params.get("color", (255, 255, 255))
            size = self.params.get("size", min(0.8, cell_size/20))
            
            # Create temporary font
            from PIL import ImageFont
            try:
                font = ImageFont.truetype("arial.ttf", int(size * cell_size))
            except:
                font = ImageFont.load_default()
            
            draw.text(
                (x_pix + cell_size//2, y_pix + cell_size//2), 
                content, 
                fill=color,
                font=font,
                anchor="mm"  # Middle center alignment
            )
            
        elif self.primitive == "polygon":
            points = self.params.get("points", [])
            color = self.params.get("color", (0, 255, 0))
            
            # Convert relative points to absolute coordinates
            absolute_points = []
            for px, py in points:
                absolute_points.append((
                    x_pix + px * cell_size,
                    y_pix + py * cell_size
                ))
                
            draw.polygon(absolute_points, fill=color)