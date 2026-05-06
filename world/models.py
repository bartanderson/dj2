from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class InventoryItem:
    id: str
    name: str
    value: int = 0
    quantity: int = 1


@dataclass
class Character:
    id: str
    name: str
    inventory: List[InventoryItem] = field(default_factory=list)


@dataclass
class SessionState:
    session_id: str
    player_id: str
    character_id: Optional[str] = None

    conversation_history: list = field(default_factory=list)
    pending_confirmation: Optional[dict] = None
    last_active: Optional[datetime] = None