# world\character.py
from dnd_character import Character as DnDCharacter
from dnd_character.equipment import Item
from dnd_character.spellcasting import SPELLS
import uuid
import random

class Character(DnDCharacter):
    def __init__(self, owner_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = f"char_{uuid.uuid4().hex[:6]}"
        self.owner_id = owner_id
        self.party_id = None
        self.ai_personality = {
            "traits": "",
            "ideals": "",
            "bonds": "",
            "flaws": ""
        }
        self.custom_items = []
        self.background_story = ""
        
        # New position/token/initiative properties
        self.position = (0, 0)  # (x, y) coordinates
        self.initiative = 0
        self.token = None  # URL to token image
        self.avatar_url = "/static/images/default_avatar.png"  # Default avatar
        self.locked_by = None  # Session ID that has control
        self.active = False  # Whether character is active in party
        
    def lock(self, session_id):
        """Attempt to lock the character for a session"""
        if self.locked_by and self.locked_by != session_id:
            return False  # Already locked by another session
        self.locked_by = session_id
        return True
        
    def unlock(self, session_id):
        """Release the lock if held by this session"""
        if self.locked_by == session_id:
            self.locked_by = None
            return True
        return False

    def roll_initiative(self):
        """Roll initiative for combat"""
        self.initiative = random.randint(1, 20) + self.dexterity_mod
        return self.initiative
    
    def join_party(self, party_id: str):
        """Join a party"""
        self.party_id = party_id
    
    def leave_party(self):
        """Leave current party"""
        self.party_id = None
        
    def add_custom_item(self, name, description, item_type="adventuring_gear"):
        """Add a personalized item from AI suggestions"""
        custom_item = Item(name)
        custom_item.description = description
        custom_item.type = item_type
        self.custom_items.append(custom_item)
        
    def get_full_inventory(self):
        """Combine standard and custom items"""
        return self.inventory + self.custom_items
    
    def equip_item(self, item_name, slot):
        """Equip an item from inventory"""
        item = next((i for i in self.get_full_inventory() if i.name == item_name), None)
        if item:
            # Handle equipment logic based on slot
            if slot == "armor":
                self.armor = item
            elif slot == "weapon":
                if not self.weapons:
                    self.weapons = []
                self.weapons.append(item)
            # Add other slot handling as needed
    
    def to_dict(self):
        """Properly serialized character with base class properties"""
        # Get base class properties
        base_dict = super().to_dict()
        
        # Add our custom properties
        extended_dict = {
            "id": self.id,
            "owner_id": self.owner_id,
            "party_id": self.party_id,
            "ai_personality": self.ai_personality,
            "background_story": self.background_story,
            "custom_items": [{"name": item.name, "description": item.description} 
                             for item in self.custom_items],
            "avatar_url": self.avatar_url,
            "position": self.position,
            "initiative": self.initiative,
            "token": self.token,
            "locked_by": self.locked_by,
            "active": self.active
        }
        
        # Merge dictionaries (custom properties override base ones if conflict)
        return {**base_dict, **extended_dict}
    
    @classmethod
    def from_dict(cls, data, owner_id):
        """Properly deserialize character with base class properties"""
        # First create base character from base properties
        char = super().from_dict(data)
        
        # Now set our custom properties
        char.id = data.get("id", f"char_{uuid.uuid4().hex[:6]}")
        char.owner_id = owner_id
        char.party_id = data.get("party_id")
        char.ai_personality = data.get("ai_personality", {
            "traits": "", "ideals": "", "bonds": "", "flaws": ""
        })
        char.background_story = data.get("background_story", "")
        char.avatar_url = data.get("avatar_url", "/static/images/default_avatar.png")
        char.position = data.get("position", (0, 0))
        char.initiative = data.get("initiative", 0)
        char.token = data.get("token")
        char.locked_by = data.get("locked_by")
        char.active = data.get("active", False)
        
        # Add custom items
        for item_data in data.get("custom_items", []):
            char.add_custom_item(item_data["name"], item_data["description"])
            
        return char