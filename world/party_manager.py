# world/party_manager.py
"""
Party Management System - handles party creation, membership, and state
Phase: State Mutation (party state changes)
"""
from typing import Dict, List, Optional, Set, Any
import uuid

class PartyManager:
    """Manages party state and operations"""

    PARTY_COLORS = [
        "#FFD700",  # gold
        "#FF4444",  # red
        "#44FF44",  # green
        "#4444FF",  # blue
        "#FF44FF",  # magenta
        "#44FFFF",  # cyan
        "#FFA500",  # orange
        "#FF00FF",  # pink
        "#00FF00",  # lime
        "#FFFF00"   # yellow
    ]
    
    def __init__(self, starting_location_id: str):
        self.parties: Dict[str, Dict] = {}
        self.character_parties: Dict[str, str] = {}
        self.active_parties: Set[str] = set()
        self.default_party_id = "main_party"
        self.starting_location_id = starting_location_id
        self._next_color_index = 0
        
        # Initialize default party
        self.parties[self.default_party_id] = {
            "name": "Main Party",
            "members": [],
            "location": self.starting_location_id,
            "color": self.PARTY_COLORS[0]
        }
        self._next_color_index = 1

    def _get_next_color(self):
        color = self.PARTY_COLORS[self._next_color_index % len(self.PARTY_COLORS)]
        self._next_color_index += 1
        return color

    def create_party(self, party_name: str, member_ids: List[str]) -> str:
        """Create a new party"""
        party_id = f"party_{uuid.uuid4().hex[:8]}"
        
        self.parties[party_id] = {
            "id": party_id,
            "name": party_name,
            "members": member_ids,
            "quests": [],
            "location": self.starting_location_id,
            "in_tavern": True,
            "color": self._get_next_color()
        }
        self.active_parties.add(party_id)
        
        # Link members to party
        for char_id in member_ids:
            self.character_parties[char_id] = party_id
        print(f"DEBUG: Party created, now parties = {self.parties}")    
        return party_id

    def add_to_party(self, char_id: str, party_id: str) -> bool:
        """Add character to a party"""
        if char_id not in self.character_parties:
            return False
        
        # Remove from current party if any
        current_party = self.character_parties.get(char_id)
        if current_party and current_party in self.parties:
            self.parties[current_party]["members"].remove(char_id)
        
        # Add to new party
        if party_id not in self.parties:
            return False
            
        self.parties[party_id]["members"].append(char_id)
        self.character_parties[char_id] = party_id
        return True

    def remove_from_party(self, char_id: str) -> bool:
        """Remove character from their current party"""
        party_id = self.character_parties.get(char_id)
        if party_id and party_id in self.parties:
            self.parties[party_id]["members"].remove(char_id)
            del self.character_parties[char_id]
        return True

    def disband_party(self, party_id: str) -> bool:
        """Disband a party and return members to solo status"""
        if party_id not in self.parties or party_id == self.default_party_id:
            return False
        
        # Remove all members from party
        for char_id in self.parties[party_id]["members"][:]:
            self.remove_from_party(char_id)
            
        del self.parties[party_id]
        return True

    def get_character_party(self, char_id: str) -> Optional[Dict]:
        """Get party data for a character"""
        party_id = self.character_parties.get(char_id)
        if party_id and party_id in self.parties:
            return self.parties[party_id]
        return None

    def get_active_parties(self) -> List[Dict]:
        """Get all active parties"""
        return [party for party in self.parties.values() if party["members"]]
    
    def complete_tavern_intro(self, party_id: str) -> bool:
        """Mark that a party has completed the initial tavern scene"""
        if party_id in self.parties:
            self.parties[party_id]["in_tavern"] = False
            return True
        return False

    def get_party_members(self, party_id: str) -> List[str]:
        """Get member IDs for a party"""
        return self.parties.get(party_id, {}).get("members", [])

    def set_party_location(self, party_id: str, location_id: str) -> bool:
        """Update party location"""
        if party_id in self.parties:
            self.parties[party_id]["location"] = location_id
            return True
        return False

    def get_party_quests(self, party_id: str) -> List[str]:
        """Get quest IDs for a party"""
        return self.parties.get(party_id, {}).get("quests", [])

    def add_party_quest(self, party_id: str, quest_id: str) -> bool:
        """Add a quest to a party"""
        if party_id in self.parties:
            if "quests" not in self.parties[party_id]:
                self.parties[party_id]["quests"] = []
            self.parties[party_id]["quests"].append(quest_id)
            return True
        return False