# tools/tool_utils.py
import inspect
import re
from typing import get_type_hints, Any, Dict, List, Optional, Union, Literal
from collections import namedtuple

def parse_google_docstring(docstring: str) -> Dict[str, str]:
    """
    Simple parser for Google-style docstrings.
    Returns a dict with 'description' and a dict of 'args' descriptions.
    """
    if not docstring:
        return {}
    lines = docstring.strip().split('\n')
    # Remove leading/trailing quotes
    lines = [l.rstrip() for l in lines if l.strip()]
    description = []
    args = {}
    current_arg = None
    in_args = False
    for line in lines:
        if line.strip().startswith('Args:'):
            in_args = True
            continue
        if in_args:
            if line.strip().startswith(('Returns:', 'Raises:', 'Yields:', 'Examples:')):
                in_args = False
                break
            # Look for lines like "    arg: description"
            match = re.match(r'\s+(\w+):\s*(.*)', line)
            if match:
                arg_name = match.group(1)
                arg_desc = match.group(2)
                args[arg_name] = arg_desc
            elif current_arg:
                # continuation line
                args[current_arg] += ' ' + line.strip()
        else:
            description.append(line)
    return {
        'description': ' '.join(description).strip(),
        'args': args
    }

def type_to_json_schema(typ) -> Dict[str, Any]:
    """Convert a Python type to a JSON schema type."""
    if typ is str:
        return {"type": "string"}
    if typ is int:
        return {"type": "integer"}
    if typ is float:
        return {"type": "number"}
    if typ is bool:
        return {"type": "boolean"}
    if typ is list or typ is List:
        return {"type": "array", "items": {}}
    if typ is dict or typ is Dict:
        return {"type": "object"}
    # Handle Optional[T]
    origin = getattr(typ, '__origin__', None)
    args = getattr(typ, '__args__', [])
    if origin is Union and type(None) in args:
        # Optional: get the non-None type
        non_none = [t for t in args if t is not type(None)][0]
        base = type_to_json_schema(non_none)
        # It's optional, but the schema doesn't have required; we'll handle required separately
        return base
    # Handle Literal
    if origin is Literal:
        # For enums, we'll use enum with the literal values
        return {"type": "string", "enum": list(args)}
    # Fallback
    return {"type": "string"}

def function_to_tool_schema(func) -> Dict[str, Any]:
    """
    Generate an OpenAI tool schema from a function's signature and docstring.
    Returns the inner function dict: { "name": ..., "description": ..., "parameters": ... }
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    doc = inspect.getdoc(func) or ""
    parsed_doc = parse_google_docstring(doc)

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        # Determine JSON schema type
        typ = type_hints.get(name, str)  # default to string if no hint
        schema = type_to_json_schema(typ)

        # Add description from docstring if available
        desc = parsed_doc.get('args', {}).get(name, f"Parameter {name}")
        schema["description"] = desc

        properties[name] = schema

        # Check if required (no default and not Optional)
        if param.default is param.empty:
            # Also need to check if type is Optional (union with None) – if so, not required
            # We handled Optional in type_to_json_schema, but the parameter still has no default
            # Actually, if the type is Optional, it's not required even without default? 
            # Usually Optional means you can pass None, but the parameter might still be required
            # We'll rely on the presence of a default value. If there is no default and the type is not Optional, then required.
            if not (getattr(typ, '__origin__', None) is Union and type(None) in getattr(typ, '__args__', [])):
                required.append(name)

    return {
        "name": func.__name__,
        "description": parsed_doc.get('description', func.__doc__ or "").strip(),
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }