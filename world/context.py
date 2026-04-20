from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

@dataclass
class UnifiedContext:
    """
    Single source of truth for all game systems (narrative, audio, visual, subhex).
    """
    # Spatial
    domain: str = "world"               # "world", "dungeon", "settlement"
    location: str = ""                  # e.g., "tavern", "forest", "crypt"
    position: Tuple[int, int, int, int] = (0, 0, 0, 0)  # (col, row, sub_q, sub_r)
    
    # Environmental
    terrain: str = "plains"
    time_of_day: str = "day"            # "day", "night", "dusk", "dawn"
    indoors: bool = False
    
    # Activity
    activity: str = "idle"              # "idle", "travel", "combat", "social"
    
    # Narrative
    mood: str = "neutral"               # "calm", "tense", "eerie", "cozy"
    tension: float = 0.0                # 0.0 to 1.0
    event: Optional[str] = None         # e.g., "encounter", "discovery"
    
    # Population
    presence: str = "alone"             # "alone", "sparse", "crowded"
    
    # State modifiers
    danger: float = 0.0
    fatigue: float = 0.0
    
    # Knowledge layer (what the player knows vs truth)
    knowledge: Dict[str, Any] = field(default_factory=dict)
    
    # Structural changes (from overlay system)
    topology_changes: List[str] = field(default_factory=list)
    
    # Audio hints
    sound_profile: Optional[str] = None
    mood_modifier: Optional[str] = None
    
    # Timestamp for tracking changes
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON transmission."""
        return {
            "domain": self.domain,
            "location": self.location,
            "position": list(self.position),
            "terrain": self.terrain,
            "time_of_day": self.time_of_day,
            "indoors": self.indoors,
            "activity": self.activity,
            "mood": self.mood,
            "tension": self.tension,
            "event": self.event,
            "presence": self.presence,
            "danger": self.danger,
            "fatigue": self.fatigue,
            "knowledge": self.knowledge,
            "topology_changes": self.topology_changes,
            "sound_profile": self.sound_profile,
            "mood_modifier": self.mood_modifier,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_game_context(cls, game_context: Dict[str, Any]) -> 'UnifiedContext':
        """
        Convert the legacy game_context dict (from dm_chat_ai.py) to UnifiedContext.
        """
        # Extract known fields, with defaults
        return cls(
            domain=game_context.get("mode", "world"),
            location=game_context.get("current_location", {}).get("name", ""),
            position=(0, 0, 0, 0),  # TODO: get from party position
            terrain=game_context.get("current_hex", {}).get("terrain", "plains"),
            time_of_day=game_context.get("time_of_day", "day"),
            indoors=game_context.get("indoors", False),
            activity=game_context.get("activity", "idle"),
            mood=game_context.get("mood", "neutral"),
            tension=game_context.get("tension", 0.0),
            event=game_context.get("event"),
            presence=game_context.get("presence", "alone"),
            danger=game_context.get("danger", 0.0),
            fatigue=game_context.get("fatigue", 0.0),
            knowledge=game_context.get("knowledge", {}),
            topology_changes=game_context.get("topology_changes", []),
            sound_profile=game_context.get("sound_profile"),
            mood_modifier=game_context.get("mood_modifier"),
        )

    def update_from_party_position(self, col: int, row: int, sub_q: int = 0, sub_r: int = 0) -> None:
        """Update position fields."""
        self.position = (col, row, sub_q, sub_r)

    def update_from_hex(self, hex_data: dict) -> None:
        """Update terrain and location from hex data."""
        self.terrain = hex_data.get("terrain", self.terrain)
        # If there's a major POI, set location
        pois = hex_data.get("pois", [])
        discovered_pois = [p for p in pois if p.get("discovered")]
        if discovered_pois:
            # For now, just use the first discovered POI as location
            self.location = discovered_pois[0].get("name", "")