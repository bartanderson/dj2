# tools\default_tools.py
import inspect
from tools import agent_tools

# Only these functions should be exposed as tools
TOOL_WHITELIST = [
    "search_files",
    "read_file",
    "read_files",
    "write_file",
    "analyze_tools",
    #"arch_context", disabled till fixed
    "deepseek_consult",
    "semantic_search",
    "create_branch",
    "commit_changes",
    "gather_context",
    "show_diff",
    "file_metadata",
    "file_imports",
    "file_importers",
    "test_coverage",
    "file_concepts",
    "concept_files",
    "cluster_files",
    "function_contract",
    "function_parameters",
    "extract_code",
    "list_functions",
]

# Build TOOLS list in the required OpenAI function‑calling format
TOOLS = []
for name in TOOL_WHITELIST:
    func = getattr(agent_tools, name)
    sig = inspect.signature(func)
    properties = {}
    required = []
    for param_name, param in sig.parameters.items():
        param_type = "string"  # Simplified; you could improve this
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
    return {name: getattr(agent_tools, name) for name in TOOL_WHITELIST}