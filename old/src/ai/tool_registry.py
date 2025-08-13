from typing import Dict, Callable, Any, List
import inspect
import functools

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Dict] = {}
        self.implementations: Dict[str, Callable] = {}
        self.context = None  # Add context storage

    def set_context(self, context):
        """Set the execution context (DM agent instance)"""
        self.context = context
    
    def register(self, name: str, description: str, parameters: Dict):
        def decorator(func):
            # Store implementation
            self.implementations[name] = func
            
            # Create tool definition
            self.tools[name] = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": parameters,
                        "required": list(parameters.keys())
                    }
                }
            }
            
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Inject context if needed
                if 'context' in inspect.signature(func).parameters:
                    kwargs['context'] = self.context
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_tools(self) -> List[Dict]:
        return list(self.tools.values())
    
    def execute(self, tool_name: str, arguments: Dict) -> Any:
        if tool_name not in self.implementations:
            raise ValueError(f"Tool '{tool_name}' not registered")
            
        # Inject context if the function requires it
        func = self.implementations[tool_name]
        if 'context' in inspect.signature(func).parameters:
            arguments['context'] = self.context
        
        return func(**arguments)

# Global registry instance
registry = ToolRegistry()