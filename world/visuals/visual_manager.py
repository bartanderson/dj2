"""
VisualManager — wires the visual system to EventLog and UnifiedContext.

Lightweight runtime component. Plug this in when you're ready:

    from world.visuals.visual_manager import VisualManager
    visual_mgr = VisualManager(catalog, event_log, output_dir=Path("static/current"))
    visual_mgr.attach()

After attach(), any state-changing event automatically updates the scene.
The composed image is saved to output_dir/scene.jpg for the web UI to display.
"""

from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VisualManager:
    def __init__(self, catalog, event_log, output_dir: Path,
                 scene_size=(1024, 576)):
        from world.visuals.scene_resolver import SceneResolver
        from world.visuals.compositor import SceneCompositor

        self.catalog    = catalog
        self.event_log  = event_log
        self.output_dir = output_dir
        self.resolver   = SceneResolver(catalog)
        self.compositor = SceneCompositor(catalog, output_size=scene_size)
        self._current_context = None
        self._listener  = None

        output_dir.mkdir(parents=True, exist_ok=True)

    def attach(self) -> None:
        """Register with EventLog to auto-update on state changes."""
        trigger_events = {
            "movement.arrived",
            "combat.start",
            "combat.end",
            "location.enter",
            "location.exit",
            "time.changed",
            "weather.changed",
            "encounter.start",
        }

        def _on_event(event):
            if event.type in trigger_events:
                self._refresh()

        self._listener = self.event_log.on_any(_on_event)
        logger.info("VisualManager attached to EventLog")

    def update_context(self, context) -> None:
        """Call this when UnifiedContext changes outside of events."""
        self._current_context = context
        self._refresh()

    def _refresh(self) -> None:
        if self._current_context is None:
            return
        try:
            selection = self.resolver.resolve(self._current_context)
            if selection is None:
                return
            out = self.output_dir / "scene.jpg"
            self.compositor.compose(selection, output_path=out)
            logger.debug(f"Scene updated: {selection.base_id} / {selection.time_of_day} / {selection.mood}")
        except Exception as e:
            logger.error(f"VisualManager refresh failed: {e}", exc_info=True)

    @property
    def scene_path(self) -> Path:
        return self.output_dir / "scene.jpg"
