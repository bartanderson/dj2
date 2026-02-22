#!/usr/bin/env python3
"""
Test the bridge: open, send a few prompts, see if it stays alive.
"""

import time
from tools.bridge.bridge_controller import BridgeController

def test_bridge():
    print("Creating bridge...")
    bridge = BridgeController()

    # First prompt
    print("\n--- First ask ---")
    resp1 = bridge.ask_deepseek("Hello, respond with a short greeting.", use_tools=False)
    print(f"Response 1: {resp1}")

    time.sleep(5)  # Wait a bit

    # Second prompt
    print("\n--- Second ask ---")
    resp2 = bridge.ask_deepseek("What is 2+2? Answer with just the number.", use_tools=False)
    print(f"Response 2: {resp2}")

    # Third prompt
    print("\n--- Third ask ---")
    resp3 = bridge.ask_deepseek("Say 'done'.", use_tools=False)
    print(f"Response 3: {resp3}")

    print("\nAll done. Browser should remain open.")
    # Do not close – keep it open so you can inspect.
    # When you're finished, you can close manually or let it be.

if __name__ == "__main__":
    test_bridge()
    input("Press Enter to exit and close browser...")  # pause so you can see