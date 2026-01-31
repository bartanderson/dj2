#!/usr/bin/env python
"""
Primary AI Assistant interface for Dungeon Journey 2
Simplified version without backup functionality
"""
import sys
import os

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))

try:
    from ai_assistant.cli import main
    sys.exit(main())
except ImportError as e:
    print(f"Error: Could not import AI assistant: {e}")
    print("Make sure you're in the project root directory.")
    sys.exit(1)