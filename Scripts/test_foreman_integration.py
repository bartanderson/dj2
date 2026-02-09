# scripts/test_foreman_integration.py
"""
Test Foreman integration with AI commands
"""

import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from foreman import Foreman

def test_foreman_basic():
    """Test basic Foreman operations"""
    print("🧪 Testing Foreman Integration")
    print("=" * 60)
    
    foreman = Foreman(ai_preference="ollama")
    foreman.start()
    print(f"\nForeman config path: {foreman.config.path}")
    print(f"Foreman config tools keys: {list(foreman.config.tools.keys())}")
    print("ConfigLoader.tools keys:", foreman.config.tools.keys())
    print("Tools from config:", foreman.config.list_tools())
    
    if 'ai_commands' in foreman.config.tools:
        print(f"\nai_commands tools:")
        for tool_name, tool_info in foreman.config.tools['ai_commands'].items():
            print(f"  - {tool_name}: {tool_info.get('description', 'No desc')[:50]}")
    else:
        print("\n❌ ai_commands not in Foreman's loaded tools!")
        
        # Show what IS loaded
        print("\nWhat IS loaded:")
        for category, items in foreman.config.tools.items():
            if isinstance(items, dict):
                print(f"{category}: {len(items)} tools")
            else:
                print(f"{category}: {type(items)}")
            
    # Test 1: Simple tool execution
    print("\n1. Testing tool command...")
    result = foreman.run("tool ai_tools")
    print(f"Result: {result[:200]}...")
    
    # Test 2: Search
    print("\n2. Testing search...")
    result = foreman.run("tool ai_search query=phase")
    print(f"Result: {result[:200]}...")
    
    # Test 3: Ask AI
    print("\n3. Testing direct AI...")
    result = foreman.run("ask What's the most important phase violation to fix?")
    print(f"Result: {result[:200]}...")
    
    return True

def test_foreman_orchestration():
    """Test orchestration with a simple goal"""
    print("\n" + "=" * 60)
    print("Testing Foreman Orchestration")
    print("=" * 60)
    
    foreman = Foreman(ai_preference="ollama")
    foreman.start()
    
    # Small, achievable goal
    goal = "Check code quality and find TODOs"
    
    print(f"Goal: {goal}")
    print("\nStarting orchestration...")
    
    try:
        # Run in auto-mode (will ask for step confirmations)
        result = foreman.orchestrate(goal, verbose=False)
        print(f"\nOrchestration result: {result}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("🚀 FOREMAN INTEGRATION TEST")
    
    if test_foreman_basic():
        print("\n✅ Basic Foreman tests passed")
    else:
        print("\n❌ Basic Foreman tests failed")
    
    # Optional: test orchestration (interactive)
    print("\n" + "=" * 60)
    response = input("Test orchestration? (y/n): ")
    if response.lower() == 'y':
        test_foreman_orchestration()

if __name__ == "__main__":
    main()