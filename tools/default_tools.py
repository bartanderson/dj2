# tools\default_tools.py
import inspect
from tools import agent_tools

# Gather all public functions from agent_tools
TOOL_NAMES = [
    name for name, obj in inspect.getmembers(agent_tools)
    if inspect.isfunction(obj) and not name.startswith('_')
]

# Build TOOLS list in the required OpenAI function‑calling format
TOOLS = []
for name in TOOL_NAMES:
    func = getattr(agent_tools, name)
    sig = inspect.signature(func)
    properties = {}
    required = []
    for param_name, param in sig.parameters.items():
        # Basic type inference (could be extended)
        param_type = "string"
        properties[param_name] = {
            "type": param_type,
            "description": f"Parameter {param_name}"
        }
        if param.default == inspect.Parameter.empty:
            required.append(param_name)
    
    TOOLS.append({
        "function": {
            "name": name,
            "description": (func.__doc__ or "").strip(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    })

def get_handlers(db_path=None, project_root=None):
    """Return a dict mapping tool names to callables."""
    return {name: getattr(agent_tools, name) for name in TOOL_NAMES}