# world/intent.py
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class IntentFrame:
    # Core action
    action: str
    category: str = "other"   # movement, economy, social, exploration, other
    target: Optional[str] = None
    item: Optional[str] = None
    destination: Optional[str] = None
    price: Optional[int] = None

    # Motivations and context
    motivation: Optional[str] = None
    mood: Optional[str] = None
    relationship_goal: Optional[str] = None
    manner: Optional[str] = None

    # Multi‑turn conversation support
    conversation_id: Optional[str] = None
    clarification_needed: bool = False
    missing_fields: List[str] = field(default_factory=list)

    # Additional free‑form context
    context: Dict[str, Any] = field(default_factory=dict)

    # Raw input for debugging
    raw_text: str = ""