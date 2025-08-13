import inspect
import json
import re
from typing import Dict, Callable, Any, List, Optional

class Tool:
    def __init__(self, name: str, func: Callable, description: str, params: Dict[str, str]):
        self.name = name
        self.func = func
        self.description = description
        self.params = params
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params
        }
    
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
                self.register(Tool(
                    name=tool_meta['name'],
                    func=method,
                    description=tool_meta['description'],
                    params=tool_meta['params']
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
    """Decorator to mark methods as tools"""
    def decorator(func):
        func.is_tool = True
        func.tool_meta = {
            'name': name,
            'description': description,
            'params': params
        }
        return func
    return decorator