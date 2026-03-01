# tools/bridge/__init__.py - UPDATED
"""
Bridge system exports – now using modular deepseek_lib.
"""

from .deepseek_lib import (
    connect_to_browser,
    find_deepseek_page,
    remove_file,
    is_file_attached,
    upload_file,
    send_message,
    wait_for_response,
    full_consult,
)

__all__ = [
    'connect_to_browser',
    'find_deepseek_page',
    'remove_file',
    'is_file_attached',
    'upload_file',
    'send_message',
    'wait_for_response',
    'full_consult',
]