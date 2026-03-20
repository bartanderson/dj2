# world/bestiary.py
"""
OG System bestiary – loads monsters from 06_monsters.json.
Provides Monster class, lookup, filtering, and CR scaling.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from world.dnd_data import _get_monsters_data

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Monster class
# ----------------------------------------------------------------------
class Monster:
    """Represents a monster from the OG System bestiary."""
    def __init__(self, key: str, data: dict):
        self.key = key                     # original JSON key, e.g. "carrion_beetle_swarm"
        self.id = key                       # for convenience
        self.name = data.get("name", key.replace('_', ' ').title())
        self.attributes = data.get("attributes", {})
        self.hp = data.get("hp", 1)
        self.defense = data.get("defense", 10)
        self.armor = data.get("armor", 0)
        self.damage = data.get("damage", "1d4")
        self.special = data.get("special", [])
        self.tags = data.get("tags", [])
        self.cr = data.get("cr", 1)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON/storage."""
        return {
            "key": self.key,
            "id": self.id,
            "name": self.name,
            "attributes": self.attributes,
            "hp": self.hp,
            "defense": self.defense,
            "armor": self.armor,
            "damage": self.damage,
            "special": self.special,
            "tags": self.tags,
            "cr": self.cr
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Monster':
        """Deserialize from dictionary (used when loading stored encounters)."""
        # Create a minimal instance; the key may not be in the original JSON,
        # but we just need the data. We'll set key from the data.
        monster = cls(data.get("key", data.get("id", "unknown")), data)
        # Overwrite any attributes that might be missing in __init__
        for k, v in data.items():
            setattr(monster, k, v)
        return monster

    @classmethod
    def all(cls) -> List['Monster']:
        """Return list of all monsters from the JSON."""
        data = _get_monsters_data()
        monsters_data = data.get("monsters", {})
        return [cls(key, mdata) for key, mdata in monsters_data.items()]

    @classmethod
    def get(cls, monster_id: str) -> Optional['Monster']:
        """Fetch a monster by its JSON key (id)."""
        data = _get_monsters_data()
        monsters_data = data.get("monsters", {})
        if monster_id in monsters_data:
            return cls(monster_id, monsters_data[monster_id])
        return None

    @classmethod
    def find_by_name(cls, name: str) -> Optional['Monster']:
        """Case‑insensitive name search. Returns first match."""
        name_lower = name.lower()
        for m in cls.all():
            if m.name.lower() == name_lower:
                return m
        return None

    @classmethod
    def filter(cls, tags: List[str] = None, max_cr: int = None, min_cr: int = None) -> List['Monster']:
        """
        Return monsters that match all given tags and are within CR range.
        Tags are matched against the monster's tags list (any overlap).
        """
        result = []
        for m in cls.all():
            if tags:
                if not any(t in m.tags for t in tags):
                    continue
            if max_cr is not None and m.cr > max_cr:
                continue
            if min_cr is not None and m.cr < min_cr:
                continue
            result.append(m)
        return result

    @classmethod
    def scale(cls, monster_id: str, target_cr: int) -> 'Monster':
        """
        Return a copy of the monster scaled to the target CR.
        Implements scaling rules from 07_encounter.json:
          HP adjusted by ±20% per CR difference.
          Damage die step adjusted (d4→d6→d8→d10→d12→2d6→2d8 etc.) per 2 CR.
        """
        original = cls.get(monster_id)
        if not original:
            raise ValueError(f"Monster {monster_id} not found")

        cr_diff = target_cr - original.cr
        # Scale HP: ±20% per CR difference
        hp_multiplier = 1.0 + (cr_diff * 0.2)
        new_hp = max(1, int(original.hp * hp_multiplier))

        # Scale damage: adjust die step by floor(cr_diff/2)
        steps = cr_diff // 2
        new_damage = cls._adjust_damage_die(original.damage, steps)

        # Create a new monster instance (copy)
        scaled = cls(original.key, {
            "name": original.name,
            "attributes": original.attributes.copy(),
            "hp": new_hp,
            "defense": original.defense,
            "armor": original.armor,
            "damage": new_damage,
            "special": original.special.copy(),
            "tags": original.tags.copy(),
            "cr": target_cr
        })
        return scaled

    @staticmethod
    def _adjust_damage_die(damage_str: str, steps: int) -> str:
        """
        Move damage die up or down by steps (positive = bigger die).
        Handles simple dice strings like "d4", "2d6", "d8+2".
        For now we only adjust the die size; modifiers are kept.
        """
        import re
        match = re.match(r'(\d*)d(\d+)(.*)', damage_str)
        if not match:
            # If we can't parse, return unchanged
            return damage_str

        num_dice = match.group(1)
        if num_dice == '':
            num_dice = 1
        else:
            num_dice = int(num_dice)
        die_size = int(match.group(2))
        suffix = match.group(3)  # e.g., "+2"

        # Die progression: 4,6,8,10,12, then 2d6,2d8,2d10,2d12, etc.
        # We'll use a simple table for up to 3 steps; more complex later.
        # Steps: 0→d4, 1→d6, 2→d8, 3→d10, 4→d12, 5→2d6, 6→2d8, 7→2d10, 8→2d12, 9→3d8, 10→3d10, etc.
        # For simplicity, we'll just increase die size and eventually number of dice.
        base_idx = die_size // 2 - 2  # d4=0, d6=1, d8=2, d10=3, d12=4
        if base_idx < 0:
            base_idx = 0

        new_idx = base_idx + steps
        if new_idx < 0:
            new_idx = 0

        # Map index back to die string
        if new_idx < 5:
            new_die = [4,6,8,10,12][new_idx]
            new_num = num_dice
        else:
            # beyond d12, increase number of dice
            extra_steps = new_idx - 4  # after d12
            new_num = num_dice + (extra_steps // 2) + 1
            new_die = [6,8,10,12][extra_steps % 4]  # cycle through d6,d8,d10,d12

        if new_num == 1:
            die_str = f"d{new_die}"
        else:
            die_str = f"{new_num}d{new_die}"
        return die_str + suffix


# ----------------------------------------------------------------------
# Quick test / verification when run directly
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("Bestiary loaded. Monsters:")
    for m in Monster.all():
        print(f"  {m.name} (CR {m.cr}) - {m.damage}")

    # Test scaling
    goblin = Monster.get("carrion_beetle_swarm")  # example
    if goblin:
        scaled = Monster.scale(goblin.id, 3)
        print(f"\nScaled {goblin.name} from CR {goblin.cr} to CR 3: HP {scaled.hp}, damage {scaled.damage}")