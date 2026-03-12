
# og_data.py - replaces dnd_data.py interface with og_system JSON loading

"""
Object‑oriented access to OG System JSON data.
Loads from og_system JSON files, provides same interface as dnd_data.py
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Union

logger = logging.getLogger(__name__)

# Get the directory where this file (og_data.py) lives
_BASE_DIR = Path(__file__).parent
OG_SYSTEM_DIR = _BASE_DIR.parent / "og_system"

# ----------------------------------------------------------------------
# JSON Loading Helpers
# ----------------------------------------------------------------------
_og_cache = {}

def _load_og_json(filename: str) -> dict:
    """Load and cache OG system JSON files"""
    if filename in _og_cache:
        return _og_cache[filename]
    
    path = OG_SYSTEM_DIR / filename
    if not path.exists():
        # Try with number prefix
        for p in OG_SYSTEM_DIR.glob(f"*_{filename}"):
            path = p
            break
    
    if not path.exists():
        logger.error(f"OG System file not found: {filename}")
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    _og_cache[filename] = data
    return data

def _get_core_data() -> dict:
    """Load 01_core.json - attributes, skills, combat, progression"""
    return _load_og_json("01_core.json")

def _get_classes_data() -> dict:
    """Load 02_classes.json - all class definitions"""
    return _load_og_json("02_classes.json")

def _get_races_data() -> dict:
    """Load 03_races.json - all race definitions"""
    return _load_og_json("03_races.json")

def _get_magic_data() -> dict:
    """Load 04_magic.json - spell schools"""
    return _load_og_json("04_magic.json")

# ----------------------------------------------------------------------
# Attribute (replaces AbilityScore)
# ----------------------------------------------------------------------
class Attribute:
    """OG System attribute: Brawn, Finesse, Wits, Will"""
    
    def __init__(self, key: str, data: dict):
        self.key = key
        self.name = data.get("name", key.capitalize())
        self.abbreviation = data.get("abbreviation", key[0].upper())
        self.governs = data.get("governs", [])
        self.hp_per_point = data.get("hp_per_point", 0)
        self.sp_per_point = data.get("sp_per_point", 0)
        self.defense_contribution = data.get("defense_contribution", False)
        self.initiative_contribution = data.get("initiative_contribution", False)
    
    @property
    def lower_name(self) -> str:
        return self.name.lower()
    
    @classmethod
    def all(cls) -> List['Attribute']:
        core = _get_core_data()
        attrs = core.get("core_mechanics", {}).get("attributes", {})
        return [cls(k, v) for k, v in attrs.items()]
    
    @classmethod
    def get(cls, key: str) -> Optional['Attribute']:
        core = _get_core_data()
        attrs = core.get("core_mechanics", {}).get("attributes", {})
        if key.lower() in attrs:
            return cls(key.lower(), attrs[key.lower()])
        # Try by name
        for k, v in attrs.items():
            if v.get("name", "").lower() == key.lower():
                return cls(k, v)
        return None

# ----------------------------------------------------------------------
# Skill (OG System has 6 skills)
# ----------------------------------------------------------------------
class Skill:
    """OG System skill: Survival, Lore, Social, Craft, Stealth, Athletics"""
    
    def __init__(self, key: str, data: dict):
        self.key = key
        self.name = data.get("name", key.capitalize())
        self.covers = data.get("covers", [])
        self.typical_tn = data.get("typical_tn", "12")
        self.max_rank = data.get("max_rank", 3)
        self.starting_ranks = data.get("starting_ranks", 0)
    
    @classmethod
    def all(cls) -> List['Skill']:
        core = _get_core_data()
        skills = core.get("skills", {})
        return [cls(k, v) for k, v in skills.items()]
    
    @classmethod
    def get(cls, name: str) -> Optional['Skill']:
        core = _get_core_data()
        skills = core.get("skills", {})
        # Try by key
        if name.lower() in skills:
            return cls(name.lower(), skills[name.lower()])
        # Try by name
        for k, v in skills.items():
            if v.get("name", "").lower() == name.lower():
                return cls(k, v)
        return None

# ----------------------------------------------------------------------
# Race
# ----------------------------------------------------------------------
class Race:
    """OG System race with mechanical bonus"""
    
    def __init__(self, key: str, data: dict):
        self.key = key
        self.name = data.get("name", key.capitalize())
        self.mechanical_bonus = data.get("mechanical_bonus", {})
        self.knacks = data.get("knacks", [])
        self.tags = data.get("tags", [])
    
    @property
    def index(self) -> str:
        return self.key
    
    def subraces(self) -> List['Race']:
        """OG System doesn't have subraces, return empty list for compatibility"""
        return []
    
    @classmethod
    def all(cls) -> List['Race']:
        data = _get_races_data()
        races = data.get("races", {})
        return [cls(k, v) for k, v in races.items()]
    
    @classmethod
    def get(cls, key: str) -> Optional['Race']:
        data = _get_races_data()
        races = data.get("races", {})
        if key.lower() in races:
            return cls(key.lower(), races[key.lower()])
        # Try by name
        for k, v in races.items():
            if v.get("name", "").lower() == key.lower():
                return cls(k, v)
        return None

