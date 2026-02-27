#!/usr/bin/env python3
# inspect_tools.py
import json
from pathlib import Path
import sys

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from agent_tools import (
    semantic_search,
    arch_context,
    search_files,
    read_file,
    analyze_tools
)

def inspect():
    print("="*60)
    print("SEMANTIC SEARCH (query='database', limit=2)")
    print("="*60)
    result = semantic_search("database", 2)
    print(json.dumps(result, indent=2))
    print()

    print("="*60)
    print("ARCH_CONTEXT (query='database', level='standard')")
    print("="*60)
    result = arch_context("database", "standard")
    # Try to parse as JSON; if fails, print raw
    try:
        parsed = json.loads(result)
        print(json.dumps(parsed, indent=2))
    except:
        print(result[:1000])  # first 1000 chars if not JSON
    print()

    print("="*60)
    print("SEARCH_FILES (query='*.py', limit=3)")
    print("="*60)
    result = search_files("*.py", 3)
    print(json.dumps(result, indent=2))
    print()

    print("="*60)
    print("ANALYZE_TOOLS (run tool analyzer)")
    print("="*60)
    try:
        result = analyze_tools()
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    print()

if __name__ == "__main__":
    inspect()