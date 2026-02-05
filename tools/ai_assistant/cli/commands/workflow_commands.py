"""
Workflow and bridge-related commands for AI Assistant CLI
Fixed version - ensures all commands register properly
"""
import sys
from pathlib import Path

# Import registry FIRST to avoid circular imports
try:
    # When imported as module
    from . import register_command
except ImportError:
    # When run directly
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from commands import register_command

def context_command(args):
    """Build context for DeepSeek analysis"""
    print("Context command - placeholder")
    print(f"Query: {getattr(args, 'query', 'None')}")
    print(f"Interactive: {getattr(args, 'interactive', False)}")
    return 0

def validate_command(args):
    """Validate a DeepSeek response"""
    print("Validate command - placeholder")
    return 0

def guardrails_command(args):
    """Show and validate guardrails"""
    print("Guardrails command - placeholder")
    return 0

def phase_check_command(args):
    """Check phase compliance for specific files or patterns"""
    print("Phase-check command - placeholder")
    return 0

def bridge_status_command(args):
    """Check AI Bridge status"""
    print("Bridge-status command - placeholder")
    return 0

# REGISTER ALL COMMANDS - CRITICAL: This must execute
register_command('context', context_command, "Build context for DeepSeek")
register_command('validate', validate_command, "Validate a DeepSeek response")
register_command('guardrails', guardrails_command, "Show and validate guardrails")
register_command('phase-check', phase_check_command, "Check phase compliance")
register_command('bridge-status', bridge_status_command, "Check AI Bridge status")

# Debug: Print when module loads
if __name__ != "__main__":
    print(f"[DEBUG] workflow_commands.py loaded - registered {5} commands")
