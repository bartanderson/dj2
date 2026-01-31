#tools/bridge/bridge_controller.py
"""
Bridge Controller - Simplified version without backup dependencies
"""

import json
import subprocess
from typing import Dict, List, Optional
import re
import time

class BridgeController:
    """Simplified bridge controller"""
    
    def __init__(self, deepseek_bridge=None):
        self.deepseek_bridge = deepseek_bridge
        self.conversation_history = []
    
    def ask_deepseek(self, question: str, use_tools: bool = True) -> Optional[str]:
        """Ask DeepSeek a question, optionally using tools for context"""
        try:
            print(f"\n[BridgeController] Asking: {question[:50]}...")
            print(f"[BridgeController] Bridge exists: {self.deepseek_bridge is not None}")
            print(f"[BridgeController] Bridge connected: {getattr(self.deepseek_bridge, '_connected', False)}")
            
            # Step 1: Get current context from our tools if needed
            context = ""
            if use_tools:
                context = self._get_context_for_question(question)
            
            # Step 2: Format the question with context
            if context:
                full_query = f"{context}\n\nQuestion: {question}"
            else:
                full_query = question
            
            print(f"[BridgeController] Full query: {full_query[:100]}...")
            
            # Step 3: Send to DeepSeek via bridge
            if self.deepseek_bridge:
                print(f"[BridgeController] Calling bridge.ask()...")
                response = self.deepseek_bridge.ask(full_query)
                print(f"[BridgeController] Bridge returned: {type(response)}")
                print(f"[BridgeController] Response preview: {repr(response)[:100] if response else 'None'}")
            else:
                print("⚠️ No DeepSeek bridge available, using fallback")
                response = f"Simulated response to: {question[:50]}..."
            
            # Step 4: Store in history
            self.conversation_history.append({
                "question": question,
                "response": response,
                "timestamp": "2026-01-27"
            })
            
            return response
            
        except Exception as e:
            print(f"❌ Error in ask_deepseek: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_context_for_question(self, question: str) -> str:
        """Get relevant code context"""
        try:
            print(f"🔍 Getting context...")
            
            # Try to use ai.py context if available
            try:
                # Import from our new structure
                import sys
                sys.path.insert(0, '.')
                from tools.ai_assistant.context_builder import BridgeAgent
                from tools.ai_assistant.indexer import CodebaseIndexer
                
                indexer = CodebaseIndexer()
                agent = BridgeAgent(indexer)
                context = agent.build_context_for_query(question)
                return context.get('structured_context', {}).get('key_insights', '')
                
            except ImportError:
                # Fallback: simple search
                cmd = f'python ai.py search "{question[:50]}" --limit 3'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout[:1000]
                return "No context available."
                
        except Exception as e:
            print(f"❌ Context error: {e}")
            return ""
    
    def _check_and_execute_tools(self, response: str) -> str:
        """Check for tool calls and execute them"""
        tool_patterns = {
            'search': r'\[TOOL:search\](.*?)\[/TOOL\]',
            'extract': r'\[TOOL:extract\](.*?)\[/TOOL\]',
            'find_class': r'\[TOOL:find_class\](.*?)\[/TOOL\]'
        }
        
        results = []
        
        for tool_name, pattern in tool_patterns.items():
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                args = match.strip()
                print(f"🛠️ Executing {tool_name}: {args[:50]}...")
                
                try:
                    if tool_name == 'search':
                        result = self._run_ai_command(f'search "{args}"')
                    elif tool_name == 'extract':
                        result = self._run_ai_command(f'extract --component {args}')
                    elif tool_name == 'find_class':
                        parts = args.split()
                        if len(parts) >= 2:
                            result = self._run_ai_command(f'find-class {parts[0]} {parts[1]}')
                        else:
                            result = f"Invalid args for find-class: {args}"
                    else:
                        result = f"Unknown tool: {tool_name}"
                    
                    results.append(f"{tool_name}: {result[:200]}...")
                    
                except Exception as e:
                    results.append(f"{tool_name} error: {e}")
        
        return "\n".join(results) if results else ""
    
    def _run_ai_command(self, command: str) -> str:
        """Run an ai.py command"""
        try:
            cmd = f"python ai.py {command}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr[:200]}"
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Exception: {e}"
    
    def get_conversation_summary(self) -> str:
        """Get formatted conversation history"""
        summary = []
        for i, entry in enumerate(self.conversation_history):
            summary.append(f"Turn {i+1}:")
            summary.append(f"  Q: {entry['question'][:80]}...")
            if entry['response']:
                summary.append(f"  A: {entry['response'][:80]}...")
        
        return "\n".join(summary)