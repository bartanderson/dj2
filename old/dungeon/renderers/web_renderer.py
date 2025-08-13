# dungeon/renderers/web_renderer.py
# from src.adapters import DungeonStateAdapter
# from src.interfaces import IGameState

from .base_renderer import BaseRenderer

class WebRenderer(BaseRenderer):
    def render(self, visible_only=True, **kwargs):
        return self.state.render_to_web(visible_only)