# ----------------------------------------------------------------------
# Class
# ----------------------------------------------------------------------
class OGClass:
    """OG System class: Warrior, Rogue, Mage, Priest, Ranger, Bard, Monk, Warlock"""
    
    def __init__(self, key: str, data: dict):
        self.key = key
        self.name = data.get("name", key.capitalize())
        self.hp_per_level = data.get("hp_per_level", 2)
        self.sp_per_level = data.get("sp_per_level", 0)
        self.core_mechanic = data.get("core_mechanic", {})
        self.starting_gear = data.get("starting_gear", [])
        self.subclasses = data.get("subclasses", {})
        self.capstones = data.get("capstones", {})
    
    @property
    def index(self) -> str:
        return self.key
    
    @property
    def hit_die(self) -> int:
        """Return effective hit die (hp_per_level * 4 roughly equivalent)"""
        return self.hp_per_level * 4
    
    def skill_choices(self) -> Dict[str, Any]:
        """OG System: 3 skills at rank 1 to start"""
        core = _get_core_data()
        skills = list(core.get("skills", {}).keys())
        return {
            "choose": 3,
            "from": [Skill(k, {"name": k.capitalize()}) for k in skills]
        }
    
    @classmethod
    def all(cls) -> List['OGClass']:
        data = _get_classes_data()
        classes = data.get("classes", {})
        return [cls(k, v) for k, v in classes.items()]
    
    @classmethod
    def get(cls, key: str) -> Optional['OGClass']:
        data = _get_classes_data()
        classes = data.get("classes", {})
        if key.lower() in classes:
            return cls(key.lower(), classes[key.lower()])
        # Try by name
        for k, v in classes.items():
            if v.get("name", "").lower() == key.lower():
                return cls(k, v)
        return None

# ----------------------------------------------------------------------
# Proficiency (compatibility layer)
# ----------------------------------------------------------------------
class Proficiency:
    """OG System doesn't have proficiencies like 5e, but we need compatibility"""
    
    def __init__(self, name: str, prof_type: str = "skill"):
        self.name = name
        self.type = prof_type
        self.reference = None
    
    @classmethod
    def get(cls, key: str) -> Optional['Proficiency']:
        # Check if it's a skill
        skill = Skill.get(key)
        if skill:
            return cls(skill.name, "Skills")
        return None
    
    @classmethod
    def all(cls) -> List['Proficiency']:
        return [cls(s.name, "Skills") for s in Skill.all()]

# ----------------------------------------------------------------------
# Trait (compatibility - OG System uses knacks)
# ----------------------------------------------------------------------
class Trait:
    """OG System knacks treated as traits for compatibility"""
    
    def __init__(self, name: str, desc: str = ""):
        self.name = name
        self.desc = [desc] if desc else []
        self.index = name.lower().replace(" ", "_")
    
    @classmethod
    def get(cls, key: str) -> Optional['Trait']:
        # Search in race knacks
        for race in Race.all():
            for knack in race.knacks:
                if knack.lower() == key.lower() or knack.lower().replace(" ", "_") == key.lower():
                    return cls(knack, f"Racial knack: {knack}")
        return None
    
    @classmethod
    def all(cls) -> List['Trait']:
        traits = []
        for race in Race.all():
            for knack in race.knacks:
                traits.append(cls(knack, f"Racial knack: {knack}"))
        return traits

# ----------------------------------------------------------------------
# Convenience functions for dropdown lists (same interface as dnd_data)
# ----------------------------------------------------------------------

def get_race_list() -> List[str]:
    """Return list of race names"""
    return [r.name for r in Race.all()]

def get_subraces_for_race(race_name: str) -> List[str]:
    """OG System doesn't have subraces, return empty list"""
    return []

def get_race_for_subrace(subrace_name: str) -> Optional[str]:
    """No subraces in OG System"""
    return None

def get_class_list() -> List[str]:
    """Return list of class names"""
    return [c.name for c in OGClass.all()]

def get_skill_list() -> List[str]:
    """Return list of skill names"""
    return [s.name for s in Skill.all()]

def get_ability_score_list() -> List[str]:
    """Return list of attribute keys (brawn, finesse, wits, will)"""
    return [a.key for a in Attribute.all()]

def get_ability_score_full_names() -> List[str]:
    """Return list of attribute full names (Brawn, Finesse, Wits, Will)"""
    return [a.name for a in Attribute.all()]

def get_ability_score_lower_names() -> List[str]:
    """Return list of lowercase attribute names"""
    return [a.lower_name for a in Attribute.all()]

# ----------------------------------------------------------------------
# Backgrounds (hardcoded - OG System doesn't define these)
# ----------------------------------------------------------------------
BACKGROUNDS = [
    "Acolyte", "Charlatan", "Criminal", "Entertainer", "Folk Hero",
    "Gladiator", "Guild Artisan", "Hermit", "Knight", "Noble",
    "Outlander", "Pirate", "Sage", "Sailor", "Soldier", "Urchin",
    "Mercenary", "Spy", "Cultist", "Hermit", "Wanderer"
]

