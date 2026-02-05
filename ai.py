#!/usr/bin/env python3
"""
AI Assistant - Unified CLI Entry Point
Routes to modular implementation when available
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Main entry point - tries modular CLI first, falls back to legacy"""
    # Try modular CLI first
    try:
        from tools.ai_assistant.cli.command_router import main as modular_main
        print("[MODULAR] Using modular CLI (new structure)", file=sys.stderr)
        return modular_main()
    except ImportError as e:
        print(f"[WARN]  Modular CLI not available: {e}", file=sys.stderr)
        print("[FALLBACK] Falling back to legacy CLI...", file=sys.stderr)
    
    # Fall back to legacy CLI
    try:
        # Try to import from old location
        from tools.ai_assistant.cli import main as legacy_main
        return legacy_main()
    except ImportError as e:
        print(f"[ERROR] Could not load any CLI: {e}", file=sys.stderr)
        print("\nAvailable options:", file=sys.stderr)
        print("1. Check that tools/ai_assistant/cli/command_router.py exists", file=sys.stderr)
        print("2. Check that the old tools/ai_assistant/cli.py exists", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())