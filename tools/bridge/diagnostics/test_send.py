#!/usr/bin/env python3
"""
Test sending a simple message to DeepSeek.
Usage: python tools/bridge/diagnostics/test_send.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page, send_message, wait_for_response

def main():
    print("=== DEEPSEEK SEND MESSAGE TEST ===")
    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    prompt = "Say hello in one sentence."
    print(f"Sending: {prompt}")
    if send_message(page, prompt):
        print("✅ Message sent")
        response = wait_for_response(page, timeout=30)
        print(f"Response: {response}")
    else:
        print("❌ Failed to send message")

    input("Press Enter to exit...")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()