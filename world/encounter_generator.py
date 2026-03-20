# world/encounter_generator.py
"""
Encounter generator – creates a concrete Encounter object from context.
Uses bestiary and scaling rules from 07_encounter.json.
"""

import json
import random
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from world.dnd_data import _get_encounter_data
from world.bestiary import Monster
from world.encounter_models import Encounter, MonsterInstance

logger = logging.getLogger(__name__)

_ENCOUNTER_DATA = _get_encounter_data().get("encounter_balance", {})

# ----------------------------------------------------------------------
# Tag mapping from point type to monster tags (biasing)
# ----------------------------------------------------------------------
TYPE_TAG_MAP = {
    "camp": ["humanoid", "goblin", "orc", "beast", "giant", "fey", "monstrosity", "construct"],
    "lair": ["beast", "monstrosity", "dragon", "giant", "aberration"],
    "ruin": ["undead", "construct", "aberration", "ooze"],
    "hunting_ground": ["beast", "monstrosity", "humanoid"],
    "ambush_site": ["humanoid", "beast", "goblin", "orc", "fey"],
    "cave": ["beast", "monstrosity", "humanoid", "giant", "ooze"],
    "default": []
}

# ----------------------------------------------------------------------
# Main generator function
# ----------------------------------------------------------------------
def generate_encounter(context: dict) -> Encounter:
    """
    Generate an Encounter based on the provided context.
    """
    point_id = context["point_id"]
    party_level = context["party_level"]
    party_size = context.get("party_size", 4)
    region = context.get("region", {})
    point_type = context.get("point_type", "default")
    difficulty_mod = region.get("danger_level", 0)

    # 1. Determine target CR
    target_cr = party_level + difficulty_mod
    if target_cr < 1:
        target_cr = 1

    # 2. Apply group size multiplier to get number of monsters
    multiplier_data = _ENCOUNTER_DATA.get("multipliers", {})
    if party_size == 1:
        mult_key = "single"
    elif party_size == 2:
        mult_key = "pair"
    elif 3 <= party_size <= 6:
        mult_key = "group_3_6"
    elif 7 <= party_size <= 12:
        mult_key = "group_7_12"
    else:
        mult_key = "army_13_plus"
    multiplier = multiplier_data.get(mult_key, 1.0)
    base_count = max(1, int(round(party_size / 2.0 * multiplier)))
    num_monsters = min(base_count, 6)

    # 3. Build candidate list
    tags = TYPE_TAG_MAP.get(point_type, TYPE_TAG_MAP["default"])
    candidates = Monster.filter(tags=tags, min_cr=target_cr-2, max_cr=target_cr+2)
    MIN_CANDIDATES = 3
    if len(candidates) < MIN_CANDIDATES:
        candidates = Monster.filter(min_cr=target_cr-2, max_cr=target_cr+2)
    if not candidates:
        candidates = Monster.all()

    # 4. Wildcard chance (15%)
    WILDCARD_CHANCE = 0.15
    wildcard = random.random() < WILDCARD_CHANCE

    monster_instances = []
    monster_names = []

    if wildcard:
        # Entire group random
        for _ in range(num_monsters):
            base = random.choice(Monster.filter(min_cr=target_cr-2, max_cr=target_cr+2) or Monster.all())
            scaled = Monster.scale(base.id, target_cr)
            monster_instances.append(MonsterInstance(scaled.id, scaled.hp))
            monster_names.append(base.name)
        description = f"You encounter a bizarre assortment of creatures: {', '.join(monster_names)}."
    else:
        # Thematic group: pick a primary, then others that share a tag
        primary = random.choice(candidates)
        primary_tags = primary.tags
        scaled_primary = Monster.scale(primary.id, target_cr)
        monster_instances.append(MonsterInstance(scaled_primary.id, scaled_primary.hp))
        monster_names.append(primary.name)

        for _ in range(num_monsters - 1):
            # Find compatible monsters (share a tag with primary)
            compatible = [m for m in candidates if set(m.tags) & set(primary_tags)]
            if not compatible:
                compatible = candidates
            base = random.choice(compatible)
            scaled = Monster.scale(base.id, target_cr)
            monster_instances.append(MonsterInstance(scaled.id, scaled.hp))
            monster_names.append(base.name)

        description = f"You encounter a group of creatures: {', '.join(monster_names)}."

    # 5. Determine loot table
    if target_cr <= 5:
        loot_table = "CR1-5"
    elif target_cr <= 10:
        loot_table = "CR6-10"
    elif target_cr <= 15:
        loot_table = "CR11-15"
    else:
        loot_table = "CR16+"

    # 6. Create encounter
    encounter = Encounter(point_id, float(target_cr), loot_table)
    for mi in monster_instances:
        encounter.add_monster(mi)
    encounter.description = description

    return encounter