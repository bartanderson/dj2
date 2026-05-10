"""
Command Registry for AI Assistant CLI
"""
import importlib
from typing import Dict, Callable, Any

COMMAND_REGISTRY: Dict[str, dict] = {}

def register_command(name: str, func: Callable, help_text: str = "", aliases: list = None):
    """Register a command in the global registry."""
    COMMAND_REGISTRY[name] = {
        'func': func,
        'help': help_text,
        'aliases': aliases or []
    }

def get_command(name: str) -> Dict[str, Any]:
    """Get command from registry, checking aliases."""
    if name in COMMAND_REGISTRY:
        return COMMAND_REGISTRY[name]
    
    # Check aliases
    for cmd_name, cmd_info in COMMAND_REGISTRY.items():
        if cmd_info['aliases'] and name in cmd_info['aliases']:
            return cmd_info
    
    return None

def list_commands() -> Dict[str, str]:
    """List all registered commands with their help text."""
    return {name: info['help'] for name, info in COMMAND_REGISTRY.items()}

def load_command_module(module_name: str):
    """Dynamically load a command module to register commands."""
    try:
        importlib.import_module(module_name)
    except ImportError as e:
        print(f"Warning: Could not load command module {module_name}: {e}")

# Auto-register modules when imported
__all__ = ['register_command', 'get_command', 'list_commands', 'load_command_module']