#!/usr/bin/env python3
"""Test Ollama context window size."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.ollama_client import get_ollama_client

def test_context_size(size_in_tokens: int) -> bool:
    client = get_ollama_client(auto_start=True)
    if not client.ensure_running():
        print("❌ Ollama not available")
        return False
    
    filler = "word " * (size_in_tokens * 4 // 5)
    prompt = f"""Test context size: {size_in_tokens} tokens.

Context:
{filler}

Task: Respond with ONLY the number {size_in_tokens}."""
    
    try:
        print(f"Testing {size_in_tokens:5} tokens... ", end="", flush=True)
        result = client.generate(prompt, max_tokens=50)
        
        if str(size_in_tokens) in result.text:
            print(f"✓ PASS")
            return True
        else:
            print(f"✗ FAIL (got: {result.text[:50]})")
            return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

def find_max_context():
    print("="*70)
    print("TESTING OLLAMA CONTEXT WINDOW SIZE")
    print("="*70)
    print("\nAssumed limit: 8192 tokens")
    print("Safe limit: 6000 tokens (with margin)\n")
    
    sizes = [1024, 2048, 4096, 6000, 8192, 12288, 16384, 24765, 32768]
    last_success = 1024
    
    for size in sizes:
        if test_context_size(size):
            last_success = size
        else:
            print(f"\n✗ Failed at {size} tokens")
            break
    
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Maximum tested: ~{last_success} tokens")
    print(f"Recommended safe limit: ~{int(last_success * 0.75)} tokens (75% buffer)")

def quick_test():
    print("="*70)
    print("QUICK TEST: 8K Context Assumption")
    print("="*70)
    
    if test_context_size(6000):
        print("\n✓ 8K assumption VALID (6K safe limit works)")
        return True
    else:
        print("\n✗ 8K assumption INVALID")
        print("  Run full test: python tools/test_context_window.py --full")
        return False

if __name__ == "__main__":
    if "--full" in sys.argv:
        find_max_context()
    else:
        quick_test()