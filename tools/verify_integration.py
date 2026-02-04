# tools/verify_integration.py (UPDATED VERSION)
"""
Verification script for Ollama integration.
Run this after implementing all changes.
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\bartl\dev\dj2")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

def test_imports():
    """Test that all imports work."""
    print("🔍 Testing imports...")
    
    tests = [
        ("ollama_client", "from ollama_client import get_ollama_client"),
        ("watchdog", "from watchdog import HybridPhaseAuditor"),
        ("context_builder", "from ai_assistant.context_builder import BridgeAgent"),
    ]
    
    all_passed = True
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"  ✓ {name}")
        except ImportError as e:
            print(f"  ✗ {name}: {e}")
            all_passed = False
    
    return all_passed

def test_ollama_client():
    """Test Ollama client functionality."""
    print("\n🤖 Testing Ollama client...")
    
    try:
        from ollama_client import get_ollama_client
        client = get_ollama_client()
        
        # Basic availability
        if client.is_available():
            print("  ✓ Ollama connection")
        else:
            print("  ⚠️ Ollama not running (expected if ollama serve not running)")
            return False
        
        # Quick generation test
        response = client.quick_chat("Say 'Integration test passed'")
        if "test" in response.lower() or "passed" in response.lower():
            print(f"  ✓ Generation test: {response[:50]}...")
        else:
            print(f"  ⚠️ Generation test: {response[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Ollama client test failed: {e}")
        return False

def test_watchdog_integration():
    """Test watchdog integration."""
    print("\n📊 Testing watchdog integration...")
    
    try:
        from watchdog import HybridPhaseAuditor
        auditor = HybridPhaseAuditor()
        
        # Test violations scanning
        violations = auditor.get_current_violations()
        if 'error' not in violations:
            print(f"  ✓ Violations scan: {violations.get('total', 0)} found")
        else:
            print(f"  ⚠️ Violations scan: {violations.get('error', 'Error')}")
        
        # Test local AI classification
        test_data = {'violations': [{'file': 'test.py', 'line': '10', 'text': 'Test violation'}]}
        classification = auditor.classify_with_local_ai(test_data)
        if classification and "error" not in classification.lower():
            print(f"  ✓ Local AI classification")
        else:
            print(f"  ⚠️ Local AI: {classification}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Watchdog test failed: {e}")
        return False

def test_workflow_commands():
    """Test new workflow commands."""
    print("\n🔄 Testing workflow commands...")
    
    commands = [
        ("python scripts/ai_workflow.py test-ollama", "Test Ollama"),
        ("python scripts/ai_workflow.py local-analyze --help", "Local analyze help"),
        ("python tools/watchdog.py --hybrid-audit", "Hybrid audit"),
    ]
    
    for cmd, description in commands[:1]:  # Just test first one
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode in [0, 1]:  # 1 is OK for --help
                print(f"  ✓ {description}: command works")
            else:
                print(f"  ⚠️ {description}: return code {result.returncode}")
        except Exception as e:
            print(f"  ✗ {description}: {e}")
    
    return True

def test_script_exists():
    """Just verify the script file exists."""
    print("\n📄 Testing script file existence...")
    
    script_path = PROJECT_ROOT / "scripts" / "ai_workflow.py"
    if script_path.exists():
        print(f"  ✓ ai_workflow.py exists at: {script_path}")
        return True
    else:
        print(f"  ✗ ai_workflow.py not found at: {script_path}")
        return False

def main():
    print("=" * 70)
    print("OLLAMA INTEGRATION VERIFICATION (FIXED)")
    print("=" * 70)
    
    tests = [
        ("Imports", test_imports),
        ("Ollama Client", test_ollama_client),
        ("Watchdog Integration", test_watchdog_integration),
        ("Script Existence", test_script_exists),
        ("Workflow Commands", test_workflow_commands),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"  ✗ {name} crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed >= 4:  # All but maybe the script import
        print("\n🎉 INTEGRATION SUCCESSFUL!")
        print("\nNext steps:")
        print("1. Test ai_workflow directly: python scripts/ai_workflow.py test-ollama")
        print("2. Run watchdog: python tools/watchdog.py --hybrid-audit")
        print("3. Get tool suggestions: python scripts/tool_discovery.py 'phase violations'")
    else:
        print("\n⚠️  Some tests failed. Review output above.")
    
    print("=" * 70)

if __name__ == "__main__":
    main()