from PIL import Image, ImageDraw
from .base_renderer import BaseRenderer

from PIL import Image, ImageDraw
from .base_renderer import BaseRenderer

class ImageRenderer(BaseRenderer):
    def render(self, cell_size=18, grid_color=(200, 200, 200), debug_show_all=False, **kwargs):
        print("ImageRenderer.render() called")
        print(f"State type: {type(self.state)}")
        print(f"State has render_to_image: {hasattr(self.state, 'render_to_image')}")
        
        try:
            # Only update effect timers
            if hasattr(self.state, 'update_effect_timers'):
                self.state.update_effect_timers()
            
            # Render without additional visibility updates
            return self.state.render_to_image(cell_size, grid_color, debug_show_all=debug_show_all)
            
        except Exception as e:
            print(f"Error in ImageRenderer.render: {str(e)}")
            # Create error image
            error_img = Image.new('RGB', (800, 600), (255, 0, 0))
            draw = ImageDraw.Draw(error_img)
            draw.text((10, 10), f"Render Error: {str(e)}", fill=(0, 0, 0))
            return error_img