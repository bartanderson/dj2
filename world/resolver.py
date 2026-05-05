# world/resolver.py
from typing import List, Dict, Any
from world.action_system import ActionQueue, Action
from world.tool_system import ToolRegistry
import traceback
from world.event_log import get_event_log

class ResolverLoop:
    def __init__(self, tool_registry: ToolRegistry, world_controller):
        self.tool_registry = tool_registry
        self.world = world_controller
        self.event_log = get_event_log()

    def resolve_queue(self, queue: ActionQueue) -> List[Dict[str, Any]]:
        results = []
        while not queue.is_empty():
            action = queue.dequeue()
            if action.status == "pending":
                tool = self.tool_registry.get_tool(action.tool_name)
                if not tool:
                    self.event_log.emit("tool.missing", {"tool_name": action.tool_name}, source_system="resolver")
                    action.status = "failed"
                    action.result = {"error": f"Tool '{action.tool_name}' not found"}
                else:
                    try:
                        self.event_log.emit("action.before", ...)
                        result = tool.execute(action.params)
                        action.status = "completed" if result.get("success") else "failed"
                        action.result = result
                    except Exception as e:
                        self.event_log.emit("action.error", {"tool": action.tool_name, "error": str(e), "trace": traceback.format_exc()}, source_system="resolver")
                        action.status = "failed"
                        action.result = {"error": str(e)}
                        get_event_log().emit("action.error", {
                            "tool": action.tool_name,
                            "error": str(e),
                            "trace": traceback.format_exc()
                        }, source_system="resolver")
                results.append(action.result)
        return results