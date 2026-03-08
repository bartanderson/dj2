"""
Centralized access to D&D 5e game data from local cache (fetched from 5e API).
Provides lists, validation, and details for races, classes, spells, etc.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

from dnd_character import CLASSES
from dnd_character.spellcasting import SPELLS

logger = logging.getLogger(__name__)

# Paths to cached data
CACHE_DIR = Path("data/dnd_cache")
RACES_FILE = CACHE_DIR / "races.json"
SUBRACES_FILE = CACHE_DIR / "subraces.json"
SKILLS_FILE =  CACHE_DIR / "skills.json"
ABILITY_SCORES_FILE =  CACHE_DIR / "ability-scores.json"
TRAITS_FILE =  CACHE_DIR / "traits.json"
PROFICIENCIES_FILE =  CACHE_DIR / "proficiencies.json"

# ----------------------------------------------------------------------
# Race data (loaded from cache)
# ----------------------------------------------------------------------
_RACES = None
_SUBRACES = None
_SKILLS = None
_ABILITY_SCORES = None
_TRAITS = None
_PROFICIENCIES = None

def _load_races():
    """Load race data from cache file."""
    global _RACES
    if _RACES is not None:
        return
    if not RACES_FILE.exists():
        logger.error(f"Race cache file not found: {RACES_FILE}. Run tools/fetch_dnd_data.py first.")
        _RACES = []
        return
    with open(RACES_FILE) as f:
        _RACES = json.load(f)
    logger.info(f"Loaded {len(_RACES)} races from cache.")

def _load_subraces():
    """Load subrace data from cache file."""
    global _SUBRACES
    if _SUBRACES is not None:
        return
    if not SUBRACES_FILE.exists():
        logger.error(f"Subrace cache file not found: {SUBRACES_FILE}. Run tools/fetch_dnd_data.py first.")
        _SUBRACES = []
        return
    with open(SUBRACES_FILE) as f:
        _SUBRACES = json.load(f)
    logger.info(f"Loaded {len(_SUBRACES)} subraces from cache.")

def _load_skills():
    """Load skills data from cache file."""
    global _SKILLS
    if _SKILLS is not None:
        return
    if not SKILLS_FILE.exists():
        logger.error(f"Skills cache file not found: {SKILLS_FILE}. Run tools/fetch_dnd_data.py first.")
        _SKILLS = []
        return
    with open(SKILLS_FILE) as f:
        _SKILLS = json.load(f)
    logger.info(f"Loaded {len(_SKILLS)} skills from cache.")

def _load_ability_scores():
    """Load ability scores data from cache file."""
    global _ABILITY_SCORES
    if _ABILITY_SCORES is not None:
        return
    if not ABILITY_SCORES_FILE.exists():
        logger.error(f"Ability scores cache file not found: {ABILITY_SCORES_FILE}. Run tools/fetch_dnd_data.py first.")
        _ABILITY_SCORES = []
        return
    with open(ABILITY_SCORES_FILE) as f:
        _ABILITY_SCORES = json.load(f)
    logger.info(f"Loaded {len(_ABILITY_SCORES)} ability scores from cache.")

def _load_traits():
    """Load traits data from cache file."""
    global _TRAITS
    if _TRAITS is not None:
        return
    if not TRAITS_FILE.exists():
        logger.error(f"Traits cache file not found: {TRAITS_FILE}. Run tools/fetch_dnd_data.py first.")
        _TRAITS = []
        return
    with open(TRAITS_FILE) as f:
        _TRAITS = json.load(f)
    logger.info(f"Loaded {len(_TRAITS)} traits from cache.")

def _load_proficiencies():
    """Load proficiencies data from cache file."""
    global _PROFICIENCIES
    if _PROFICIENCIES is not None:
        return
    if not PROFICIENCIES_FILE.exists():
        logger.error(f"Proficiencies cache file not found: {PROFICIENCIES_FILE}. Run tools/fetch_dnd_data.py first.")
        _PROFICIENCIES = []
        return
    with open(PROFICIENCIES_FILE) as f:
        _PROFICIENCIES = json.load(f)
    logger.info(f"Loaded {len(_PROFICIENCIES)} proficiencies from cache.")

def get_race_list() -> List[str]:
    """Return a list of all race names (capitalized as in the API)."""
    _load_races()
    return [race["name"] for race in _RACES]

def get_subrace_list() -> List[str]:
    """Return list of all subrace names (e.g., 'High Elf', 'Hill Dwarf')."""
    _load_subraces()
    return [s["name"] for s in _SUBRACES]

def get_subraces_for_race(race_name: str) -> List[str]:
    """Return list of subrace names that belong to a given base race."""
    _load_races()
    _load_subraces()
    race = get_race_details(race_name)
    if not race:
        return []
    # Subraces are listed under the race's "subraces" array
    return [sub["name"] for sub in race.get("subraces", [])]

def get_skill_list() -> List[str]:
    _load_skills()
    return [s["name"] for s in _SKILLS]

def get_ability_scores_list() -> List[str]:
    _load_ability_scores()
    return [s["name"] for s in _ABILITY_SCORES]

def get_traits_list() -> List[str]:
    _load_traits()
    return [s["name"] for s in _TRAITS]

def get_proficiencies_list() -> List[str]:
    _load_proficiencies()
    return [s["name"] for s in _PROFICIENCIES]

def get_race_details(race_name: str) -> Optional[Dict]:
    """Return the full details dict for a race (case‑insensitive)."""
    _load_races()
    name_lower = race_name.lower()
    for race in _RACES:
        if race["name"].lower() == name_lower:
            return race
    return None

def validate_race(race_name: str) -> bool:
    """Check if a base race name exists."""
    _load_races()
    return any(r["name"].lower() == race_name.lower() for r in _RACES)

def validate_subrace(subrace_name: str, race_name: str = None) -> bool:
    """
    Validate a subrace name.
    If race_name is given, also ensure it belongs to that race.
    """
    _load_subraces()
    # Find the subrace in the global list
    sub = None
    for s in _SUBRACES:
        if s["name"].lower() == subrace_name.lower():
            sub = s
            break
    if not sub:
        return False
    if race_name:
        # Check that the subrace belongs to the given race
        race_of_sub = sub.get("race", {}).get("name")
        if not race_of_sub:
            return False
        return race_of_sub.lower() == race_name.lower()
    return True

def validate_skill(skill_name: str) -> bool:
    _load_skills()
    return any(s["name"].lower() == skill_name.lower() for s in _SKILLS)

def validate_ability_score(score_name: str) -> bool:
    _load_ability_scores()
    return any(s["name"].lower() == score_name.lower() for s in _ABILITY_SCORES)

def validate_trait(trait_name: str) -> bool:
    _load_traits()
    return any(t["name"].lower() == trait_name.lower() for t in _TRAITS)

def validate_proficiency(prof_name: str) -> bool:
    _load_proficiencies()
    return any(p["name"].lower() == prof_name.lower() for p in _PROFICIENCIES)

def get_race_description(race_name: str) -> str:
    """Return a short description (first sentence of the race's 'flavor' text)."""
    race = get_race_details(race_name)
    if race and "flavor" in race:
        return race["flavor"].split('.')[0] + '.'
    return f"A {race_name} character with unique traits."

def get_ability_bonuses(race_name: str, subrace_name: str = None) -> Dict[str, int]:
    """Return a dict of ability score bonuses for a race/subrace."""
    bonuses = {}
    race = get_race_details(race_name)
    if not race:
        return bonuses
    # Race ability bonuses
    for ab in race.get("ability_bonuses", []):
        bonuses[ab["ability_score"]["name"]] = ab["bonus"]
    # Subrace additional bonuses
    if subrace_name:
        _load_subraces()
        for sub in _SUBRACES:
            if sub["name"].lower() == subrace_name.lower():
                for ab in sub.get("ability_bonuses", []):
                    bonuses[ab["ability_score"]["name"]] = bonuses.get(ab["ability_score"]["name"], 0) + ab["bonus"]
                break
    return bonuses

# ----------------------------------------------------------------------
# Class helpers (from dnd_character)
# ----------------------------------------------------------------------

def get_class_list() -> List[str]:
    return list(CLASSES.keys())

def validate_class(class_name: str) -> bool:
    return class_name.lower() in CLASSES

def get_class_object(class_name: str) -> Optional[Any]:
    return CLASSES.get(class_name.lower())

def get_class_description(class_name: str) -> str:
    cls_obj = get_class_object(class_name)
    if cls_obj and cls_obj.__doc__:
        desc = cls_obj.__doc__.strip().split('.')[0]
        if desc:
            return desc + '.'
    return f"A {class_name} character."

def get_spellcasting_ability(class_name: str) -> Optional[str]:
    cls_obj = get_class_object(class_name)
    if not cls_obj or not hasattr(cls_obj, 'spellcasting') or not cls_obj.spellcasting:
        return None
    ability_dict = cls_obj.spellcasting.get('spellcasting_ability')
    if ability_dict:
        return ability_dict.get('name', '').upper()
    return None

def get_classes_by_criterion(criterion: str) -> List[str]:
    # Can be left empty or removed; not critical.
    return []

# ----------------------------------------------------------------------
# Spell helpers (from dnd_character)
# ----------------------------------------------------------------------

def get_spell_list() -> List[str]:
    return list(SPELLS.keys())

def validate_spell(spell_name: str) -> bool:
    return spell_name.lower() in SPELLS

def get_spell_description(spell_name: str) -> str:
    spell = SPELLS.get(spell_name.lower())
    if spell and hasattr(spell, 'desc') and spell.desc:
        full_desc = ' '.join(spell.desc)
        return full_desc[:200] + ('...' if len(full_desc) > 200 else '')
    return "No description available."

from dnd_character.spellcasting import spells_for_class_level

def get_cantrips(class_name: str) -> List[str]:
    spells = spells_for_class_level(class_name.lower(), 0)
    return [spell.name for spell in spells]

def get_class_spells(class_name: str, level: int) -> List[str]:
    spells = spells_for_class_level(class_name.lower(), level)
    return [spell.name for spell in spells]

# ----------------------------------------------------------------------
# Initialization check
# ----------------------------------------------------------------------
def verify_data():
    _load_races()
    _load_subraces()
    _load_skills()
    _load_ability_scores()
    _load_traits()
    _load_proficiencies()
    logger.info(f"Loaded {len(CLASSES)} classes: {', '.join(CLASSES.keys())}")
    logger.info(f"Loaded {len(SPELLS)} spells.")
    logger.info(f"Loaded {len(_RACES)} races.")
    logger.info(f"Loaded {len(_SUBRACES)} subraces.")
    logger.info(f"Loaded {len(_SKILLS)} skills.")
    logger.info(f"Loaded {len(_ABILITY_SCORES)} ability scores.")
    logger.info(f"Loaded {len(_TRAITS)} traits.")
    logger.info(f"Loaded {len(_PROFICIENCIES)} proficiencies.")