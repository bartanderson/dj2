"""
Session management system - tracks player conversation state
Phase: State Mutation (for state updates), but provides context to other phases
"""
from collections import deque
from typing import Dict, List, Optional, Any, Deque
from datetime import datetime

class SessionState:
    """State for a single player session"""

    def __init__(self, session_id: str, player_id: Optional[str] = None):
        self.session_id = session_id
        self.player_id = player_id

        self.chat_topics: Deque[str] = deque(maxlen=5)  # Recent topics
        self.chat_history = []
        
        self.character_data: Dict[str, Any] = {}      # Character creation progress

        self.awaiting_confirmation = False
        self.creation_state = "not_started"           # not_started, gathering_info, class_suggested, class_confirmed, completed
        self.pending_suggestion: Optional[Dict] = None   # Suggested class details (temporary)
        
        self.last_interaction_time = 0
        
        self.character_id = None
        self.party_id = None
        self.active_character_id: Optional[str] = None
        self.device_id: Optional[str] = None
        
        self.connected_at: Optional[datetime] = None
        self.last_active = datetime.now()

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def setdefault(self, key, default=None):
        if not hasattr(self, key):
            setattr(self, key, default)
        return getattr(self, key)


class SessionSystem:
    """Manages player session state across the game"""

    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    def get_or_create_session(self, session_id: str, player_id: str = None) -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(session_id, player_id)

        session = self.sessions[session_id]

        if player_id and session.player_id is None:
            session.player_id = player_id

        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def add_message(self, session_id: str, speaker: str, content: str):
        """Add a message to chat history"""
        session = self.get_session(session_id)
        if session:
            session.chat_history.append(DialogResponse(
                speaker= speaker,
                content= content,
                dialog_type="log"
            ))

    def add_topic(self, session_id: str, topic: str):
        """Add topic to conversation topics"""
        session = self.get_session(session_id)
        if session and topic and topic not in session.chat_topics:
            session.chat_topics.append(topic)

    def get_recent_topics(self, session_id: str, limit: int = 3) -> List[str]:
        """Get most recent conversation topics"""
        session = self.get_session(session_id)
        if session:
            return list(session.chat_topics)[-limit:]
        return []

    def update_character_data(self, session_id: str, updates: Dict[str, Any]):
        """Update character creation data"""
        session = self.get_session(session_id)
        if session:
            session.character_data.update(updates)

    def set_creation_state(self, session_id: str, state: str):
        """Update character creation state (validates allowed states)"""
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

    def set_pending_suggestion(self, session_id: str, suggestion: Optional[Dict]):
        """Store or clear a pending class suggestion"""
        session = self.get_session(session_id)
        if session:
            session.pending_suggestion = suggestion

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

    def set_active_character(self, session_id: str, character_id: Optional[str]):
        """Store the active character ID for the session."""
        session = self.get_session(session_id)
        if session:
            session.active_character_id = character_id

    def get_active_character(self, session_id: str) -> Optional[str]:
        """Retrieve the active character ID for the session."""
        session = self.get_session(session_id)
        return session.active_character_id if session else None

    def set_character_data(self, session_id: str, data: Dict[str, Any]):
        """Replace the entire character_data dictionary (used for reset)."""
        session = self.get_session(session_id)
        if session:
            session.character_data = data.copy()

    def remove_character_data_field(self, session_id: str, field: str):
        """Delete a specific field from character_data."""
        session = self.get_session(session_id)
        if session and field in session.character_data:
            del session.character_data[field]