import json
from pathlib import Path

MASTER_FILE = "og_system_master.json"
OUTPUT_DIR = Path("pieces")
OUTPUT_DIR.mkdir(exist_ok=True)

EXTRACTIONS = [
    # These lived inside the "og_system" object
    ("01_core.json", {
        "meta": "og_system.meta",
        "core_mechanics": "og_system.core_mechanics",
        "skills": "og_system.skills",
        "skill_generation": "og_system.skill_generation",
        "combat": "og_system.combat",
        "progression": "og_system.progression"
    }),
    ("02_classes.json", {"classes": "og_system.classes"}),
    ("03_races.json", {"races": "og_system.races"}),
    ("04_magic.json", {"magic": "og_system.magic"}),
    ("05_equipment.json", {"equipment": "og_system.equipment"}),
    ("06_monsters.json", {"monsters": "og_system.monsters"}),
    ("07_encounter.json", {
        "encounter_balance": "og_system.encounter_balance",
        "ai_protocol": "og_system.ai_protocol"
    }),
    # These live inside the "modules" object (at the root)
    ("08_exploration.json", {"exploration": "modules.exploration"}),
    ("09_social.json", {"social": "modules.social"}),
    ("10_crafting.json", {"crafting": "modules.crafting"}),
    ("11_settlement.json", {"settlement": "modules.settlement"}),
    # These live directly at the root
    ("12_engine.json", {"engine": "engine"}),
    ("13_index.json", {
        "index": "index",
        "markdownGenerator": "markdownGenerator"
    }),
]

def extract_piece(master, spec):
    """Extract fields from master according to spec with error handling"""
    result = {}
    for new_key, path in spec.items():
        keys = path.split(".")
        value = master
        try:
            for k in keys:
                value = value[k]
            result[new_key] = value
        except KeyError:
            print(f"  [!] Warning: Could not find '{path}' in JSON.")
            result[new_key] = None
    return result

def main():
    try:
        with open(MASTER_FILE) as f:
            # We load the WHOLE file here (the root)
            master = json.load(f)
    except FileNotFoundError:
        print(f"Error: {MASTER_FILE} not found.")
        return

    for filename, spec in EXTRACTIONS:
        piece = extract_piece(master, spec)
        with open(OUTPUT_DIR / filename, 'w') as f:
            json.dump(piece, f, indent=2)
        print(f"Extracted {filename}")
    
    print(f"\nAll pieces exported to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()