# scripts/ai_workflow.py
"""
AI Workflow Manager - Enhanced version with verbose logging
"""
import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
import os

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    parser = argparse.ArgumentParser(description="AI Workflow Manager")
    parser.add_argument("action", 
                       choices=["start", "continue", "status", "send", 
                               "local-analyze", "test-ollama"], 
                       help="Action to perform")
    parser.add_argument("--topic", "-t", help="Session topic")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Verbose logging")
    parser.add_argument("--send", "-s", action="store_true", 
                       help="Send to DeepSeek (for start action)")
    parser.add_argument("--model", default="llama3.2:3b", 
                       help="Ollama model to use (for local-analyze)")
    
    args = parser.parse_args()
    
    if args.action == "start":
        start_session(args.topic, verbose=args.verbose, send_to_deepseek=args.send)
    elif args.action == "continue":
        continue_session(args.topic, verbose=args.verbose)
    elif args.action == "status":
        show_status()
    elif args.action == "send":
        send_to_deepseek()
    elif args.action == "local-analyze":
        local_analyze_command(args)
    elif args.action == "test-ollama":
        test_ollama_command(args)
    else:
        print(f"Unknown action: {args.action}")
        sys.exit(1)

def start_session(topic: str, verbose: bool = False, send_to_deepseek: bool = False):
    """Start a new AI session"""
    print(f"[START] Starting AI session: {topic}")
    
    # Import here to avoid circular imports
    from context_manager import ContextManager
    
    # Initialize context manager
    cm = ContextManager(verbose=verbose)
    
    # Check for existing session
    session_path = Path("ai_context/session/current_session.json")
    if session_path.exists():
        with open(session_path, 'r') as f:
            existing = json.load(f)
        
        existing_topic = existing.get('topic', 'Unknown')
        
        # Check if we should continue existing session
        if existing_topic and existing_topic.lower() in topic.lower():
            print(f"[CONTINUE] Continuing session: {existing_topic}")
            session_state = existing
            
            # Add history entry
            if 'history' not in session_state:
                session_state['history'] = []
            
            session_state['history'].append({
                'timestamp': datetime.now().isoformat(),
                'action': 'continued_from',
                'previous_topic': existing_topic
            })
        else:
            print(f"[NEW] Starting new session (previous was: {existing_topic})")
            # Archive old session
            archive_session(existing)
            session_state = {
                'topic': topic,
                'started': datetime.now().isoformat(),
                'history': []
            }
    else:
        print("[NEW] Starting first session")
        session_state = {
            'topic': topic,
            'started': datetime.now().isoformat(),
            'history': []
        }
    
    # Build context package
    print("[CONTEXT] Building context package...")
    
    # Use a better query for search - extract key terms
    import re
    # Remove common words and take first 3-4 meaningful words
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                    'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 
                    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did'}
    
    words = topic.lower().split()
    key_terms = [word for word in words if word not in common_words]
    search_query = ' '.join(key_terms[:4]) if key_terms else topic[:40]
    
    print(f"[SEARCH] Using search query: '{search_query}'")
    package = cm.build_package(target="deepseek", max_tokens=5000, query=search_query)
    
    # Update session state
    session_state['updated'] = datetime.now().isoformat()
    
    # Get the files count from the correct location
    files_count = 0
    if 'components' in package and 'code' in package['components']:
        files_count = len(package['components']['code'].get('files', []))
    elif 'files' in package:  # Fallback for old format
        files_count = len(package['files'])
    
    session_state['context_summary'] = {
        'token_estimate': package.get('token_estimate', 0),
        'files_found': files_count,
        'violations': package.get('components', {}).get('violations', '')[:200] + '...' if len(package.get('components', {}).get('violations', '')) > 200 else package.get('components', {}).get('violations', '')
    }
    
    # Add history entry
    session_state['history'].append({
        'timestamp': datetime.now().isoformat(),
        'action': 'context_generated',
        'token_estimate': package.get('token_estimate', 0),
        'files_found': files_count  # Use the same count we calculated above
    })
    
    # Save context to file
    context_file = Path("ai_context/session/context_for_ai.txt")
    context_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(context_file, 'w', encoding='utf-8') as f:
        f.write(package.get('formatted', ''))
    
    # Save session state
    session_path.parent.mkdir(parents=True, exist_ok=True)
    with open(session_path, 'w') as f:
        json.dump(session_state, f, indent=2)
    
    print(f"[OK] Session started")
    print(f"    Topic: {topic}")
    print(f"    Context tokens: ~{package.get('token_estimate', 0)}")
    print(f"    Files found: {files_count}") # print(f"    Files found: {len(package.get('files', []))}")
    
    print(f"\n[FILES] Context saved to: {context_file.absolute()}")
    print(f"        Session state: {session_path.absolute()}")
    
    # Send to DeepSeek if requested
    if send_to_deepseek:
        send_to_deepseek_bridge(package.get('formatted', ''), topic)
    
    return session_state