def get_background_list() -> List[str]:
    return BACKGROUNDS

# ----------------------------------------------------------------------
# Validation functions (same interface as dnd_data)
# ----------------------------------------------------------------------

def validate_race(race_name: str) -> bool:
    return Race.get(race_name) is not None

def validate_class(class_name: str) -> bool:
    return OGClass.get(class_name) is not None

def validate_skill(skill_name: str) -> bool:
    return Skill.get(skill_name) is not None

def validate_ability_score(score_name: str) -> bool:
    return Attribute.get(score_name) is not None

def validate_spell(spell_name: str) -> bool:
    """Check if spell exists in magic schools"""
    magic = _get_magic_data()
    schools = magic.get("magic", {}).get("schools", {})
    for school_data in schools.values():
        for effect in school_data.get("effects", []):
            if effect.get("name", "").lower() == spell_name.lower():
                return True
    return False

def validate_trait(trait_name: str) -> bool:
    return Trait.get(trait_name) is not None

def validate_proficiency(prof_name: str) -> bool:
    return validate_skill(prof_name)

# ----------------------------------------------------------------------
# Legacy compatibility functions
# ----------------------------------------------------------------------

def get_class_object(class_name: str) -> Optional[OGClass]:
    """Return class object for character creation"""
    return OGClass.get(class_name)

def get_class_description(class_name: str) -> str:
    """Get description of class"""
    cls = OGClass.get(class_name)
    if cls and cls.core_mechanic:
        return cls.core_mechanic.get("description", f"A {class_name} character.")
    return f"A {class_name} character."

def get_spellcasting_ability(class_name: str) -> Optional[str]:
    """OG System: Mages/Priests use Wits, Warlocks use Will"""
    cls = OGClass.get(class_name)
    if not cls:
        return None
    if class_name.lower() in ["mage", "priest"]:
        return "WITS"
    elif class_name.lower() == "warlock":
        return "WILL"
    return None

def get_spell_list() -> List[str]:
    """Return list of all spell effect names"""
    spells = []
    magic = _get_magic_data()
    schools = magic.get("magic", {}).get("schools", {})
    for school_data in schools.values():
        for effect in school_data.get("effects", []):
            spells.append(effect.get("name", ""))
    return spells

def get_spell_description(spell_name: str) -> str:
    """Get description of a spell"""
    magic = _get_magic_data()
    schools = magic.get("magic", {}).get("schools", {})
    for school_data in schools.values():
        for effect in school_data.get("effects", []):
            if effect.get("name", "").lower() == spell_name.lower():
                return effect.get("description", "No description available.")
    return "No description available."

# ----------------------------------------------------------------------
# Semantic matching (stub - can be enhanced later)
# ----------------------------------------------------------------------

def semantic_match(raw: str, category: str, names: List[str], threshold: float = 0.7) -> Optional[str]:
    """Simple exact match fallback"""
    raw_lower = raw.lower()
    for name in names:
        if name.lower() == raw_lower:
            return name
    return None

def semantic_match_spell(raw: str) -> Optional[str]:
    return semantic_match(raw, "spells", get_spell_list())

def semantic_match_skill(raw: str) -> Optional[str]:
    return semantic_match(raw, "skills", get_skill_list())

def semantic_match_race(raw: str) -> Optional[str]:
    return semantic_match(raw, "races", get_race_list())

def semantic_match_subrace(raw: str) -> Optional[str]:
    return None  # No subraces

def semantic_match_class(raw: str) -> Optional[str]:
    return semantic_match(raw, "classes", get_class_list())

def semantic_match_trait(raw: str) -> Optional[str]:
    return semantic_match(raw, "traits", [t.name for t in Trait.all()])

def semantic_match_proficiency(raw: str) -> Optional[str]:
    return semantic_match_skill(raw)

def semantic_match_ability_score(raw: str) -> Optional[str]:
    return semantic_match(raw, "attributes", get_ability_score_full_names())

def semantic_match_fighting_style(raw: str, class_name: str = None) -> Optional[str]:
    return None  # No fighting styles

# ----------------------------------------------------------------------
# Initialization check
# ----------------------------------------------------------------------
def verify_data():
    """Force load all data and log counts."""
    races = Race.all()
    classes = OGClass.all()
    skills = Skill.all()
    attrs = Attribute.all()
    logger.info(f"Loaded {len(races)} races from OG System.")
    logger.info(f"Loaded {len(classes)} classes from OG System.")
    logger.info(f"Loaded {len(skills)} skills from OG System.")
    logger.info(f"Loaded {len(attrs)} attributes from OG System.")
    logger.info(f"Attributes: {[a.name for a in attrs]}")

if __name__ == "__main__":
    print(f"Looking for og_system at: {OG_SYSTEM_DIR}")
    print(f"Exists? {OG_SYSTEM_DIR.exists()}")
    verify_data()   # this loads JSON and logs counts
