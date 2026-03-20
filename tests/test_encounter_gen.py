# test_encounter_gen.py
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent  # tests/ -> dj2/
sys.path.insert(0, str(project_root))

from world.encounter_generator import generate_encounter
from world.bestiary import Monster

# Ensure bestiary loads (optional, but good)
print("Monsters in bestiary:", len(Monster.all()))

# Sample context
context = {
    "point_id": "test_point_1",
    "party_level": 3,
    "party_size": 4,
    "region": {
        "danger_level": 0,
        "terrain": "forest",
        "faction": "goblins"
    },
    "point_type": "camp"
}

encounter = generate_encounter(context)

print(f"Encounter ID: {encounter.id}")
print(f"Difficulty: {encounter.difficulty}")
print(f"Loot table: {encounter.loot_table}")
print(f"Description: {encounter.description}")
print("Monsters:")
for m in encounter.monsters:
    # fetch full monster data for display
    monster_data = Monster.get(m.monster_id)
    print(f"  - {monster_data.name} (CR {monster_data.cr}) HP: {m.current_hp}")