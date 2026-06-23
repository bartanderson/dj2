"""
Runtime scene compositor — pure PIL, no GPU.

Takes a SceneSelection + optional character IDs and composes a final scene image:
  background variant → mood overlay → character layers → output

All heavy GPU work happens offline (variant_generator.py).
This runs during play at negligible cost.
"""

from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import json


# Mood → (color tint RGBA, opacity)
MOOD_OVERLAYS = {
    "neutral":  None,
    "cozy":     ((255, 200, 100, 30),),   # warm amber wash
    "tense":    ((80,  0,   0,  50),),    # red-dark wash
    "eerie":    ((40,  0,   80, 45),),    # purple-dark
    "desolate": ((100, 110, 120, 40),),   # cold grey-blue
}

# Time-of-day → brightness multiplier, color shift
TIME_ADJUSTMENTS = {
    "day":   (1.0,  None),
    "dawn":  (0.75, (255, 180, 120)),     # warm orange cast
    "dusk":  (0.65, (200, 120, 80)),      # deeper orange-red
    "night": (0.35, (30,  40,  80)),      # cool dark blue
}


class SceneCompositor:
    def __init__(self, catalog, output_size: Tuple[int, int] = (1024, 576)):
        self.catalog = catalog
        self.output_size = output_size  # 16:9 default

    def compose(self, selection, character_ids: List[str] = None,
                output_path: Optional[Path] = None) -> Image.Image:
        """
        selection: SceneSelection from SceneResolver.resolve()
        character_ids: optional list of character catalog IDs to layer in
        output_path: if given, saves the result there

        Returns a PIL Image.
        """
        # 1. Load background
        bg = self._load_background(selection.base_path)

        # 2. Time-of-day adjustment
        bg = self._apply_time(bg, selection.time_of_day)

        # 3. Mood overlay
        bg = self._apply_mood(bg, selection.mood)

        # 4. Weather effect
        if selection.weather and selection.weather != "clear":
            bg = self._apply_weather(bg, selection.weather)

        # 5. Character layers
        if character_ids:
            bg = self._composite_characters(bg, character_ids)

        # 6. Vignette (cheap atmosphere)
        bg = self._vignette(bg)

        if output_path:
            bg.save(str(output_path))

        return bg

    # ------------------------------------------------------------------
    # Internal steps
    # ------------------------------------------------------------------

    def _load_background(self, path: str) -> Image.Image:
        img = Image.open(path).convert("RGB")
        img = img.resize(self.output_size, Image.LANCZOS)
        return img

    def _apply_time(self, img: Image.Image, time_of_day: str) -> Image.Image:
        brightness, tint = TIME_ADJUSTMENTS.get(time_of_day, (1.0, None))

        if brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(brightness)

        if tint:
            tint_layer = Image.new("RGB", img.size, tint)
            img = Image.blend(img, tint_layer, alpha=0.25)

        return img

    def _apply_mood(self, img: Image.Image, mood: str) -> Image.Image:
        overlays = MOOD_OVERLAYS.get(mood)
        if not overlays:
            return img

        result = img.convert("RGBA")
        for color in overlays:
            overlay = Image.new("RGBA", img.size, color)
            result = Image.alpha_composite(result, overlay)

        return result.convert("RGB")

    def _apply_weather(self, img: Image.Image, weather: str) -> Image.Image:
        if weather == "fog":
            fog = Image.new("RGBA", img.size, (200, 210, 215, 80))
            result = img.convert("RGBA")
            result = Image.alpha_composite(result, fog)
            result = result.filter(ImageFilter.GaussianBlur(radius=1))
            return result.convert("RGB")

        if weather == "rain":
            # Darken + blue-grey tint
            img = ImageEnhance.Brightness(img).enhance(0.80)
            tint = Image.new("RGB", img.size, (70, 80, 100))
            img = Image.blend(img, tint, alpha=0.20)
            return img

        if weather == "storm":
            img = ImageEnhance.Brightness(img).enhance(0.55)
            tint = Image.new("RGB", img.size, (40, 45, 60))
            img = Image.blend(img, tint, alpha=0.35)
            img = ImageEnhance.Contrast(img).enhance(1.3)
            return img

        if weather == "snow":
            snow = Image.new("RGBA", img.size, (255, 255, 255, 40))
            result = img.convert("RGBA")
            result = Image.alpha_composite(result, snow)
            return result.convert("RGB")

        return img

    def _composite_characters(self, bg: Image.Image,
                              character_ids: List[str]) -> Image.Image:
        result = bg.convert("RGBA")
        w, h = bg.size

        for i, char_id in enumerate(character_ids[:4]):   # cap at 4 characters
            char = self.catalog.find_characters()
            # find by id
            char_row = next(
                (c for c in self.catalog.find_characters() if c["id"] == char_id),
                None
            )
            if not char_row:
                continue

            try:
                sprite = Image.open(char_row["path"]).convert("RGBA")
            except Exception:
                continue

            anchor = char_row.get("anchor", {})
            if isinstance(anchor, str):
                try:
                    anchor = json.loads(anchor)
                except Exception:
                    anchor = {}

            # Default placement: spread characters across bottom third
            sprite_w = anchor.get("w", w // 5)
            sprite_h = anchor.get("h", h // 2)
            sprite = sprite.resize((sprite_w, sprite_h), Image.LANCZOS)

            x = anchor.get("x", int(w * 0.2 + i * (w * 0.18)))
            y = anchor.get("y", h - sprite_h - int(h * 0.05))

            result.paste(sprite, (x, y), sprite)

        return result.convert("RGB")

    def _vignette(self, img: Image.Image) -> Image.Image:
        """Subtle dark edge vignette for atmosphere."""
        w, h = img.size
        vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)

        steps = 40
        for i in range(steps):
            alpha = int(120 * (i / steps) ** 2)
            margin = int(min(w, h) * 0.5 * (1 - i / steps))
            draw.rectangle(
                [margin, margin, w - margin, h - margin],
                outline=(0, 0, 0, alpha)
            )

        result = img.convert("RGBA")
        result = Image.alpha_composite(result, vignette)
        return result.convert("RGB")
