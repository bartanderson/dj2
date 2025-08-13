import uuid
class Character:
    def __init__(self, name, owner_id, type="player"):
        self.id = f"char_{uuid.uuid4().hex[:6]}"
        self.name = name
        self.owner_id = owner_id  # user_id who owns this character
        self.type = type
        self.position = (0, 0)
        self.initiative = 0
        self.token = None
        self.stats = self._default_stats()
        self.equipment = []
        self.spells = []
        self.locked_by = None
        self.action_points = 0
        self.active = False
        
    def _default_stats(self):
        return {
            "str": 10, "dex": 10, "con": 10,
            "int": 10, "wis": 10, "cha": 10,
            "hp": 10, "max_hp": 10, "ac": 10,
            "speed": 30
        }

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
        self.initiative = random.randint(1, 20)
        return self.initiative
    
    def join_party(self, party_id: str):
        """Join a party"""
        self.party_id = party_id
    
    def leave_party(self):
        """Leave current party"""
        self.party_id = None