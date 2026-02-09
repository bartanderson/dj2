# tools/ai_assistant/cli/commands/tool_commands.py - ULTRA SIMPLE VERSION
"""
Tool discovery commands - SIMPLE VERSION THAT WORKS
"""

import sys
from pathlib import Path

from . import register_command

def tools_command(args):
    """Simple tool listing using tool_discovery module"""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    
    # Add scripts directory to path
    scripts_dir = project_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    
    try:
        from tool_discovery import list_tools
        query = getattr(args, 'query', None)
        list_tools(query)
        return 0
    except ImportError as e:
        print(f"Error importing tool_discovery: {e}")
        print(f"Scripts directory: {scripts_dir}")
        print(f"Python path: {sys.path[:3]}...")
        return 1

def tool_help_command(args):
    """Simple tool help using tool_discovery module"""
    if not args.tool_name:
        print("Error: tool name required")
        print("Usage: python ai.py tool-help <tool_name>")
        return 1
    
    project_root = Path(__file__).parent.parent.parent.parent.parent
    
    # Add scripts directory to path
    scripts_dir = project_root / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    
    try:
        from tool_discovery import get_tool_help
        get_tool_help(args.tool_name)
        return 0
    except ImportError as e:
        print(f"Error importing tool_discovery: {e}")
        print(f"Scripts directory: {scripts_dir}")
        return 1

# Register commands
register_command('tools', tools_command, "List and search available tools")
register_command('tool-help', tool_help_command, "Get detailed help for a tool", aliases=['th'])