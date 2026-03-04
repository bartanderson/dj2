# tools\default_tools.py
import inspect
from tools import agent_tools
from tools.tool_utils import function_to_tool_schema


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
    "retrieve_knowledge",
]

# Build TOOLS list using introspection
TOOLS = []
for name in TOOL_WHITELIST:
    func = getattr(agent_tools, name)
    tool_func_schema = function_to_tool_schema(func)
    TOOLS.append({
        "type": "function",
        "function": tool_func_schema
    })

def get_handlers(db_path=None, project_root=None):
    """Return a dict mapping tool names to callables."""
    return {name: getattr(agent_tools, name) for name in TOOL_WHITELIST}