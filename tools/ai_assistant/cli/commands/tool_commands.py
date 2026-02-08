# tools/ai_assistant/cli/commands/tool_commands.py - ULTRA SIMPLE VERSION
"""
Tool discovery commands - SIMPLE VERSION THAT WORKS
"""

import sys
import json
from pathlib import Path

from . import register_command

def tools_command(args):
    """Simple tool listing that doesn't depend on scripts/"""
    project_root = Path(__file__).parent.parent.parent.parent.parent
    
    # Load tool_index.json directly
    tool_file = project_root / "ai_context" / "tool_index.json"
    
    if not tool_file.exists():
        print("[FAIL] tool_index.json not found")
        return 1
    
    try:
        with open(tool_file, 'r') as f:
            tools = json.load(f)
    except Exception as e:
        print(f"[FAIL] Error reading tool_index.json: {e}")
        return 1
    
    print("\n[TOOLS] AVAILABLE TOOLS (DJ2)")
    print("=" * 50)
    
    for category, tool_dict in tools.items():
        print(f"\n{category.upper()}:")
        for name, info in tool_dict.items():
            status = "[OK]" if info.get("tested") else "[WARN]"
            desc = info.get('description', 'No description')[:50]
            print(f"  {status} {name:<20} - {desc}...")
    
    return 0

def tool_help_command(args):
    """Simple tool help that doesn't depend on scripts/"""
    if not args.tool_name:
        print("Error: tool name required")
        return 1
    
    project_root = Path(__file__).parent.parent.parent.parent.parent
    tool_file = project_root / "ai_context" / "tool_index.json"
    
    if not tool_file.exists():
        print("[FAIL] tool_index.json not found")
        return 1
    
    with open(tool_file, 'r') as f:
        tools = json.load(f)
    
    # Search nested structure
    for category, tool_dict in tools.items():
        if args.tool_name in tool_dict:
            info = tool_dict[args.tool_name]
            print(f"\n[HELP] {args.tool_name.upper()}")
            print("=" * 40)
            print(f"Description: {info.get('description', 'N/A')}")
            print(f"Category: {category}")
            print(f"Tested: {'[OK] Yes' if info.get('tested') else '[WARN] No'}")
            print(f"Phase Safe: {'[OK] Yes' if info.get('phase_safe') else '[FAIL] No'}")
            print(f"\nCommand: {info.get('windows_cmd', 'N/A')}")
            return 0
    
    print(f"[FAIL] Tool '{args.tool_name}' not found")
    return 1

# Register commands
register_command('tools', tools_command, "List and search available tools")
register_command('tool-help', tool_help_command, "Get detailed help for a tool", aliases=['th'])