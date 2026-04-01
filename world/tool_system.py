    # TODO: When integrating new tools, ensure that any tool invocation checks for valid, registered tool names.
    # If a tool is not found or specified as null/None, fallback to narrative handling and avoid execution errors.
import inspect
import json
import re
from typing import Dict, Callable, Any, List, Optional

class Tool:
    def __init__(self, name: str, func: Callable, description: str, params: Dict[str, str], param_types: Dict[str, type] = None):
        self.name = name
        self.func = func
        self.description = description
        self.params = params  # param name -> description
        self.param_types = param_types or {}  # param name -> type (for validation)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params
        }
    
    def to_prompt_string(self) -> str:
        """Generate a human-readable description for the system prompt."""
        if not self.params:
            return f"- {self.name}: {self.description} (no parameters)"
        params_str = ", ".join([f"{p}: {desc}" for p, desc in self.params.items()])
        return f"- {self.name}: {self.description} (parameters: {params_str})"
    
    def execute(self, arguments: dict) -> Any:
        return self.func(**arguments)

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool):
        self.tools[tool.name] = tool
    
    def register_from_class(self, instance: object):
        """Automatically register all methods decorated with @tool"""
        for name, method in inspect.getmembers(instance, inspect.ismethod):
            if hasattr(method, 'is_tool'):
                tool_meta = getattr(method, 'tool_meta')
                # Get parameter types from function signature
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
                    param_types=param_types
                ))
    
    def get_tools_spec(self) -> list:
        return [tool.to_dict() for tool in self.tools.values()]
    
    def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")
        return self.tools[tool_name].execute(arguments)
    
    def get_tool(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

def tool(name: str, description: str, **params: str):
    """Decorator to mark methods as tools with parameter descriptions."""
    def decorator(func):
        func.is_tool = True
        func.tool_meta = {
            'name': name,
            'description': description,
            'params': params
        }
        return func
    return decorator