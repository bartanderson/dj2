# bidirectional_cli.py
"""
CLI for bidirectional AI collaboration
"""
import argparse
import sys
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    parser = argparse.ArgumentParser(description="Bidirectional AI Collaboration")
    parser.add_argument("--question", "-q", help="Question to process")
    parser.add_argument("--context", "-c", help="Context file or text")
    parser.add_argument("--local-only", action="store_true", help="Use only local AI")
    parser.add_argument("--deepseek-only", action="store_true", help="Use only DeepSeek")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser (test mode)")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode(args.no_browser)
    elif args.question:
        process_question(args.question, args.context, args.local_only, args.deepseek_only, args.no_browser)
    else:
        print("No question provided. Use --question or --interactive")
        sys.exit(1)

def process_question(question: str, context: str = None, 
                    local_only: bool = False, deepseek_only: bool = False,
                    no_browser: bool = False):
    """Process a single question"""
    
    if local_only:
        # Use only local AI
        from tools.local_ai_orchestrator import LocalAIOrchestrator
        orchestrator = LocalAIOrchestrator(deepseek_bridge=None)
        result = orchestrator.think_and_ask(question)
        print_result(result)
    elif deepseek_only:
        # Use only DeepSeek
        from tools.deepseek_bridge import DeepSeekBridge
        bridge = DeepSeekBridge()
        if not no_browser:
            bridge.connect()
            response = bridge.ask(question)
            bridge.close()
        else:
            response = "Browser disabled for testing"
        print(f"\n{'='*60}")
        print("DeepSeek Response:")
        print(f"{'='*60}")
        print(response if response else "No response")
    else:
        # Bidirectional
        print("🤖 Starting bidirectional AI collaboration...")
        
        from tools.deepseek_bridge import DeepSeekBridge
        from tools.local_ai_orchestrator import LocalAIOrchestrator
        
        bridge = None
        if not no_browser:
            bridge = DeepSeekBridge()
            print("🌐 Connecting to DeepSeek...")
            bridge.connect()
        else:
            print("🌐 Using simulated bridge (no browser)")
        
        orchestrator = LocalAIOrchestrator(deepseek_bridge=bridge)
        full_context = f"{context}\n\nQuestion: {question}" if context else question
        result = orchestrator.think_and_ask(full_context)
        
        if bridge:
            bridge.close()
        
        print_result(result)

def interactive_mode(no_browser: bool = False):
    """Interactive conversation mode"""
    print("🤖 Starting Bidirectional AI Collaboration")
    print("Mode: Local AI + DeepSeek Bridge")
    print("Type 'quit' to exit")
    print("-" * 60)
    
    from tools.deepseek_bridge import DeepSeekBridge
    from tools.local_ai_orchestrator import LocalAIOrchestrator
    
    bridge = None
    if not no_browser:
        bridge = DeepSeekBridge()
        print("🌐 Connecting to DeepSeek...")
        bridge.connect()
    else:
        print("🌐 Using simulated bridge (no browser)")
    
    orchestrator = LocalAIOrchestrator(deepseek_bridge=bridge)
    
    while True:
        print("\n" + "=" * 60)
        user_input = input("\n🎯 Your question/context: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        
        print("\n🤔 Processing...")
        result = orchestrator.think_and_ask(user_input)
        
        print("\n" + "=" * 60)
        print_result(result)
        
        # Show conversation summary
        print("\n📜 Conversation History:")
        print(orchestrator.get_conversation_summary())
    
    if bridge:
        bridge.close()
    print("\n✅ Session ended")

def print_result(result: dict):
    """Pretty print result"""
    if result.get("asked_deepseek", False):
        print("\n🔁 BIDIRECTIONAL PROCESSING:")
        print(f"\n🧠 Local Analysis: {result.get('local_analysis', 'N/A')[:200]}...")
        print(f"\n📤 To DeepSeek: {result.get('question', 'N/A')[:200]}...")
        print(f"\n📥 From DeepSeek: {result.get('deepseek_response', 'N/A')[:500]}...")
        print(f"\n🎯 Final Analysis: {result.get('final_analysis', 'N/A')[:300]}...")
    else:
        print("\n🎯 LOCAL PROCESSING ONLY:")
        print(f"\nAnalysis: {result.get('local_analysis', 'N/A')[:500]}...")

if __name__ == "__main__":
    main()