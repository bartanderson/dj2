# tools/bridge/bridge_controller.py - UPDATED
"""
Bridge Controller - Updated to use React bridge for file upload capability
"""

from typing import Optional
import subprocess
import time

class BridgeController:
    """Bridge controller using React bridge for file uploads"""
    
    def __init__(self, bridge=None):
        # Use React bridge by default (has file upload capability)
        if bridge is None:
            from .deepseek_bridge_react import DeepSeekBridgeReact
            self.bridge = DeepSeekBridgeReact(verbose=True)
        else:
            self.bridge = bridge
        
        self.conversation_history = []
    
    def ask_deepseek(self, question: str, use_tools: bool = True, timeout: int = 3600) -> Optional[str]:
        """Ask DeepSeek using file upload for reliability"""
        try:
            print(f"\n[BridgeController] Asking: {question[:50]}...")
            
            # Get context if needed
            context = ""
            if use_tools:
                context = self._get_context_for_question(question)
            
            # Always use file upload for reliability
            if not self.bridge.connect():
                print("❌ Failed to connect to DeepSeek")
                return None
            
            # Build full content
            if context:
                full_content = f"Context:\n{context}\n\nQuestion: {question}"
            else:
                full_content = question
            
            print(f"[BridgeController] Using file upload for {len(full_content)} chars")
            
            # Upload file and wait for response
            if self.bridge.send_via_file_upload(full_content, "analysis_context.txt"):
                response = self.bridge._wait_for_response(timeout=180)
            else:
                print("❌ File upload failed")
                return None
            
            # Store history
            self.conversation_history.append({
                "question": question,
                "response": response,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            return response
            
        except Exception as e:
            print(f"❌ Error in ask_deepseek: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_context_for_question(self, question: str) -> str:
        """Get context for question (simplified)"""
        try:
            # Use ai.py search for context
            cmd = ['python', 'ai.py', 'search', question[:50], '--limit', '3']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout[:1000]
            return ""
        except:
            return ""
    
    def get_conversation_summary(self) -> str:
        """Get conversation summary"""
        summary = []
        for i, entry in enumerate(self.conversation_history):
            summary.append(f"Turn {i+1}:")
            summary.append(f"  Q: {entry['question'][:80]}...")
            if entry['response']:
                summary.append(f"  A: {entry['response'][:80]}...")
        
        return "\n".join(summary)