# world/models/dialog.py

from dataclasses import dataclass
from datetime import datetime

@dataclass
class DialogResponse:
    speaker: str
    content: str
    type: str
    timestamp: datetime