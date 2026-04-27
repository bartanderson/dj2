#world.player.py
import uuid
from typing import List, Optional, Dict, Any
class Player:
    def __init__(self, id=None, name="Unknown Player", attributes=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.attributes = attributes or {}
        # Ensure default values in attributes
        self.attributes.setdefault('character_ids', [])
        self.attributes.setdefault('active_character_id', None)
        # Convenience accessors (not persisted separately)
        self.character_ids = self.attributes['character_ids']
        self.active_character_id = self.attributes['active_character_id']
        self.session_id = None

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "attributes": self.attributes,
            "session_id": self.session_id,
            "character_ids": self.character_ids,
            "active_character_id": self.active_character_id,
        }
        
    def set_active_character(self, character_id):
        if character_id in self.character_ids:
            self.active_character_id = character_id
            self.attributes['active_character_id'] = character_id
            return True
        party = self.party_manager.get_character_party(character_id)
        if party:
            self.default_party_id = party['id']
        return False