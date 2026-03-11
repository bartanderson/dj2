"""
Object‑oriented access to cached D&D 5e data from the 5e API.
All data is loaded lazily from the JSON files in CACHE_DIR.
Relationships (e.g., skill -> ability score) are resolved as object references.
"""

import json
import logging
import pickle
import random
from pathlib import Path
from typing import List, Dict, Optional, Any, Union

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

from dnd_character import CLASSES as LEGACY_CLASSES
from dnd_character.spellcasting import SPELLS

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/dnd_cache")

# ----------------------------------------------------------------------
# Embedding model (lazy loaded)
# ----------------------------------------------------------------------
_EMBEDDER = None

def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = SentenceTransformer('all-MiniLM-L6-v2')
    return _EMBEDDER

# ----------------------------------------------------------------------
# Base class for all cached objects
# ----------------------------------------------------------------------
class DnDObject:
    """Base class for all cached objects. Subclasses define their own _cache and _data_file."""
    _data_file = None  # to be overridden

    @classmethod
    def _load_json(cls):
        """Load the JSON file for this class and return the list of raw dicts."""
        if cls._data_file is None:
            raise NotImplementedError(f"{cls.__name__} must set _data_file")
        path = CACHE_DIR / cls._data_file
        if not path.exists():
            logger.error(f"Cache file not found: {path}")
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def _build_cache(cls):
        """Create instances from raw JSON and store them in the class's _cache by index."""
        if hasattr(cls, '_cache') and cls._cache:
            return
        # Initialize cache if not present
        if not hasattr(cls, '_cache'):
            cls._cache = {}
        raw_list = cls._load_json()
        for raw in raw_list:
            idx = raw.get("index")
            if idx:
                cls._cache[idx] = cls(raw)

    @classmethod
    def get(cls, index: str) -> Optional['DnDObject']:
        """Retrieve an object by its API index (e.g., 'fighter', 'acrobatics')."""
        cls._build_cache()
        return cls._cache.get(index)

    @classmethod
    def all(cls) -> List['DnDObject']:
        """Return a list of all objects of this type."""
        cls._build_cache()
        return list(cls._cache.values())

    @classmethod
    def names(cls) -> List[str]:
        """Return a list of all object names (for dropdowns)."""
        return [obj.name for obj in cls.all()]

    def __init__(self, data: dict):
        self._data = data
        self.index = data.get("index")
        self.name = data.get("name")
        self.url = data.get("url")

# ----------------------------------------------------------------------
# Ability Score
# ----------------------------------------------------------------------
class AbilityScore(DnDObject):
    _cache = {}
    _data_file = "ability-scores.json"

    def __init__(self, data: dict):
        super().__init__(data)
        self.full_name = data.get("full_name", self.name)  # e.g., "STRENGTH" -> "Strength"
        self.desc = data.get("desc", [])

    @property
    def lower_name(self) -> str:
        """Return lowercase full name (e.g., 'strength') for use in form fields."""
        return self.full_name.lower()

# ----------------------------------------------------------------------
# Skill
# ----------------------------------------------------------------------
class Skill(DnDObject):
    _cache = {}
    _data_file = "skills.json"

    def __init__(self, data: dict):
        super().__init__(data)
        # Resolve ability score reference
        ability_ref = data.get("ability_score")
        if ability_ref and isinstance(ability_ref, dict):
            self.ability_score = AbilityScore.get(ability_ref["index"])
        else:
            self.ability_score = None
        self.desc = data.get("desc", [])

# ----------------------------------------------------------------------
# Proficiency
# ----------------------------------------------------------------------
class Proficiency(DnDObject):
    _cache = {}
    _data_file = "proficiencies.json"

    def __init__(self, data: dict):
        super().__init__(data)
        self.type = data.get("type")  # e.g., "Skills", "Armor", "Weapons"
        ref = data.get("reference")
        if ref and isinstance(ref, dict):
            self.reference = {
                "index": ref.get("index"),
                "name": ref.get("name")
            }
        else:
            self.reference = None

