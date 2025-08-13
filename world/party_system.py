from dungeon_neo.movement_service import MovementService, CharacterMovementService
from typing import List, Dict, Optional
class PartySystem:
    def __init__(self, state):
        self.state = state
        self.character_movement = CharacterMovementService(state)
        self.parties = {}  # party_id: {leader_id, members}
        self.character_parties = {}  # char_id: party_id

    def get_party_members(self, party_id: str) -> List[str]:
        """Get all character IDs in a party"""
        party = self.get_party(party_id)
        return party["members"] if party else []
    
    def move_with_party(self, character_id: str, direction: str, steps: int = 1):
        """Move a character with their party"""
        party_id = self.character_parties.get(character_id)
        if not party_id:
            return self.move_individual(character_id, direction, steps)
        
        return self.move_party(party_id, direction, steps)

    def get_user_characters_in_party(self, user_id, party_id):
        """Get all characters a user has in a specific party"""
        if party_id not in self.parties:
            return []
            
        return [char_id for char_id in self.parties[party_id]['members'] 
                if self.state.get_character(char_id).owner_id == user_id]
    
    def can_manage_party(self, user_id, party_id):
        """Check if user has management rights (owns leader character)"""
        if party_id not in self.parties:
            return False
            
        leader_id = self.parties[party_id]['leader']
        leader = self.state.get_character(leader_id)
        return leader and leader.owner_id == user_id

    def create_party(self, leader_char_id):
        """Create new party with character as leader"""
        party_id = f"party_{leader_char_id[:6]}"
        self.parties[party_id] = {
            "leader": leader_char_id,
            "members": [leader_char_id]
        }
        self.character_parties[leader_char_id] = party_id
        return party_id
        
    def join_party(self, char_id, party_id):
        """Add character to a party"""
        if party_id not in self.parties:
            return False
            
        if char_id in self.character_parties:
            return False  # Already in a party
            
        self.parties[party_id]["members"].append(char_id)
        self.character_parties[char_id] = party_id
        return True
        
    def leave_party(self, char_id):
        """Remove character from their party"""
        party_id = self.character_parties.get(char_id)
        if not party_id or party_id not in self.parties:
            return False
            
        party = self.parties[party_id]
        party["members"].remove(char_id)
        del self.character_parties[char_id]
        
        # Handle leadership transfer
        if party["leader"] == char_id and party["members"]:
            new_leader = party["members"][0]
            party["leader"] = new_leader
            return {"new_leader": new_leader}
        
        # Disband party if empty
        if not party["members"]:
            del self.parties[party_id]
            
        return True
        
    def transfer_leadership(self, party_id, new_leader_id):
        """Transfer party leadership to another member"""
        if party_id not in self.parties:
            return False
            
        party = self.parties[party_id]
        if new_leader_id not in party["members"]:
            return False
            
        party["leader"] = new_leader_id
        return True
    
    def move_party(self, party_id, direction, steps=1):
        """Move entire party using core movement logic"""
        party = self.state.get_party(party_id)
        if not party:
            return []
            
        results = []
        leader = self.state.get_character(party['leader'])
        
        # Move leader using unified movement service
        leader_result = self.state.movement.move_character(leader, direction, steps)
        results.append(leader_result)
        
        # Move followers to leader's previous position
        if leader_result['success']:
            old_position = leader_result.get('old_position')
            
            for char_id in party['members']:
                if char_id == party['leader']:
                    continue  # Leader already moved
                
                char = self.state.get_character(char_id)
                if char:
                    # Move directly to leader's previous position
                    char.position = old_position
                    results.append({
                        "success": True,
                        "message": f"{char.name} followed to {char.position}",
                        "character_id": char_id
                    })
        
        return results