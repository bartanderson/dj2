class Player:
    def __init__(self, id=None, name="Unknown Player", attributes=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.attributes = attributes or {}
        self.session_id = None
        self.character_ids = []
        self.active_character_id = None
        
        # REMOVE THESE - They belong in SessionState:
        # self.character_data = {}
        # self.awaiting_confirmation = False
        # self.creation_state = "not_started"  # States: not_started, gathering_info, class_suggested, class_confirmed, completed
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "attributes": self.attributes,
            "session_id": self.session_id,
            "character_ids": self.character_ids,
            "active_character_id": self.active_character_id
            # REMOVED: character_data, awaiting_confirmation, creation_state
        }
    
    def set_active_character(self, character_id):
        """Set a character as active for this player"""
        if character_id in self.character_ids:
            self.active_character_id = character_id
            self.attributes['active_character'] = character_id
            return True
        return False