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
    "arch_context",
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
    "display_file", #alias for read_file
    "list_files",
    "parse_json_file",
]

# Build TOOLS list in the required OpenAI function‑calling format
TOOLS = []
for name in TOOL_WHITELIST:
    func = getattr(agent_tools, name)
    sig = inspect.signature(func)
    #print(f"[default_tools] {name} has {len(sig.parameters)} parameters: {list(sig.parameters.keys())}")
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
    # Override list_files with proper schema
    for tool in TOOLS:
        if tool['function']['name'] == 'list_files':
            tool['function']['parameters'] = {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to list files from, relative to project root (default: '.')"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File pattern, e.g., '*.py' (default: '*')"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to search subdirectories recursively (default: false)"
                    }
                },
                "required": []
            }
            break
    # Override deepseek_consult with proper parameter types and descriptions
    for tool in TOOLS:
        if tool['function']['name'] == 'deepseek_consult':
            tool['function']['parameters'] = {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The main question or instruction."
                    },
                    "file": {
                        "type": "string",
                        "description": "Optional path to a file to upload. The file's content is uploaded separately."
                    },
                    "data": {
                        "type": "string",
                        "description": "Optional additional data to include in the prompt (converted to string)."
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Maximum seconds to wait for response. Default: 3600."
                    }
                },
                "required": ["prompt"]
            }
            break

def get_handlers(db_path=None, project_root=None):
    """Return a dict mapping tool names to callables."""
    return {name: getattr(agent_tools, name) for name in TOOL_WHITELIST}