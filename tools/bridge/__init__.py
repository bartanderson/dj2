# tools/bridge/__init__.py - UPDATED
"""
Bridge system exports
"""

from .deepseek_bridge_react import DeepSeekBridgeReact
from .bridge_controller import BridgeController

__all__ = [
    'DeepSeekBridgeReact', 
    'BridgeController'
]