def local_analyze_command(args):
    """Use local AI for quick analysis without DeepSeek."""
    try:
        # Add tools directory to path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from tools.ollama_client import get_ollama_client
    except ImportError:
        print("[ERROR] ollama_client.py not found in tools/ directory")
        print("Make sure you created tools/ollama_client.py")
        return 1
    
    query = args.topic
    if not query:
        query = input("What would you like to analyze locally? ")
    
    print(f"\n[LOCAL AI] Analyzing: {query}")
    print("-" * 60)
    
    client = get_ollama_client(args.model)
    
    if not client.is_available():
        print("[ERROR] Ollama not available. Make sure 'ollama serve' is running")
        print("Run this command to check: ollama list")
        return 1
    
    # Warm up the model (optional)
    if args.verbose:
        print("[INFO] Warming up model...")
        client.ensure_model_loaded(keep_alive="5m")
    
    # Get project context using existing context_manager
    from context_manager import ContextManager
    cm = ContextManager(verbose=args.verbose)
    
    print("[INFO] Building context...")
    context_package = cm.build_package(
        target="ollama", 
        max_tokens=1500, 
        query=query
    )
    
    # Build the prompt
    prompt = f"""Development Analysis: {query}

Context Summary:
{context_package.get('formatted', '')[:1000]}

Provide:
1. Top 3 technical considerations
2. Potential phase boundary issues
3. Next steps (specific tools/commands)
4. DeepSeek needed? (Yes/No with reason)

Format: Concise bullet points, 5 lines max."""
    
    print("[INFO] Querying local AI...")
    response = client.quick_chat(prompt, max_lines=5)
    
    print("\n" + "=" * 60)
    print("LOCAL AI ANALYSIS")
    print("=" * 60)
    print(response)
    print("=" * 60)
    
    # Save results
    output_file = Path("ai_context/session/local_analysis.txt")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    output_content = f"""Local AI Analysis
================
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Query: {query}
Model: {args.model}

{response}

---
Generated by: python scripts/ai_workflow.py local-analyze --topic "{query}"
"""
    
    output_file.write_text(output_content, encoding='utf-8')
    print(f"\n[SAVED] Analysis saved to: {output_file}")
    
    return 0


def test_ollama_command(args):
    """Test Ollama connection and models."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from tools.ollama_client import get_ollama_client
    except ImportError:
        print("[ERROR] ollama_client.py not found")
        print("Create tools/ollama_client.py first")
        return 1
    
    print("[TEST] Testing Ollama integration...")
    print("-" * 40)
    
    client = get_ollama_client(args.model)
    
    # Test connection
    if client.is_available():
        print("✅ Ollama is running")
    else:
        print("❌ Ollama not running")
        print("Run 'ollama serve' in another terminal")
        return 1
    
    # List available models
    models = client.list_models()
    if models:
        print(f"✅ Available models: {models}")
    else:
        print("⚠️  No models found. Run: ollama pull llama3.2:3b")
    
    # Quick test generation
    print("\n[TEST] Quick generation test...")
    test_response = client.quick_chat("Say 'Test successful' if working.")
    
    if "test" in test_response.lower() or "success" in test_response.lower():
        print(f"✅ Generation works: {test_response[:50]}...")
    else:
        print(f"⚠️  Generation test: {test_response[:50]}...")
    
    print("\n" + "=" * 40)
    print("OLLAMA TEST COMPLETE")
    print("=" * 40)
    print("Next: python scripts/ai_workflow.py local-analyze --topic 'test'")
    
    return 0

def send_to_deepseek():
    """Send existing context to DeepSeek"""
    context_file = Path("ai_context/session/context_for_ai.txt")
    if not context_file.exists():
        print("[ERROR] No context file found. Run 'start' action first.")
        return
    
    with open(context_file, 'r', encoding='utf-8') as f:
        context = f.read()
    
    session_path = Path("ai_context/session/current_session.json")
    if session_path.exists():
        with open(session_path, 'r') as f:
            session = json.load(f)
        topic = session.get('topic', 'Unknown')
    else:
        topic = "Current context"
    
    send_to_deepseek_bridge(context, topic)

# def send_to_deepseek_bridge(context: str, topic: str):
#     """Send context to DeepSeek via bridge"""
#     print("\n[SEND] Sending to DeepSeek...")
    
#     try:
#         # Add tools directory to path
#         sys.path.insert(0, 'tools')
#         from bridge.deepseek_bridge_react import DeepSeekBridgeReact as DeepSeekBridge
        
#         bridge = DeepSeekBridge(verbose=True)
        
#         if bridge.connect():
#             # Create the question
#             question = f"""Topic: {topic}

