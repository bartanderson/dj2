# world\world_session.py
import uuid
from datetime import datetime
from typing import Dict, List, Optional

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}  # session_id -> player_data
        self.character_assignments: Dict[str, str] = {}  # character_id -> session_id
        self.party_views: Dict[str, List[str]] = {}  # party_id -> [session_ids]
        self.device_sessions: Dict[str, List[str]] = {}  # device_id -> [session_ids]
    
    def create_session(self, session_id, player_name, device_info=None):
        player = self.world_controller.get_or_create_player(player_name, device_info)

        if player is None:
            return None

        session = self.world_controller.session_manager.get_or_create_session(
            session_id,
            player.id
        )

        session.player_name = player_name
        session.device_info = device_info
        session.connected_at = datetime.now()
        session.last_active = datetime.now()

        return session
    
    def assign_character(self, session_id: str, character_id: str) -> bool:
        if session_id not in self.sessions:
            return False
 
        if session_id not in self.sessions:
            return False

        # Release any previous assignment
        old_char_id = self.sessions[session_id].character_id
        if old_char_id and old_char_id in self.character_assignments:
            del self.character_assignments[old_char_id]
        
        # Make new assignment
        self.sessions[session_id].character_id = character_id
        self.character_assignments[character_id] = session_id
        self.sessions[session_id].last_active = datetime.now()
        
        return True
    
    def assign_to_party(self, session_id: str, party_id: str) -> bool:
        if session_id not in self.sessions:
            return False
        
        # Leave previous party
        old_party_id = self.sessions[session_id].party_id
        if old_party_id and old_party_id in self.party_views:
            if session_id in self.party_views[old_party_id]:
                self.party_views[old_party_id].remove(session_id)
        
        # Join new party
        self.sessions[session_id].party_id = party_id
        if party_id not in self.party_views:
            self.party_views[party_id] = []
        
        if session_id not in self.party_views[party_id]:
            self.party_views[party_id].append(session_id)
        
        self.sessions[session_id].last_active = datetime.now()
        return True
    
    def get_party_members(self, party_id: str) -> List[dict]:
        """Get all session data for party members"""
        if party_id not in self.party_views:
            return []
        
        return [self.sessions[sid] for sid in self.party_views[party_id] if sid in self.sessions]
    
    def get_session_by_character(self, character_id: str) -> Optional[dict]:
        """Get session data for character owner"""
        session_id = self.character_assignments.get(character_id)
        if session_id and session_id in self.sessions:
            return self.sessions[session_id]
        return None
    
    def cleanup_inactive_sessions(self, timeout_minutes: int = 30):
        """Remove sessions that haven't been active for a while"""
        now = datetime.now()
        to_remove = []
        
        for session_id, session_data in self.sessions.items():
            inactive_time = now - session_data['last_active']
            if inactive_time.total_seconds() > timeout_minutes * 60:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            character_id = self.sessions[session_id].character_id
            if character_id and character_id in self.character_assignments:
                del self.character_assignments[character_id]
            
            party_id = self.sessions[session_id].party_id
            if party_id and party_id in self.party_views:
                if session_id in self.party_views[party_id]:
                    self.party_views[party_id].remove(session_id)
            
            device_id = self.sessions[session_id].device_id
            if device_id and device_id in self.device_sessions:
                if session_id in self.device_sessions[device_id]:
                    self.device_sessions[device_id].remove(session_id)
            
            del self.sessions[session_id]
