# world/action_system.py
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import deque

@dataclass
class Action:
    tool_name: str
    params: Dict[str, Any]
    modifiers: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"   # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None

class ActionQueue:
    def __init__(self):
        self.queue = deque()

    def enqueue(self, action: Action):
        self.queue.append(action)

    def enqueue_front(self, action: Action):
        self.queue.appendleft(action)

    def dequeue(self) -> Optional[Action]:
        if self.queue:
            return self.queue.popleft()
        return None

    def clear(self):
        self.queue.clear()

    def is_empty(self) -> bool:
        return len(self.queue) == 0

class ActionPlanner:
    def __init__(self, tool_registry):
        self.tool_registry = tool_registry
        # Map intent to tool name (static for now)
        self.intent_to_tool = {
            "move": "move_tool",
            "buy": "merchant_buy",
            "sell": "merchant_sell",
            "haggle": "merchant_haggle",
        }

    def plan(self, intent: str, parameters: Dict[str, Any]) -> List[Action]:
        tool_name = self.intent_to_tool.get(intent)
        if not tool_name:
            return []   # no action (e.g., "answer" intent)
        # Optional: validate parameters here
        return [Action(tool_name=tool_name, params=parameters)]