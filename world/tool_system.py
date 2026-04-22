# world/tool_system.py
import inspect
from typing import Dict, Callable, Any, List, Optional

class Tool:
    def __init__(self, name: str, func: Callable, description: str, params: Dict[str, str],
                 param_types: Dict[str, type] = None, intent: str = None):
        self.name = name
        self.func = func
        self.description = description
        self.params = params
        self.param_types = param_types or {}
        self.intent = intent

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params
        }

    def to_prompt_string(self) -> str:
        if not self.params:
            return f"- {self.name}: {self.description} (no parameters)"
        params_str = ", ".join([f"{p}: {desc}" for p, desc in self.params.items()])
        return f"- {self.name}: {self.description} (parameters: {params_str})"

    def execute(self, arguments: dict) -> Any:
        return self.func(**arguments)

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.tools_by_intent: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.tools[tool.name] = tool
        if tool.intent:
            self.tools_by_intent[tool.intent] = tool

    def register_from_class(self, instance: object):
        for name, method in inspect.getmembers(instance, inspect.ismethod):
            if hasattr(method, 'is_tool'):
                tool_meta = getattr(method, 'tool_meta')
                sig = inspect.signature(method)
                param_types = {}
                for param_name, param in sig.parameters.items():
                    if param_name != 'self':
                        param_types[param_name] = param.annotation if param.annotation != inspect.Parameter.empty else str
                self.register(Tool(
                    name=tool_meta['name'],
                    func=method,
                    description=tool_meta['description'],
                    params=tool_meta['params'],
                    param_types=param_types,
                    intent=tool_meta.get('intent')
                ))

    def get_tools_spec(self) -> list:
        return [tool.to_dict() for tool in self.tools.values()]

    def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        return self.tools[tool_name].execute(arguments)

    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def get_tool_by_intent(self, intent: str) -> Optional[Tool]:
        return self.tools_by_intent.get(intent)

def tool(name: str, description: str, intent: str = None, **params: str):
    def decorator(func):
        func.is_tool = True
        func.tool_meta = {
            'name': name,
            'description': description,
            'params': params,
            'intent': intent
        }
        return func
    return decorator