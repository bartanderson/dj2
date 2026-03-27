
# character.py - standalone Character class using OG System data
"""
OG System Character class - replaces dnd_character dependency.
Standalone implementation using OG System attributes and mechanics.
"""

import uuid
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

# Import OG System data layer
from world import dnd_data

@dataclass
class InventoryItem:
    """Simple inventory item"""
    name: str
    description: str = ""
    quantity: int = 1
    type: str = "adventuring_gear"
    equipped: bool = False
    slot: Optional[str] = None  # "armor", "weapon", "shield", etc.

class Character:
    """
    OG System Character - standalone, no inheritance.
    Uses 4 attributes: Brawn, Finesse, Wits, Will
    """
    def __init__(self, 
                 name: str,
                 race: str,
                 classs: Any,  # Can be string or OGClass object
                 level: int = 1,
                 background: str = "unknown",
                 player_id: Optional[str] = None,
                 owner_id: Optional[str] = None,
                 # Attributes (0-4 scale in OG System)
                 brawn: Optional[int] = None,
                 finesse: Optional[int] = None,
                 wits: Optional[int] = None,
                 will: Optional[int] = None,
                 # Optional fields
                 age: Optional[int] = None,
                 gender: Optional[str] = None,
                 description: Optional[str] = None,
                 alignment: Optional[str] = None,
                 # Narrative fields (optional)
                 backstory: Optional[Dict] = None,
                 connections: Optional[List] = None,
                 secrets: Optional[List] = None,
                 vows: Optional[Dict] = None,
                 **kwargs):
        
        # Core identity
        self.id = str(uuid.uuid4())
        self.owner_id = owner_id or "unknown"
        self.name = name
        self.race = race
        self.background = background
        self.player_id = player_id
        
        # Handle class (can be string name or OGClass object)
        if isinstance(classs, str):
            self.classs = dnd_data.OGClass.get(classs)
            if not self.classs:
                # Create minimal class object
                self.classs = dnd_data.OGClass(classs.lower(), {"name": classs, "hp_per_level": 2})
        else:
            self.classs = classs
        
        self.level = level
        
        # OG System: 4 attributes, default to 1 if not specified
        self.brawn = brawn if brawn is not None else 1
        self.finesse = finesse if finesse is not None else 1
        self.wits = wits if wits is not None else 1
        self.will = will if will is not None else 1
        
        # Apply racial bonuses
        self._apply_racial_bonuses()
        
        # HP calculation: 6 + (Brawn × 2) + (level × class_hp_per_level)
        self.max_hp = self._calculate_max_hp()
        self.hp = self.max_hp
        
        # SP (Spell Points): Will × 2 + (level × class_sp_per_level)
        self.max_sp = self._calculate_max_sp()
        self.sp = self.max_sp
        
        # Defense: 10 + Finesse + shield_bonus (calculated later)
        self.base_defense = 10 + self.finesse
        self.defense = self.base_defense
        
        # Initiative: d20 + Wits (rolled later)
        self.initiative = 0
        
        # Armor and damage reduction
        self.armor = None
        self.armor_bonus = 0
        self.damage_reduction = 0  # From armor type
        
        # Inventory and equipment
        self.inventory: List[InventoryItem] = []
        self.weapons: List[InventoryItem] = []
        self.shield = None
        self.equipped_gear = {}  # slot -> item
        
        # Skills: dict of skill_name -> rank (0-3)
        self.skills: Dict[str, int] = {}
        
        # Spells known (for Mage, Priest, Warlock, Bard)
        self.spells_known: List[str] = []
        
        # Personal details
        self.age = age
        self.gender = gender
        self.description = description
        self.alignment = alignment
        
        # AI-generated content (your superior features)
        self.ai_personality = {
            "traits": "",
            "ideals": "",
            "bonds": "",
            "flaws": ""
        }
        self.full_background_story = ""
        self.custom_items: List[InventoryItem] = []
        
        # Session/party management
        self.party_id = None
        self.position = (0, 0)  # (x, y) coordinates
        self.token = None  # URL to token image
        self.avatar_url = "/static/images/default_avatar.png"
        self.locked_by = None  # Session ID that has control
        self.active = False
        
        # Conditions (from OG System combat)
        self.conditions: List[str] = []
        
        # Narrative fields (Phase 2)
        self.backstory = backstory or {}
        self.connections = connections or []
        self.secrets = secrets or []
        self.vows = vows or {}
        
        # Add starting gear if class defined
        if self.classs and hasattr(self.classs, 'starting_gear'):
            self._add_starting_gear()    

    
    def _apply_racial_bonuses(self):
        """Apply racial attribute bonuses from OG System"""
        race_obj = dnd_data.Race.get(self.race)
        if not race_obj:
            return
        
        bonus = race_obj.mechanical_bonus
        if not bonus:
            return
        
        bonus_type = bonus.get("type")
        bonus_value = bonus.get("value", "")
        
        if bonus_type == "attribute":
            # +1 to any attribute (Human)
            if "+1 any" in bonus_value:
                # Default to Brawn if not specified, or could be player choice
                self.brawn = min(4, self.brawn + 1)
        elif bonus_type == "choice":
            # Parse choice bonuses like "+1 Brawn or +1 Armor"
            if "Brawn" in bonus_value and "or" in bonus_value:
                self.brawn = min(4, self.brawn + 1)
            elif "Finesse" in bonus_value:
                self.finesse = min(4, self.finesse + 1)
            elif "Will" in bonus_value:
                self.will = min(4, self.will + 1)
        elif bonus_type == "static":
            # Special abilities like regeneration
            pass  # Handled via knacks/tags
    
    def _calculate_max_hp(self) -> int:
        """Calculate max HP: 6 + (Brawn × 2) + (level × class_hp_per_level)"""
        base = 6
        brawn_bonus = self.brawn * 2
        class_bonus = (self.classs.hp_per_level if self.classs else 2) * self.level
        return base + brawn_bonus + class_bonus
    
    def _calculate_max_sp(self) -> int:
        """Calculate max SP: Will × 2 + (level × class_sp_per_level)"""
        will_bonus = self.will * 2
        class_bonus = (self.classs.sp_per_level if self.classs else 0) * self.level
        return will_bonus + class_bonus
    
    def _add_starting_gear(self):
        """Add starting equipment from class definition"""
        if not self.classs or not hasattr(self.classs, 'starting_gear'):
            return
        
        for gear_name in self.classs.starting_gear:
            item = InventoryItem(name=gear_name, description=f"Starting gear: {gear_name}")
            self.inventory.append(item)
            
            # Auto-equip armor and weapons
            if "armor" in gear_name.lower() or gear_name.lower() in ["mail", "leather", "robes"]:
                item.slot = "armor"
                item.equipped = True
                self.equipped_gear["armor"] = item
                self._update_armor_stats(gear_name)
            elif gear_name.lower() in ["longsword", "shortsword", "staff", "mace", "dagger", "bow", "rapier"]:
                item.slot = "weapon"
                item.equipped = True
                self.weapons.append(item)
                self.equipped_gear["weapon"] = item
            elif gear_name.lower() in ["shield", "buckler"]:
                item.slot = "shield"
                item.equipped = True
                self.shield = item
                self._update_shield_stats(gear_name)
    
    def _update_armor_stats(self, armor_name: str):
        """Update defense and damage reduction based on armor"""
        armor_types = {
            "mail": {"dr": 2, "move": "-5ft"},
            "leather": {"dr": 1, "move": "full"},
            "robes": {"dr": 0, "move": "full"},
            "medium armor": {"dr": 2, "move": "-5ft"},
            "heavy armor": {"dr": 3, "move": "-10ft"},
        }
        
        armor_key = armor_name.lower()
        if armor_key in armor_types:
            stats = armor_types[armor_key]
            self.damage_reduction = stats["dr"]
            # Defense is 10 + Finesse, armor doesn't add in OG System
            # But heavy armor might limit max Finesse bonus
    
    def _update_shield_stats(self, shield_name: str):
        """Update defense based on shield"""
        if "buckler" in shield_name.lower():
            self.defense = self.base_defense + 1
        elif "shield" in shield_name.lower():
            self.defense = self.base_defense + 2
        
    # ------------------------------------------------------------------
    # Methods for compatibility with dnd_character interface
    # ------------------------------------------------------------------
    
    def lock(self, session_id: str) -> bool:
        """Attempt to lock the character for a session"""
        if self.locked_by and self.locked_by != session_id:
            return False
        self.locked_by = session_id
        return True
    
    def unlock(self, session_id: str) -> bool:
        """Release the lock if held by this session"""
        if self.locked_by == session_id:
            self.locked_by = None
            return True
        return False
    
    def roll_initiative(self) -> int:
        """Roll initiative: d20 + Wits"""
        roll = random.randint(1, 20)
        self.initiative = roll + self.wits
        return self.initiative
    
    def join_party(self, party_id: str):
        """Join a party"""
        self.party_id = party_id
    
    def leave_party(self):
        """Leave current party"""
        self.party_id = None
    
    def add_custom_item(self, name: str, description: str, item_type: str = "adventuring_gear"):
        """Add a personalized item from AI suggestions"""
        item = InventoryItem(name=name, description=description, type=item_type)
        self.custom_items.append(item)
    
    def get_full_inventory(self) -> List[InventoryItem]:
        """Combine standard and custom items"""
        return self.inventory + self.custom_items
    
    def equip_item(self, item_name: str, slot: str):
        """Equip an item from inventory"""
        # Find item in inventory
        item = next((i for i in self.inventory if i.name == item_name), None)
        if not item:
            # Check custom items
            item = next((i for i in self.custom_items if i.name == item_name), None)
        
        if item:
            item.equipped = True
            item.slot = slot
            self.equipped_gear[slot] = item
            
            if slot == "armor":
                self._update_armor_stats(item_name)
            elif slot == "weapon":
                if item not in self.weapons:
                    self.weapons.append(item)
            elif slot == "shield":
                self.shield = item
                self._update_shield_stats(item_name)
    
    def add_skill(self, skill_name: str, rank: int = 1):
        """Add or improve a skill (max rank 3)"""
        if dnd_data.validate_skill(skill_name):
            current = self.skills.get(skill_name, 0)
            self.skills[skill_name] = min(3, current + rank)
    
    def get_skill_rank(self, skill_name: str) -> int:
        """Get current rank in a skill (0 if not trained)"""
        return self.skills.get(skill_name, 0)
    
    def learn_spell(self, spell_name: str):
        """Add a spell to spells known"""
        if spell_name not in self.spells_known:
            self.spells_known.append(spell_name)
    
    def to_dict(self):
        def _item_to_dict(item):
            if hasattr(item, 'to_dict'):
                return item.to_dict()
            elif isinstance(item, dict):
                return item
            else:
                return vars(item) if hasattr(item, '__dict__') else {'name': str(item)}

        return {
            "id": self.id,
            "name": self.name,
            "race": self.race,
            "class": self.classs.name if hasattr(self.classs, 'name') else str(self.classs),
            "level": self.level,
            "background": self.background,
            "player_id": getattr(self, 'player_id', None),
            "owner_id": getattr(self, 'owner_id', None),
            "attributes": {
                "brawn": self.brawn,
                "finesse": self.finesse,
                "wits": self.wits,
                "will": self.will,
            },
            "hp": self.hp,
            "max_hp": self.max_hp,
            "sp": self.sp,
            "max_sp": self.max_sp,
            "defense": self.defense,
            "armor": self.armor,
            "damage_reduction": self.damage_reduction,
            "skills": self.skills,
            "inventory": [_item_to_dict(i) for i in self.inventory],
            "spells_known": self.spells_known,
            "age": self.age,
            "gender": self.gender,
            "description": self.description,
            "alignment": self.alignment,
            "avatar_url": self.avatar_url,
            "position": self.position,
            "party_id": self.party_id,
            "conditions": self.conditions,
            "backstory": self.backstory,
            "connections": self.connections,
            "secrets": self.secrets,
            "vows": self.vows,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], owner_id: Optional[str] = None) -> 'Character':
        """Deserialize character from dictionary"""
        # Create base character
        char = cls(
            name=data.get("name", "Unknown"),
            race=data.get("race", "Human"),
            classs=data.get("class", "Warrior"),
            level=data.get("level", 1),
            background=data.get("background", "unknown"),
            owner_id=owner_id or data.get("owner_id", "unknown"),
            brawn=data.get("brawn", 1),
            finesse=data.get("finesse", 1),
            wits=data.get("wits", 1),
            will=data.get("will", 1),
            age=data.get("age"),
            gender=data.get("gender"),
            description=data.get("description"),
            alignment=data.get("alignment"),
        )
        
        # Restore ID if present
        if "id" in data:
            char.id = data["id"]
        
        # Restore HP/SP (may have taken damage)
        char.hp = data.get("hp", char.max_hp)
        char.sp = data.get("sp", char.max_sp)
        
        # Restore skills
        char.skills = data.get("skills", {})
        
        # Restore spells
        char.spells_known = data.get("spells_known", [])
        
        # Restore AI content
        char.ai_personality = data.get("ai_personality", {
            "traits": "", "ideals": "", "bonds": "", "flaws": ""
        })
        char.full_background_story = data.get("full_background_story", "")
        
        # Restore custom items
        for item_data in data.get("custom_items", []):
            char.add_custom_item(
                item_data.get("name", "Unknown"),
                item_data.get("description", "")
            )
        
        # Restore party/session data
        char.party_id = data.get("party_id")
        char.position = data.get("position", (0, 0))
        char.avatar_url = data.get("avatar_url", "/static/images/default_avatar.png")
        char.token = data.get("token")
        char.active = data.get("active", False)
        char.locked_by = data.get("locked_by")
        char.conditions = data.get("conditions", [])
        
        return char
    
    def __repr__(self) -> str:
        return f"<Character {self.name} ({self.race} {self.classs.name if self.classs else 'Unknown'} L{self.level})>"