# ----------------------------------------------------------------------
# Trait
# ----------------------------------------------------------------------
class Trait(DnDObject):
    _cache = {}
    _data_file = "traits.json"

    def __init__(self, data: dict):
        super().__init__(data)
        self.desc = data.get("desc", [])

# ----------------------------------------------------------------------
# Race
# ----------------------------------------------------------------------
class Race(DnDObject):
    _cache = {}
    _data_file = "races.json"

    def __init__(self, data: dict):
        super().__init__(data)
        self.speed = data.get("speed")
        self.ability_bonuses = data.get("ability_bonuses", [])
        self.alignment = data.get("alignment")
        self.age = data.get("age")
        self.size = data.get("size")
        self.size_description = data.get("size_description")
        # Languages
        self.languages = []
        for lang_ref in data.get("languages", []):
            self.languages.append(lang_ref.get("name"))
        self.language_desc = data.get("language_desc")
        # Traits
        self.traits = []
        for trait_ref in data.get("traits", []):
            trait = Trait.get(trait_ref["index"])
            if trait:
                self.traits.append(trait)
        # Subraces (indices for lazy loading)
        self.subrace_indices = [sub["index"] for sub in data.get("subraces", [])]

    def subraces(self) -> List['Subrace']:
        """Return list of Subrace objects belonging to this race."""
        result = []
        for idx in self.subrace_indices:
            sub = Subrace.get(idx)
            if sub:
                result.append(sub)
        return result

# ----------------------------------------------------------------------
# Subrace
# ----------------------------------------------------------------------
class Subrace(DnDObject):
    _cache = {}
    _data_file = "subraces.json"

    def __init__(self, data: dict):
        super().__init__(data)
        self.desc = data.get("desc", "")
        race_ref = data.get("race")
        if race_ref and isinstance(race_ref, dict):
            self.race = Race.get(race_ref["index"])
        else:
            self.race = None
        self.ability_bonuses = data.get("ability_bonuses", [])
        self.traits = []
        for trait_ref in data.get("racial_traits", []):
            trait = Trait.get(trait_ref["index"])
            if trait:
                self.traits.append(trait)

# ----------------------------------------------------------------------
# Class
# ----------------------------------------------------------------------
class DnDClass(DnDObject):
    _cache = {}
    _data_file = "classes.json"

    def __init__(self, data: dict):
        super().__init__(data)
        self.hit_die = data.get("hit_die")
        self.class_levels_url = data.get("class_levels")

        # Saving throws
        self.saving_throws = []
        for st_ref in data.get("saving_throws", []):
            ab = AbilityScore.get(st_ref["index"])
            if ab:
                self.saving_throws.append(ab)

        # Proficiencies (automatic)
        self.proficiencies = []
        for prof_ref in data.get("proficiencies", []):
            prof = Proficiency.get(prof_ref["index"])
            if prof:
                self.proficiencies.append(prof)

        # Proficiency choices (skills, etc.)
        self.proficiency_choices = data.get("proficiency_choices", [])

    def skill_choices(self) -> Dict[str, Any]:
        """
        Return a dict with 'choose' (int) and 'from' (list of Skill objects)
        for the first proficiency choice that is of type 'proficiencies' and
        refers to skills.
        """
        for choice in self.proficiency_choices:
            if choice.get("type") != "proficiencies":
                continue
            choose = choice.get("choose", 0)
            options = []
            for opt in choice.get("from", {}).get("options", []):
                if opt.get("option_type") == "reference":
                    item = opt.get("item", {})
                    prof = Proficiency.get(item.get("index"))
                    if prof and prof.type == "Skills" and prof.reference:
                        skill = Skill.get(prof.reference["index"])
                        if skill:
                            options.append(skill)
            return {"choose": choose, "from": options}
        return {"choose": 0, "from": []}

# ----------------------------------------------------------------------
# Fighting styles (hardcoded fallback)
# ----------------------------------------------------------------------
FALLBACK_FIGHTING_STYLES = {
    "fighter": ["Archery", "Defense", "Dueling", "Great Weapon Fighting", "Protection", "Two-Weapon Fighting"],
    "paladin": ["Defense", "Dueling", "Great Weapon Fighting", "Protection"],
    "ranger": ["Archery", "Defense", "Dueling", "Two-Weapon Fighting"]
}

