# tools/ai_assistant/cli/commands/tool_commands.py
"""
Tool discovery commands for AI Assistant CLI
"""

import sys
from pathlib import Path

# Import registry
from . import register_command

# Try to import from scripts.tool_discovery
try:
    from scripts.tool_discovery import list_tools, get_tool_help, ai_suggest_tools
except ImportError:
    # Fallback: try to add the scripts directory to path
    scripts_dir = Path(__file__).parent.parent.parent.parent / 'scripts'
    if scripts_dir.exists():
        sys.path.insert(0, str(scripts_dir))
        from tool_discovery import list_tools, get_tool_help, ai_suggest_tools
    else:
        # If not found, create stubs
        def list_tools(query=None):
            print("Error: tool_discovery.py not found")
        
        def get_tool_help(tool_name):
            print(f"Error: tool_discovery.py not found, cannot get help for {tool_name}")
        
        def ai_suggest_tools(query):
            return None

def tools_command(args):
    """List and search available tools"""
    if args.query:
        list_tools(args.query)
    else:
        list_tools()
    
    # Also show AI suggestions if query provided
    if args.query and hasattr(args, 'ai_suggest') and args.ai_suggest:
        print("\n[AI TOOL SUGGESTIONS]")
        print("-" * 40)
        suggestions = ai_suggest_tools(args.query)
        if suggestions:
            print(suggestions)
    
    return 0

def tool_help_command(args):
    """Get detailed help for a tool"""
    if args.tool_name:
        get_tool_help(args.tool_name)
    else:
        print("Error: tool name required")
        print("Usage: python ai.py tool-help <tool_name>")
    
    return 0

# Register commands
register_command('tools', tools_command, "List and search available tools")
register_command('tool-help', tool_help_command, "Get detailed help for a tool", aliases=['th'])