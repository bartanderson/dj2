# world/encounter_models.py
"""
Data models for the encounter system:
- MonsterInstance: a specific monster in an encounter (with current HP, conditions)
- Encounter: a concrete encounter (list of monsters, state, loot, etc.)
- EncounterPoint: a persistent location on the map where an encounter can occur
"""

import uuid
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime


class PointState(Enum):
    UNTOUCHED = "untouched"
    ACTIVE = "active"
    CLEARED = "cleared"
    ABANDONED = "abandoned"
    EVOLVED = "evolved"


class EncounterState(Enum):
    PENDING = "pending"
    RESOLVED_COMBAT = "resolved_combat"
    RESOLVED_NONCOMBAT = "resolved_noncombat"
    FLED = "fled"
    PARTIAL = "partial"


class MonsterInstance:
    """A specific monster present in an encounter, with mutable state."""
    def __init__(self, monster_id: str, current_hp: int, name: Optional[str] = None):
        self.monster_id = monster_id
        self.current_hp = current_hp
        self.conditions: List[str] = []
        self.name = name or None  # optional, for named monsters

    def to_dict(self) -> dict:
        return {
            "monster_id": self.monster_id,
            "current_hp": self.current_hp,
            "conditions": self.conditions,
            "name": self.name
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MonsterInstance':
        inst = cls(data["monster_id"], data["current_hp"], data.get("name"))
        inst.conditions = data.get("conditions", [])
        return inst

    def is_alive(self) -> bool:
        return self.current_hp > 0


class Encounter:
    """A concrete encounter, generated when a point is activated."""
    def __init__(self, point_id: str, difficulty: float, loot_table: str = ""):
        self.id = f"enc_{uuid.uuid4().hex[:8]}"
        self.point_id = point_id
        self.monsters: List[MonsterInstance] = []
        self.description: str = ""
        self.difficulty = difficulty          # calculated CR or XP budget
        self.loot_table = loot_table          # e.g., "CR1-5" or specific list
        self.state = EncounterState.PENDING
        self.survivors: List[str] = []        # monster IDs that fled
        self.consequences: Dict[str, Any] = {}  # e.g., {"rumor": "..."}

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "point_id": self.point_id,
            "monsters": [m.to_dict() for m in self.monsters],
            "description": self.description,
            "difficulty": self.difficulty,
            "loot_table": self.loot_table,
            "state": self.state.value,
            "survivors": self.survivors,
            "consequences": self.consequences
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Encounter':
        enc = cls(data["point_id"], data["difficulty"], data.get("loot_table", ""))
        enc.id = data["id"]
        enc.monsters = [MonsterInstance.from_dict(m) for m in data.get("monsters", [])]
        enc.description = data.get("description", "")
        enc.state = EncounterState(data["state"])
        enc.survivors = data.get("survivors", [])
        enc.consequences = data.get("consequences", {})
        return enc

    def add_monster(self, monster_instance: MonsterInstance):
        self.monsters.append(monster_instance)

    def remove_dead(self):
        """Remove dead monsters and possibly add them to survivors if they fled."""
        # For now, just remove dead; survivors handled separately
        self.monsters = [m for m in self.monsters if m.is_alive()]

    def all_dead(self) -> bool:
        return len(self.monsters) == 0


class EncounterPoint:
    """A persistent point on the world map where an encounter can happen."""
    def __init__(self, point_id: str, region_id: str, x: int, y: int, type_hint: str):
        self.id = point_id
        self.region_id = region_id
        self.x = x
        self.y = y
        self.type_hint = type_hint          # e.g., "camp", "lair", "ruin"
        self.state = PointState.UNTOUCHED
        self.last_updated = datetime.now().isoformat()
        self.current_encounter_id: Optional[str] = None
        self.story_tags: List[str] = []     # e.g., ["rumor_mentions", "quest_target"]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "region_id": self.region_id,
            "x": self.x,
            "y": self.y,
            "type_hint": self.type_hint,
            "state": self.state.value,
            "last_updated": self.last_updated,
            "current_encounter_id": self.current_encounter_id,
            "story_tags": self.story_tags
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'EncounterPoint':
        point = cls(
            data["id"],
            data["region_id"],
            data["x"],
            data["y"],
            data["type_hint"]
        )
        point.state = PointState(data["state"])
        point.last_updated = data.get("last_updated", point.last_updated)
        point.current_encounter_id = data.get("current_encounter_id")
        point.story_tags = data.get("story_tags", [])
        return point

    def activate(self, encounter_id: str):
        """Mark point as active and link to an encounter."""
        self.state = PointState.ACTIVE
        self.current_encounter_id = encounter_id
        self.last_updated = datetime.now().isoformat()

    def clear(self):
        """Mark point as cleared (no active encounter)."""
        self.state = PointState.CLEARED
        self.current_encounter_id = None
        self.last_updated = datetime.now().isoformat()