# Please analyze this project context and provide:
# 1. What is the highest priority technical debt item?
# 2. What specific code changes should we make next?
# 3. Any architectural issues to address?

# Be specific and reference actual files/code where possible."""
            
#             full_message = f"{context}\n\n{question}"
            
#             print(f"[SEND] Sending {len(full_message)} chars to DeepSeek...")
#             response = bridge.ask(full_message)
#             bridge.close()
            
#             if response:
#                 print(f"\n[RESPONSE] Received: {len(response)} chars")
                
#                 # Save response
#                 response_file = Path("ai_context/session/deepseek_response.txt")
#                 with open(response_file, 'w', encoding='utf-8') as f:
#                     f.write(response)
                
#                 print(f"[SAVED] Response saved to: {response_file.absolute()}")
                
#                 # Show preview
#                 print("\n" + "="*80)
#                 print("RESPONSE PREVIEW")
#                 print("="*80)
#                 print(response[:1000] + ("..." if len(response) > 1000 else ""))
#                 print("="*80)
                
#                 # Also append to session history
#                 session_path = Path("ai_context/session/current_session.json")
#                 if session_path.exists():
#                     with open(session_path, 'r') as f:
#                         session = json.load(f)
                    
#                     if 'history' not in session:
#                         session['history'] = []
                    
#                     session['history'].append({
#                         'timestamp': datetime.now().isoformat(),
#                         'action': 'ai_response_received',
#                         'response_length': len(response)
#                     })
                    
#                     with open(session_path, 'w') as f:
#                         json.dump(session, f, indent=2)
#             else:
#                 print("[ERROR] No response from DeepSeek")
#         else:
#             print("[ERROR] Failed to connect to DeepSeek bridge")
            
#     except ImportError as e:
#         print(f"[ERROR] Failed to import bridge: {e}")
#     except Exception as e:
#         print(f"[ERROR] Bridge error: {e}")
#         import traceback
#         traceback.print_exc()

def send_to_deepseek_bridge(context: str, topic: str):
    """Send context to DeepSeek via bridge - FIXED version"""
    print("\n[SEND] Sending to DeepSeek via bridge...")
    
    try:
        # Import bridge
        sys.path.insert(0, 'tools')
        from bridge.deepseek_bridge_react import DeepSeekBridgeReact as DeepSeekBridge
        
        bridge = DeepSeekBridge(verbose=True)
        
        if not bridge.connect():
            print("[ERROR] Failed to connect to DeepSeek bridge")
            return None
        
        # Create the full message with instructions (like the first version)
        question = f"""Topic: {topic}

Please analyze this project context and provide:
1. What is the highest priority technical debt item?
2. What specific code changes should we make next?
3. Any architectural issues to address?

Be specific and reference actual files/code where possible."""
        
        full_message = f"{context}\n\n{question}"
        
        print(f"[SEND] Sending {len(full_message)} chars to DeepSeek...")
        
        # Send via bridge
        response = bridge.ask(full_message, timeout=300)  # Longer timeout for file uploads
        
        if not response:
            print("[ERROR] No response from bridge.ask()")
            bridge.close()
            return None
        
        bridge.close()
        
        if response:
            print(f"\n[RESPONSE] Received: {len(response)} chars")
            
            # Check if response is just the instruction (error case)
            if len(response) < 100 and any(keyword in response.lower() for keyword in ["uploaded", "please read", "provide analysis"]):
                print("⚠️  WARNING: Response appears to be the upload instruction, not AI analysis")
                print("   This suggests the bridge didn't wait for the actual response")
                print("\n[DEBUG] Try increasing timeout or checking the bridge's response detection")
                
                # Save what we got anyway
                response_file = Path("ai_context/session/deepseek_response.txt")
                response_file.write_text(response, encoding='utf-8')
                print(f"[SAVED] Partial response saved to: {response_file}")
                
                return None
            else:
                # Save the actual response
                response_file = Path("ai_context/session/deepseek_response.txt")
                response_file.write_text(response, encoding='utf-8')
                print(f"[SAVED] Response saved to: {response_file}")
                
                # Show preview
                print("\n" + "="*80)
                print("RESPONSE PREVIEW")
                print("="*80)
                preview = response[:1000] + ("..." if len(response) > 1000 else "")
                print(preview)
                print("="*80)
                
                return response
        else:
            print("[ERROR] Bridge returned empty response")
            return None
            
    except ImportError as e:
        print(f"[ERROR] Failed to import bridge: {e}")
        print("Make sure tools/bridge/deepseek_bridge_react.py exists")
        return None
    except Exception as e:
        print(f"[ERROR] Bridge error: {e}")
        import traceback
        traceback.print_exc()
        return None