def get_fighting_styles_for_class(class_name: str) -> List[str]:
    return FALLBACK_FIGHTING_STYLES.get(class_name.lower(), [])

# ----------------------------------------------------------------------
# Backgrounds (hardcoded)
# ----------------------------------------------------------------------
BACKGROUNDS = [
    "Acolyte", "Charlatan", "Criminal", "Entertainer", "Folk Hero",
    "Gladiator", "Guild Artisan", "Hermit", "Knight", "Noble",
    "Outlander", "Pirate", "Sage", "Sailor", "Soldier", "Urchin"
]

def get_background_list() -> List[str]:
    return BACKGROUNDS

# ----------------------------------------------------------------------
# Convenience functions for dropdown lists
# ----------------------------------------------------------------------
def get_race_list() -> List[str]:
    return [r.name for r in Race.all()]

def get_subraces_for_race(race_name: str) -> List[str]:
    race = Race.get(race_name.lower())
    if race:
        return [s.name for s in race.subraces()]
    return []

def get_class_list() -> List[str]:
    return [c.name for c in DnDClass.all()]

def get_skill_list() -> List[str]:
    # Direct JSON load to avoid any cache pollution
    path = CACHE_DIR / "skills.json"
    if not path.exists():
        logger.error(f"Skills file not found: {path}")
        return []
    with open(path, 'r', encoding='utf-8') as f:
        skills = json.load(f)
    return [s["name"] for s in skills]

def get_ability_score_list() -> List[str]:
    """Return list of ability score names as they appear in the API (e.g., 'STR')."""
    return [a.name for a in AbilityScore.all()]

def get_ability_score_full_names() -> List[str]:
    """Return list of full names (e.g., 'Strength')."""
    return [a.full_name for a in AbilityScore.all()]

def get_ability_score_lower_names() -> List[str]:
    """Return list of lowercase full names (e.g., 'strength') for form fields."""
    return [a.lower_name for a in AbilityScore.all()]

# ----------------------------------------------------------------------
# Validation (exact match)
# ----------------------------------------------------------------------
def validate_race(race_name: str) -> bool:
    return Race.get(race_name.lower()) is not None

def validate_subrace(subrace_name: str, race_name: str = None) -> bool:
    sub = Subrace.get(subrace_name.lower())
    if not sub:
        return False
    if race_name:
        return sub.race and sub.race.index == race_name.lower()
    return True

def validate_class(class_name: str) -> bool:
    return DnDClass.get(class_name.lower()) is not None

def validate_skill(skill_name: str) -> bool:
    # Use direct JSON to avoid cache issues
    all_skills = get_skill_list()
    return skill_name in all_skills

def validate_ability_score(score_name: str) -> bool:
    return AbilityScore.get(score_name.lower()) is not None

def validate_spell(spell_name: str) -> bool:
    return spell_name.lower() in SPELLS

def validate_trait(trait_name: str) -> bool:
    return Trait.get(trait_name.lower()) is not None

def validate_proficiency(prof_name: str) -> bool:
    return Proficiency.get(prof_name.lower()) is not None

# ----------------------------------------------------------------------
# Embedding-based semantic matching
# ----------------------------------------------------------------------
def _compute_embeddings(items: List[str], cache_name: str) -> Dict[str, np.ndarray]:
    cache_file = CACHE_DIR / f"{cache_name}_embeddings.pkl"
    if cache_file.exists():
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    embedder = _get_embedder()
    embeddings = embedder.encode(items)
    result = {item: emb for item, emb in zip(items, embeddings)}
    with open(cache_file, 'wb') as f:
        pickle.dump(result, f)
    return result

def _get_embeddings(category: str, names: List[str]) -> Dict[str, np.ndarray]:
    if not hasattr(_get_embeddings, "cache"):
        _get_embeddings.cache = {}
    if category not in _get_embeddings.cache:
        _get_embeddings.cache[category] = _compute_embeddings(names, category)
    return _get_embeddings.cache[category]

