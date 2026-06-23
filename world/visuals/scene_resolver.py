"""
Maps a UnifiedContext (or equivalent dict) to a scene selection:
which base image + which modifiers to apply.

Priority: exact terrain+structure match → terrain-only → any base.
Modifier mapping is deterministic from context fields.
"""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass


# Maps UnifiedContext.activity/domain combos to structure types
STRUCTURE_MAP = {
    ("dungeon", None):      "dungeon",
    ("world", "idle"):      "wilderness",
    ("world", "travel"):    "wilderness",
    ("world", "combat"):    "wilderness",
    ("settlement", "idle"): "village",
    ("settlement", "social"): "tavern_interior",
    ("settlement", "combat"): "village",
}

# Maps UnifiedContext.terrain to catalog terrain keys
TERRAIN_MAP = {
    "plains":   "plains",
    "forest":   "forest",
    "hills":    "hills",
    "mountain": "mountains",
    "mountains":"mountains",
    "desert":   "desert",
    "coastal":  "coastal",
    "lake":     "coastal",
    "swamp":    "forest",   # fallback
    "arctic":   "arctic",
    "snow":     "arctic",
    "underground": "underground",
    "interior": "interior",
}

MOOD_MAP = {
    # tension thresholds
    "high":   "tense",
    "medium": "neutral",
    "low":    "cozy",
}


@dataclass
class SceneSelection:
    base_id: str
    base_path: str
    season: Optional[str]
    weather: Optional[str]
    time_of_day: str
    mood: str
    character_tags: List[str]   # hints for compositor character selection


class SceneResolver:
    def __init__(self, catalog):
        self.catalog = catalog

    def resolve(self, context) -> Optional[SceneSelection]:
        """
        context: UnifiedContext instance or dict with same fields.
        Returns SceneSelection or None if no base images registered yet.
        """
        d = context if isinstance(context, dict) else context.to_dict()

        terrain   = TERRAIN_MAP.get(d.get("terrain", "plains"), "plains")
        domain    = d.get("domain", "world")
        activity  = d.get("activity", "idle")
        indoors   = d.get("indoors", False)

        structure = self._resolve_structure(domain, activity, indoors)
        time_of_day = d.get("time_of_day", "day")
        mood      = self._resolve_mood(d.get("tension", 0.0), d.get("mood", "neutral"))
        weather   = d.get("weather")   # may not exist in older contexts
        season    = d.get("season")    # same

        # Find best base
        base = self._find_best_base(terrain, structure)
        if not base:
            return None

        # Find or note needed variant
        variant = self.catalog.find_variant(
            base["id"],
            season=season,
            weather=weather,
            time_of_day=time_of_day,
            mood=mood,
        )
        path = variant["path"] if variant else base["path"]

        char_tags = self._character_hints(d)

        return SceneSelection(
            base_id=base["id"],
            base_path=path,
            season=season,
            weather=weather,
            time_of_day=time_of_day,
            mood=mood,
            character_tags=char_tags,
        )

    # ------------------------------------------------------------------

    def _resolve_structure(self, domain: str, activity: str, indoors: bool) -> str:
        if indoors:
            return "tavern_interior"
        return STRUCTURE_MAP.get((domain, activity),
               STRUCTURE_MAP.get((domain, None), "wilderness"))

    def _resolve_mood(self, tension: float, mood_str: str) -> str:
        if mood_str in ("eerie", "tense", "cozy", "desolate", "neutral"):
            return mood_str
        if tension >= 0.7:
            return "tense"
        if tension >= 0.3:
            return "neutral"
        return "cozy"

    def _find_best_base(self, terrain: str, structure: str) -> Optional[Dict]:
        # Exact match
        bases = self.catalog.find_bases(terrain=terrain, structure=structure)
        if bases:
            return bases[0]
        # Terrain only
        bases = self.catalog.find_bases(terrain=terrain)
        if bases:
            return bases[0]
        # Any
        bases = self.catalog.find_bases()
        return bases[0] if bases else None

    def _character_hints(self, d: dict) -> List[str]:
        """
        Returns archetype tags to guide compositor character selection.
        Maps game state to which character types should appear in scene.
        """
        tags = []
        activity = d.get("activity", "idle")
        domain   = d.get("domain", "world")
        tension  = d.get("tension", 0.0)

        if activity == "combat":
            tags.extend(["enemy", "combat"])
            if tension >= 0.7:
                tags.append("attacking")
        elif activity == "social":
            if domain == "settlement":
                tags.extend(["npc", "innkeeper", "merchant"])
            else:
                tags.append("npc")
        elif activity == "travel":
            if tension >= 0.5:
                tags.extend(["bandit", "enemy"])

        presence = d.get("presence", "alone")
        if presence == "alone":
            tags.append("solo")
        elif presence == "crowded":
            tags.append("crowd")

        return tags
