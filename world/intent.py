from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass
class IntentFrame:
    action: str
    target: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    modifiers: Dict[str, Any] = field(default_factory=dict)