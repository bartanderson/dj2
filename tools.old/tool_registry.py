"""
Tool registry – decorator to register functions as tools.
Allows attaching schema overrides without modifying other files.
"""

import functools
from typing import Dict, Any, Callable

_TOOL_REGISTRY: Dict[str, Callable] = {}
_TOOL_SCHEMA_OVERRIDES: Dict[str, Dict[str, Any]] = {}

def tool(name: str = None, schema_override: Dict[str, Any] = None):
    """
    Decorator to register a function as a tool.

    Args:
        name: Optional custom name for the tool (defaults to function name).
        schema_override: Optional dictionary of JSON schema keywords to merge
                         into the auto‑generated parameters schema.
                         Should only contain top‑level keywords like
                         `additionalProperties`, `minItems`, etc. Do NOT include
                         `properties` or `required` unless you intend to replace
                         the entire parameters object.
    """
    def decorator(func: Callable):
        tool_name = name or func.__name__
        if tool_name in _TOOL_REGISTRY:
            raise ValueError(f"Duplicate tool name: {tool_name}")
        _TOOL_REGISTRY[tool_name] = func
        if schema_override:
            _TOOL_SCHEMA_OVERRIDES[tool_name] = schema_override
        return func
    return decorator

def get_all_tools():
    """Return a list of (name, func) for all registered tools."""
    return list(_TOOL_REGISTRY.items())

def get_tool_schema_override(name: str) -> Dict[str, Any]:
    """Return any schema override for the given tool."""
    return _TOOL_SCHEMA_OVERRIDES.get(name, {})