#!/usr/bin/env python3
"""
Quick tool discovery - references ai_context/tool_index.json
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\bartl\dev\dj2")
AI_CONTEXT = PROJECT_ROOT / "ai_context"

# In tool_discovery.py, add this new function:

def ai_suggest_tools(query: str = None):
    """Use local AI to suggest tools based on the query."""
    try:
        from tools.ollama_client import get_ollama_client
        client = get_ollama_client()
        
        if not client.is_available():
            print("[INFO] Ollama not available for AI suggestions")
            return None
        
        # Load tool index
        tool_file = AI_CONTEXT / "tool_index.json"
        if not tool_file.exists():
            print("[INFO] No tool_index.json found")
            return None
            
        with open(tool_file, 'r') as f:
            tools = json.load(f)
        
        # Flatten tools for prompt
        tool_list = []
        for category, tool_dict in tools.items():
            for name, info in tool_dict.items():
                tool_list.append(f"{category}/{name}: {info.get('description', '')}")
        
        tools_text = "\n".join(tool_list[:30])  # First 30 tools
        
        prompt = f"""User needs help with: {query or 'general development'}

Available tools:
{tools_text}

Suggest 2-3 most relevant tools for this task.
For each tool, provide:
1. Why it's relevant
2. Simple example command

Format as concise bullet points."""
        
        response = client.quick_chat(prompt, max_lines=6)
        return response
        
    except Exception as e:
        print(f"[INFO] AI suggestion failed: {e}")
        return None

def list_tools(query: str = None):
    """List or search tools from ai_context/tool_index.json"""
    
    tool_file = AI_CONTEXT / "tool_index.json"
    
    if not tool_file.exists():
        print("[FAIL] tool_index.json not found in ai_context/")
        print("       Run: Create ai_context/tool_index.json first")
        return
    
    try:
        with open(tool_file, 'r') as f:
            tools = json.load(f)
    except Exception as e:
        print(f"[FAIL] Error reading tool_index.json: {e}")
        return

    # Get AI suggestions FIRST if query provided
    ai_suggestions = None
    if query:
        print(f"\n[AI TOOL SUGGESTIONS]")
        print("-" * 40)
        ai_suggestions = ai_suggest_tools(query)
        if ai_suggestions:
            print(ai_suggestions)
            print("-" * 40)
    
    if query:
        # Search for matching tools
        results = []
        query_lower = query.lower()
        
        for category, tool_dict in tools.items():
            for name, info in tool_dict.items():
                searchable = f"{category} {name} {info.get('description', '')}".lower()
                if query_lower in searchable:
                    results.append((category, name, info))
        
        if results:
            print(f"[SEARCH] Found {len(results)} tools matching '{query}':")
            for cat, name, info in results:
                print(f"\n[ITEM] {cat}/{name}")
                print(f"       {info.get('description', 'No description')}")
                print(f"       Cmd: {info.get('windows_cmd', 'N/A')}")
                status = "[OK]" if info.get("tested") else "[WARN]"
                print(f"       Status: {status} tested")
        else:
            print(f"[FAIL] No tools found matching '{query}'")
            list_all_tools(tools)
    else:
        list_all_tools(tools)

def list_all_tools(tools=None):
    """List all available tools with status"""
    if tools is None:
        tool_file = AI_CONTEXT / "tool_index.json"
        if tool_file.exists():
            with open(tool_file, 'r') as f:
                tools = json.load(f)
        else:
            print("[FAIL] tool_index.json not found")
            return
    
    print("\n[TOOLS] AVAILABLE TOOLS (DJ2)")
    print("=" * 50)
    
    for category, tool_dict in tools.items():
        print(f"\n{category.upper()}:")
        for name, info in tool_dict.items():
            status = "[OK]" if info.get("tested") else "[WARN]"
            desc = info.get('description', 'No description')[:50]
            print(f"  {status} {name:<20} - {desc}...")

def get_tool_help(tool_name: str):
    """Get detailed help for a specific tool"""
    tool_file = AI_CONTEXT / "tool_index.json"
    
    if not tool_file.exists():
        print("[FAIL] tool_index.json not found")
        return
    
    with open(tool_file, 'r') as f:
        tools = json.load(f)
    
    # Search nested structure
    for category, tool_dict in tools.items():
        if tool_name in tool_dict:
            info = tool_dict[tool_name]
            print(f"\n[HELP] {tool_name.upper()}")
            print("=" * 40)
            print(f"Description: {info.get('description', 'N/A')}")
            print(f"Category: {category}")
            print(f"Tested: {'[OK] Yes' if info.get('tested') else '[WARN] No'}")
            print(f"Phase Safe: {'[OK] Yes' if info.get('phase_safe') else '[FAIL] No'}")
            print(f"\nCommand: {info.get('windows_cmd', 'N/A')}")
            if 'example' in info:
                print(f"Example: {info['example']}")
            if 'note' in info:
                print(f"\nNote: {info['note']}")
            return
    
    print(f"[FAIL] Tool '{tool_name}' not found")
    print("Run without arguments to see all tools")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" and len(sys.argv) > 2:
            get_tool_help(sys.argv[2])
        else:
            list_tools(" ".join(sys.argv[1:]))
    else:
        list_tools()