def semantic_match(raw: str, category: str, names: List[str], threshold: float = 0.7) -> Optional[str]:
    if not names:
        return None
    embeddings = _get_embeddings(category, names)
    embedder = _get_embedder()
    raw_emb = embedder.encode([raw])
    best_name = None
    best_score = -1
    for name, emb in embeddings.items():
        score = cosine_similarity(raw_emb, emb.reshape(1, -1))[0][0]
        if score > best_score:
            best_score = score
            best_name = name
    if best_score >= threshold:
        return best_name
    return None

# ----------------------------------------------------------------------
# Category-specific semantic matchers
# ----------------------------------------------------------------------
def semantic_match_spell(raw: str) -> Optional[str]:
    names = list(SPELLS.keys())
    return semantic_match(raw, "spells", names)

def semantic_match_skill(raw: str) -> Optional[str]:
    names = get_skill_list()
    return semantic_match(raw, "skills", names)

def semantic_match_race(raw: str) -> Optional[str]:
    names = get_race_list()
    return semantic_match(raw, "races", names)

def semantic_match_subrace(raw: str) -> Optional[str]:
    names = [s.name for s in Subrace.all()]
    return semantic_match(raw, "subraces", names)

def semantic_match_class(raw: str) -> Optional[str]:
    names = get_class_list()
    return semantic_match(raw, "classes", names)

def semantic_match_trait(raw: str) -> Optional[str]:
    names = [t.name for t in Trait.all()]
    return semantic_match(raw, "traits", names)

def semantic_match_proficiency(raw: str) -> Optional[str]:
    names = [p.name for p in Proficiency.all()]
    return semantic_match(raw, "proficiencies", names)

def semantic_match_ability_score(raw: str) -> Optional[str]:
    names = get_ability_score_list()
    return semantic_match(raw, "ability_scores", names)

def semantic_match_fighting_style(raw: str, class_name: str = None) -> Optional[str]:
    if class_name:
        names = get_fighting_styles_for_class(class_name)
    else:
        all_styles = set()
        for styles in FALLBACK_FIGHTING_STYLES.values():
            all_styles.update(styles)
        names = list(all_styles)
    return semantic_match(raw, "fighting_styles", names)

# ----------------------------------------------------------------------
# Spell helpers (from dnd_character)
# ----------------------------------------------------------------------
def get_spell_list() -> List[str]:
    return list(SPELLS.keys())

def get_spell_description(spell_name: str) -> str:
    spell = SPELLS.get(spell_name.lower())
    if spell and hasattr(spell, 'desc') and spell.desc:
        full_desc = ' '.join(spell.desc)
        return full_desc[:200] + ('...' if len(full_desc) > 200 else '')
    return "No description available."

# ----------------------------------------------------------------------
# Class helpers (from legacy dnd_character)
# ----------------------------------------------------------------------
def get_legacy_class_list() -> List[str]:
    return list(LEGACY_CLASSES.keys())

def get_class_object(class_name: str) -> Optional[Any]:
    return LEGACY_CLASSES.get(class_name.lower())

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

# ----------------------------------------------------------------------
# Initialization check (optional)
# ----------------------------------------------------------------------
def verify_data():
    """Force load all caches and log counts."""
    races = Race.all()
    subraces = Subrace.all()
    classes = DnDClass.all()
    skills = Skill.all()
    abilities = AbilityScore.all()
    traits = Trait.all()
    proficiencies = Proficiency.all()
    logger.info(f"Loaded {len(races)} races.")
    logger.info(f"Loaded {len(subraces)} subraces.")
    logger.info(f"Loaded {len(classes)} classes.")
    logger.info(f"Loaded {len(skills)} skills.")
    logger.info(f"Loaded {len(abilities)} ability scores.")
    logger.info(f"Loaded {len(traits)} traits.")
    logger.info(f"Loaded {len(proficiencies)} proficiencies.")
    logger.info(f"Loaded {len(SPELLS)} spells from dnd_character.")
    logger.info(f"Loaded {len(LEGACY_CLASSES)} legacy classes from dnd_character.")