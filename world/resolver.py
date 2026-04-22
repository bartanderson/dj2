# world/resolver.py
from typing import List, Dict, Any
from world.action_system import ActionQueue, Action
from world.tool_system import ToolRegistry

class ResolverLoop:
    def __init__(self, tool_registry: ToolRegistry, world_controller):
        self.tool_registry = tool_registry
        self.world = world_controller

    def resolve_queue(self, queue: ActionQueue) -> List[Dict[str, Any]]:
        results = []
        while not queue.is_empty():
            action = queue.dequeue()
            if action.status == "pending":
                tool = self.tool_registry.get_tool(action.tool_name)
                if not tool:
                    action.status = "failed"
                    action.result = {"error": f"Tool '{action.tool_name}' not found"}
                else:
                    try:
                        result = tool.execute(action.params)
                        action.status = "completed" if result.get("success") else "failed"
                        action.result = result
                    except Exception as e:
                        action.status = "failed"
                        action.result = {"error": str(e)}
                results.append(action.result)
        return results