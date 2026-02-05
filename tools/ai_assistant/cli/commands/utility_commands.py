"""
Utility commands for AI Assistant CLI
"""
import sys
import os
from pathlib import Path

# Import registry
from . import register_command

def tools_command(args):
    """List and search available tools"""
    # Add scripts directory to Python path
    project_root = Path(__file__).parent.parent.parent.parent.parent  # dj2 root
    scripts_dir = project_root / "scripts"
    
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    
    try:
        # Now import from scripts directory
        from tool_discovery import list_tools
        query = getattr(args, 'query', None)
        list_tools(query)
        return 0
    except ImportError as e:
        print(f"Error importing tool_discovery: {e}")
        print(f"Scripts directory: {scripts_dir}")
        print(f"Python path: {sys.path}")
        return 1

def tool_help_command(args):
    """Get detailed help for a tool"""
    # Add scripts directory to Python path
    project_root = Path(__file__).parent.parent.parent.parent.parent  # dj2 root
    scripts_dir = project_root / "scripts"
    
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    
    try:
        # Now import from scripts directory
        from tool_discovery import get_tool_help
        get_tool_help(args.tool_name)
        return 0
    except ImportError as e:
        print(f"Error importing tool_discovery: {e}")
        print(f"Scripts directory: {scripts_dir}")
        return 1

# Register utility commands
register_command('tools', tools_command, "List and search available tools")
register_command('tool-help', tool_help_command, "Get detailed help for a tool")