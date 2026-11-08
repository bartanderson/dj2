"""OG System Character class using six-ability model."""
import uuid
import random
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from world import dnd_data

logger = logging.getLogger(__name__)

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
SCORE_MIN, SCORE_MAX = 3, 18


def ability_modifier(score: int) -> int:
    """floor((score - 10) / 2). Uses // because Python floors negatives correctly."""
    return (score - 10) // 2


def proficiency_bonus_for_level(level: int) -> int:
    """Level 1-4: +2, 5-8: +3, 9-12: +4, 13-16: +5, 17-20: +6."""
    return 2 + (max(1, min(20, level)) - 1) // 4

@dataclass
class InventoryItem:
    name: str
    description: str = ""
    quantity: int = 1
    type: str = "adventuring_gear"
    equipped: bool = False
    slot: Optional[str] = None
    cost: int = 0


class Character:
    """Six-ability OG System character."""

    def __init__(
        self,
        name: str,
        race: str,
        classs: Any,
        level: int = 1,
        background: str = "unknown",
        player_id: Optional[str] = None,
        owner_id: Optional[str] = None,
        currency: int = 100,
        # ---- Canonical abilities (post-racial) ----
        abilities: Optional[Dict[str, int]] = None,
        save_proficiencies: Optional[List[str]] = None,
        skill_proficiencies: Optional[List[str]] = None,
        skill_expertise: Optional[List[str]] = None,
        initiative_proficient: Optional[bool] = None,
        # ---- Startup control ----
        add_starting_gear: bool = True,
        # ---- Narrative / cosmetic ----
        age: Optional[int] = None,
        gender: Optional[str] = None,
        description: Optional[str] = None,
        alignment: Optional[str] = None,
        backstory: Optional[Dict] = None,
        connections: Optional[List] = None,
        secrets: Optional[List] = None,
        vows: Optional[Dict] = None,
        **kwargs,
    ):

        if kwargs:
            raise TypeError(
                f"Character({name!r}) received unexpected kwargs: {sorted(kwargs)}. "
                "Pass `abilities={...}` with STR/DEX/CON/INT/WIS/CHA scores."
            )

        if abilities is None:
            raise ValueError(
                f"Character({name!r}) requires `abilities` (dict of STR/DEX/CON/INT/WIS/CHA)."
            )

        self.abilities: Dict[str, int] = self._validate_abilities(abilities)
        self.id = str(uuid.uuid4())
        self.owner_id = owner_id or "unknown"
        self.player_id = player_id
        self.name = name
        self.race = race
        self.background = background
        self.currency = currency

        # Class
        if isinstance(classs, str):
            self.classs = dnd_data.OGClass.get(classs)
            if not self.classs:
                self.classs = dnd_data.OGClass(
                    classs.lower(), {"name": classs, "hp_per_level": 2}
                )
        else:
            self.classs = classs

        self.level = max(1, int(level))

        # Proficiencies
        self.proficiency_bonus = proficiency_bonus_for_level(self.level)
        self.save_proficiencies = list(save_proficiencies or [])
        self.skill_proficiencies = list(skill_proficiencies or [])
        self.skill_expertise = list(skill_expertise or [])
        self.initiative_proficient = (
            bool(initiative_proficient)
            if initiative_proficient is not None
            else bool(getattr(self.classs, "initiative_proficient", False))
        )

        # Derived stats
        self.max_hp = self._calculate_max_hp()
        self.hp = self.max_hp
        self.max_sp = self._calculate_max_sp()
        self.sp = self.max_sp
        self.base_defense = self._calculate_defense()
        self.defense = self.base_defense
        self.damage_reduction = 0
        self.initiative_bonus = self._calculate_initiative_bonus()
        self.initiative = 0

        # Equipment
        self.inventory: List[InventoryItem] = []
        self.weapons: List[InventoryItem] = []
        self.shield: Optional[InventoryItem] = None
        self.equipped_gear: Dict[str, InventoryItem] = {}
        self.armor: Optional[InventoryItem] = None

        # Narrative
        self.age = age
        self.gender = gender
        self.description = description
        self.alignment = alignment
        self.ai_personality = {"traits": "", "ideals": "", "bonds": "", "flaws": ""}
        self.full_background_story = ""
        self.custom_items: List[InventoryItem] = []

        # Session
        self.party_id = None
        self.position = (0, 0)
        self.token = None
        self.avatar_url = "/static/images/default_avatar.png"
        self.locked_by = None
        self.active = False
        self.conditions: List[str] = []

        self.backstory = backstory or {}
        self.connections = connections or []
        self.secrets = secrets or []
        self.vows = vows or {}
        self.spells_known: List[str] = []

        if add_starting_gear and self.classs and getattr(self.classs, "starting_gear", None):
            self._add_starting_gear()

    # ---------- Validation & derivation ----------

    @staticmethod
    def _validate_abilities(abilities: Optional[Dict[str, int]]) -> Dict[str, int]:
        if not abilities:
            return {ab: 10 for ab in ABILITIES}
        cleaned = {}
        for ab in ABILITIES:
            score = abilities.get(ab, 10)
            try:
                score = int(score)
            except (TypeError, ValueError):
                raise ValueError(f"Ability {ab} must be an integer, got {score!r}")
            if not (SCORE_MIN <= score <= SCORE_MAX):
                raise ValueError(
                    f"Ability {ab}={score} out of range {SCORE_MIN}-{SCORE_MAX}"
                )
            cleaned[ab] = score
        return cleaned

    def modifier(self, ability: str) -> int:
        return ability_modifier(self.abilities[ability])

    def _calculate_max_hp(self) -> int:
        class_hp = getattr(self.classs, "hp_per_level", 2) if self.classs else 2
        return 6 + (class_hp * self.level) + (2 * self.modifier("CON"))

    def _calculate_max_sp(self) -> int:
        class_sp = getattr(self.classs, "sp_per_level", 0) if self.classs else 0
        return class_sp * self.level

    def _calculate_defense(self) -> int:
        return 10 + self.modifier("DEX")

    def _calculate_initiative_bonus(self) -> int:
        base = self.modifier("DEX")
        return base + (self.proficiency_bonus if self.initiative_proficient else 0)

    # ---------- Gear ----------

    @staticmethod
    def normalize_inventory_item(item) -> InventoryItem:
        if isinstance(item, InventoryItem):
            return item
        if isinstance(item, dict):
            allowed = {"name", "description", "quantity", "type", "equipped", "slot", "cost"}
            return InventoryItem(**{k: v for k, v in item.items() if k in allowed})
        raise TypeError(f"Invalid inventory item type: {type(item)}")

    def add_item(self, item) -> InventoryItem:
        item = self.normalize_inventory_item(item)
        self.inventory.append(item)
        return item

    def add_custom_item(self, name: str, description: str,
                        item_type: str = "adventuring_gear", cost: int = 0) -> InventoryItem:
        item = InventoryItem(name=name, description=description, type=item_type, cost=cost)
        self.custom_items.append(item)
        return item

    def _add_starting_gear(self):
        for gear_name in getattr(self.classs, "starting_gear", []) or []:
            item = self.add_item(InventoryItem(
                name=gear_name, description=f"Starting gear: {gear_name}",
            ))
            lname = gear_name.lower()
            if lname in ("mail", "leather", "robes") or "armor" in lname:
                item.slot = "armor"
                item.equipped = True
                self.equipped_gear["armor"] = item
                self.armor = item
                self._update_armor_stats(lname)
            elif lname in ("longsword", "shortsword", "staff", "mace",
                           "dagger", "bow", "rapier"):
                item.slot = "weapon"
                item.equipped = True
                self.weapons.append(item)
                self.equipped_gear["weapon"] = item
            elif lname in ("shield", "buckler"):
                item.slot = "shield"
                item.equipped = True
                self.shield = item
                self._update_shield_stats(lname)

    def _update_armor_stats(self, armor_name: str):
        table = {
            "mail": 2, "medium armor": 2,
            "leather": 1,
            "robes": 0,
            "heavy armor": 3,
        }
        if armor_name in table:
            self.damage_reduction = table[armor_name]

    def _update_shield_stats(self, shield_name: str):
        if "buckler" in shield_name:
            self.defense = self.base_defense + 1
        elif "shield" in shield_name:
            self.defense = self.base_defense + 2

    def equip_item(self, item_name: str, slot: str):
        self.inventory = [self.normalize_inventory_item(i) for i in self.inventory]
        self.custom_items = [self.normalize_inventory_item(i) for i in self.custom_items]
        item = next((i for i in self.inventory if i.name == item_name), None) \
            or next((i for i in self.custom_items if i.name == item_name), None)
        if not item:
            logger.warning("equip_item: %r not found", item_name)
            return
        item.equipped = True
        item.slot = slot
        self.equipped_gear[slot] = item
        if slot == "armor":
            self._update_armor_stats(item_name.lower())
        elif slot == "weapon":
            if item not in self.weapons:
                self.weapons.append(item)
        elif slot == "shield":
            self.shield = item
            self._update_shield_stats(item_name.lower())

    # ---------- Skills / spells ----------

    def add_skill(self, skill_name: str, rank: int = 1):
        if not dnd_data.validate_skill(skill_name):
            return
        if rank >= 2:
            if skill_name not in self.skill_proficiencies:
                self.skill_proficiencies.append(skill_name)
            if skill_name not in self.skill_expertise:
                self.skill_expertise.append(skill_name)
        elif skill_name not in self.skill_proficiencies:
            self.skill_proficiencies.append(skill_name)
        if dnd_data.validate_skill(skill_name):
            if skill_name not in self.skill_proficiencies:
                self.skill_proficiencies.append(skill_name)

    def get_skill_rank(self, skill_name: str) -> int:
        if skill_name in self.skill_expertise:
            return self.proficiency_bonus * 2
        if skill_name in self.skill_proficiencies:
            return self.proficiency_bonus
        return 0

    def learn_spell(self, spell_name: str):
        if spell_name not in self.spells_known:
            self.spells_known.append(spell_name)

    # ---------- Session ----------

    def lock(self, session_id: str) -> bool:
        if self.locked_by and self.locked_by != session_id:
            return False
        self.locked_by = session_id
        return True

    def unlock(self, session_id: str) -> bool:
        if self.locked_by == session_id:
            self.locked_by = None
            return True
        return False

    def roll_initiative(self) -> int:
        roll = random.randint(1, 20)
        self.initiative = roll + self.initiative_bonus
        return self.initiative

    def join_party(self, party_id: str): self.party_id = party_id
    def leave_party(self): self.party_id = None

    def get_full_inventory(self) -> List[InventoryItem]:
        return list(self.inventory) + list(self.custom_items)

    # ---------- Persistence ----------

    def to_dict(self) -> Dict[str, Any]:
        def _item(item):
            if isinstance(item, InventoryItem):
                return {
                    "name": item.name, "description": item.description,
                    "quantity": item.quantity, "type": item.type,
                    "equipped": item.equipped, "slot": item.slot, "cost": item.cost,
                    "initiative": self.initiative,
                }
            return item
        return {
            "id": self.id,
            "name": self.name,
            "race": self.race,
            "class": self.classs.name if hasattr(self.classs, "name") else str(self.classs),
            "level": self.level,
            "background": self.background,
            "owner_id": self.owner_id,
            "player_id": self.player_id,
            "currency": self.currency,
            "abilities": dict(self.abilities),
            "save_proficiencies": list(self.save_proficiencies),
            "skill_proficiencies": list(self.skill_proficiencies),
            "skill_expertise": list(self.skill_expertise),
            "initiative_proficient": self.initiative_proficient,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "sp": self.sp,
            "max_sp": self.max_sp,
            "defense": self.defense,
            "damage_reduction": self.damage_reduction,
            "inventory": [_item(i) for i in self.inventory],
            "custom_items": [_item(i) for i in self.custom_items],
            "spells_known": list(self.spells_known),
            "age": self.age,
            "gender": self.gender,
            "description": self.description,
            "alignment": self.alignment,
            "avatar_url": self.avatar_url,
            "position": self.position,
            "party_id": self.party_id,
            "conditions": list(self.conditions),
            "backstory": self.backstory,
            "connections": self.connections,
            "secrets": self.secrets,
            "vows": self.vows,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], owner_id: Optional[str] = None) -> "Character":
        if "abilities" not in data:
            raise ValueError(
                f"from_dict: 'abilities' key required. Got keys: {sorted(data)}"
            )
        abilities = data["abilities"]

        char = cls(
            name=data.get("name", "Unknown"),
            race=data.get("race", "Human"),
            classs=data.get("class", "Warrior"),
            level=data.get("level", 1),
            background=data.get("background", "unknown"),
            player_id=data.get("player_id"),
            owner_id=owner_id or data.get("owner_id", "unknown"),
            currency=data.get("currency", 100),
            abilities=abilities,
            save_proficiencies=data.get("save_proficiencies", []),
            skill_proficiencies=data.get("skill_proficiencies", []),
            skill_expertise=data.get("skill_expertise", []),
            initiative_proficient=data.get("initiative_proficient"),
            add_starting_gear=False,
            age=data.get("age"),
            gender=data.get("gender"),
            description=data.get("description"),
            alignment=data.get("alignment"),
            backstory=data.get("backstory"),
            connections=data.get("connections"),
            secrets=data.get("secrets"),
            vows=data.get("vows"),
        )
        if "id" in data:
            char.id = data["id"]
        char.hp = data.get("hp", char.max_hp)
        char.initiative = data.get("initiative", 0)
        char.sp = data.get("sp", char.max_sp)
        char.spells_known = list(data.get("spells_known", []))
        char.ai_personality = data.get(
            "ai_personality",
            {"traits": "", "ideals": "", "bonds": "", "flaws": ""},
        )
        char.full_background_story = data.get("full_background_story", "")

        if "abilities" not in data:
            raise ValueError(
                f"from_dict: 'abilities' key required. Got keys: {sorted(data)}"
            )
        abilities = data["abilities"]

        char.inventory = []
        for item_data in data.get("inventory", []):
            try:
                char.inventory.append(char.normalize_inventory_item(item_data))
            except (TypeError, ValueError) as exc:
                logger.warning("from_dict: skipping invalid inventory item %r: %s",
                               item_data, exc)
        char.custom_items = []
        for item_data in data.get("custom_items", []):
            try:
                char.custom_items.append(char.normalize_inventory_item(item_data))
            except (TypeError, ValueError) as exc:
                logger.warning("from_dict: skipping invalid custom item %r: %s",
                               item_data, exc)

        for item in char.inventory:
            if item.equipped and item.slot:
                char.equipped_gear[item.slot] = item
                if item.slot == "weapon":
                    char.weapons.append(item)
                elif item.slot == "shield":
                    char.shield = item
                elif item.slot == "armor":
                    char.armor = item
                    char._update_armor_stats(item.name.lower())

        char.party_id = data.get("party_id")
        char.position = data.get("position", (0, 0))
        char.avatar_url = data.get("avatar_url", "/static/images/default_avatar.png")
        char.token = data.get("token")
        char.active = data.get("active", False)
        char.locked_by = data.get("locked_by")
        char.conditions = list(data.get("conditions", []))
        return char

    def __repr__(self) -> str:
        cname = self.classs.name if self.classs else "Unknown"
        return f"<Character {self.name} ({self.race} {cname} L{self.level})>"