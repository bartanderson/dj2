# tools/bridge/deepseek_bridge_react.py - UPDATED
"""
DeepSeek Bridge - React-aware version using unified core
Maintains exact same interface for backward compatibility
"""

from .unified_core import BridgeCore
from typing import Optional

class DeepSeekBridgeReact:
    """React bridge using unified core implementation"""
    
    def __init__(self, verbose=True):
        self._core = BridgeCore(verbose=verbose)
        self._connected = False
    
    def connect(self) -> bool:
        """Connect to DeepSeek"""
        self._connected = self._core.connect()
        return self._connected
    
    def send_via_file_upload(self, text: str, filename: str = "context.txt") -> bool:
        """
        Upload file - main production method
        Returns True if upload appears successful
        """
        if not self._connected:
            if not self.connect():
                return False
        
        return self._core.upload_file(text, filename)
    
    def _simulate_real_typing(self, text: str) -> bool:
        """Keep for compatibility but log warning"""
        self._core._log("⚠️ Typing simulation disabled - use file upload instead")
        return False
    
    def _find_and_click_send(self) -> bool:
        """Keep for compatibility"""
        self._core._log("⚠️ Send method disabled - use file upload instead")
        return False
    
    def send(self, text: str) -> bool:
        """Send text - for short messages only"""
        self._core._log("⚠️ Direct send disabled for reliability - use file upload")
        return False
    
    def send_message(self, text: str) -> bool:
        """Alias for send"""
        return self.send(text)
    
    def ask(self, message: str, timeout: int = 180) -> Optional[str]:
        """
        Ask a question - automatically uses file upload for long content
        For backward compatibility only - prefer send_via_file_upload directly
        """
        if not self._connected:
            if not self.connect():
                return None
        
        # Always use file upload (more reliable)
        if self._core.upload_file(message, "query.txt"):
            return self._core.wait_for_response(timeout)
        return None
    
    def _wait_for_response(self, timeout: int = 180) -> Optional[str]:
        """Wait for response"""
        return self._core.wait_for_response(timeout)
    
    def receive(self) -> str:
        """Get latest response"""
        return self._core._get_response_text()
    
    def close(self):
        """Close connection"""
        self._core.close()
        self._connected = False