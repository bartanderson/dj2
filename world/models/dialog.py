# world/models/dialog.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class DialogResponse:
    speaker: str
    content: str
    dialog_type: str = "narration"
    timestamp: datetime = field(default_factory=datetime.utcnow)