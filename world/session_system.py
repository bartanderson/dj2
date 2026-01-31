# world/session_system.py
"""
Session management system - tracks player conversation state
Phase: State Mutation (for state updates), but provides context to other phases
"""
from collections import defaultdict, deque
import uuid
import json
from typing import Dict, List, Optional, Any, Deque

class SessionState:
    """State for a single player session"""
    
    def __init__(self, session_id: str, player_id: Optional[str] = None):
        self.session_id = session_id
        self.player_id = player_id
        self.conversation_topics: Deque[str] = deque(maxlen=5)  # Recent topics
        self.chat_history: List[Dict[str, str]] = []  # Format: {"speaker": "DM/Player", "content": str}
        self.character_data: Dict[str, Any] = {}  # Character creation progress
        self.awaiting_confirmation = False
        self.creation_state = "not_started"  # not_started, gathering_info, class_suggested, class_confirmed, completed
        self.last_interaction_time = 0
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "conversation_topics": list(self.conversation_topics),
            "chat_history": self.chat_history[-10:],  # Last 10 messages
            "character_data": self.character_data,
            "awaiting_confirmation": self.awaiting_confirmation,
            "creation_state": self.creation_state
        }

class SessionSystem:
    """Manages player session state across the game"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        
    def get_or_create_session(self, session_id: str, player_id: Optional[str] = None) -> SessionState:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(session_id, player_id)
        elif player_id and not self.sessions[session_id].player_id:
            self.sessions[session_id].player_id = player_id
            
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def add_message(self, session_id: str, speaker: str, content: str):
        """Add a message to chat history"""
        session = self.get_session(session_id)
        if session:
            session.chat_history.append({
                "speaker": speaker,
                "content": content,
                "timestamp": self._get_timestamp()
            })
    
    def add_topic(self, session_id: str, topic: str):
        """Add topic to conversation topics"""
        session = self.get_session(session_id)
        if session and topic and topic not in session.conversation_topics:
            session.conversation_topics.append(topic)
    
    def get_recent_topics(self, session_id: str, limit: int = 3) -> List[str]:
        """Get most recent conversation topics"""
        session = self.get_session(session_id)
        if session:
            return list(session.conversation_topics)[-limit:]
        return []
    
    def update_character_data(self, session_id: str, updates: Dict[str, Any]):
        """Update character creation data"""
        session = self.get_session(session_id)
        if session:
            session.character_data.update(updates)
    
    def set_creation_state(self, session_id: str, state: str):
        """Update character creation state"""
        valid_states = ["not_started", "gathering_info", "class_suggested", "class_confirmed", "completed"]
        session = self.get_session(session_id)
        if session and state in valid_states:
            session.creation_state = state
            return True
        return False
    
    def set_awaiting_confirmation(self, session_id: str, awaiting: bool):
        """Set confirmation waiting state"""
        session = self.get_session(session_id)
        if session:
            session.awaiting_confirmation = awaiting
    
    def get_conversation_context(self, session_id: str, message_count: int = 10) -> str:
        """Get recent conversation for AI context"""
        session = self.get_session(session_id)
        if not session:
            return ""
        
        recent_messages = session.chat_history[-message_count:]
        return "\n".join([f"{msg['speaker']}: {msg['content']}" for msg in recent_messages])
    
    def _get_timestamp(self) -> str:
        """Simple timestamp for chat history"""
        import time
        return time.strftime("%H:%M:%S")