def continue_session(topic: str, verbose: bool = False):
    """Continue an existing session"""
    print(f"[CONTINUE] Continuing session: {topic}")
    
    # Load existing session
    session_path = Path("ai_context/session/current_session.json")
    if not session_path.exists():
        print("[ERROR] No session to continue")
        return
    
    with open(session_path, 'r') as f:
        session_state = json.load(f)
    
    # Update topic if different
    if topic and topic != session_state.get('topic'):
        print(f"[UPDATE] Updating topic from '{session_state.get('topic')}' to '{topic}'")
        session_state['topic'] = topic
    
    # Add history entry
    if 'history' not in session_state:
        session_state['history'] = []
    
    session_state['history'].append({
        'timestamp': datetime.now().isoformat(),
        'action': 'session_continued'
    })
    
    # Save updated session
    with open(session_path, 'w') as f:
        json.dump(session_state, f, indent=2)
    
    print(f"[OK] Session continued: {topic}")
    print(f"    Last updated: {session_state.get('updated', 'Never')}")
    print(f"    History entries: {len(session_state.get('history', []))}")
    
    # Offer to send to DeepSeek
    context_file = Path("ai_context/session/context_for_ai.txt")
    if context_file.exists():
        print(f"\n[INFO] Context file exists: {context_file}")
        response = input("Send to DeepSeek? (y/n): ")
        if response.lower() == 'y':
            with open(context_file, 'r', encoding='utf-8') as f:
                context = f.read()
            send_to_deepseek_bridge(context, topic)
    else:
        print("[INFO] No context file found")

def archive_session(session_data):
    """Archive a session"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = Path(f"ai_context/session/session_archive_{timestamp}.json")
    
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(archive_path, 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print(f"[ARCHIVE] Previous session saved to: {archive_path}")
    return archive_path

def show_status():
    """Show current session status"""
    session_path = Path("ai_context/session/current_session.json")
    
    if session_path.exists():
        with open(session_path, 'r') as f:
            session = json.load(f)
        
        print("=== CURRENT SESSION ===")
        print(f"Topic: {session.get('topic', 'Unknown')}")
        print(f"Started: {session.get('started', 'Unknown')}")
        print(f"Updated: {session.get('updated', 'Never')}")
        
        if 'context_summary' in session:
            summary = session['context_summary']
            print(f"\nContext Summary:")
            print(f"  Token estimate: {summary.get('token_estimate', 0)}")
            print(f"  Files found: {summary.get('files_found', 0)}")
        
        if 'history' in session:
            print(f"\nHistory ({len(session['history'])} entries):")
            for entry in session['history'][-5:]:  # Last 5 entries
                action = entry.get('action', 'unknown')
                timestamp = entry.get('timestamp', '')
                print(f"  {timestamp}: {action}")
    else:
        print("No active session")
    
    # Check context file
    context_file = Path("ai_context/session/context_for_ai.txt")
    if context_file.exists():
        size = context_file.stat().st_size
        print(f"\nContext file: {context_file} ({size} bytes)")
    else:
        print("\nNo context file found")

if __name__ == "__main__":
    main()