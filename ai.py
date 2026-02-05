# Updated ai.py (clean version)
#!/usr/bin/env python3
"""
AI Assistant - Main Entry Point
Now using modular CLI structure
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point - always use modular CLI"""
    try:
        from tools.ai_assistant.cli.command_router import main as modular_main
        return modular_main()
    except ImportError as e:
        print(f"Error: Failed to load modular CLI: {e}", file=sys.stderr)
        print("\nPlease ensure:", file=sys.stderr)
        print("1. tools/ai_assistant/cli/command_router.py exists", file=sys.stderr)
        print("2. All command modules are in place", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())