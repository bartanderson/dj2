#!/usr/bin/env python3
"""
Sends three messages, waiting for each response to finish.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page, send_message, wait_for_response

def main():
    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    messages = ["First", "Second", "Third"]
    for i, msg in enumerate(messages, 1):
        print(f"Sending {i}: {msg}")
        if send_message(page, msg):
            print("  ✅ Reported success")
            # Wait for response to complete before next send
            response = wait_for_response(page, timeout=60)
            if response:
                print(f"  Response received (length {len(response)})")
            else:
                print("  ⚠️ No response?")
        else:
            print("  ❌ Reported failure")
            break
        time.sleep(1)

    # After all sends, check the textarea
    textarea = page.locator('textarea[placeholder*="Message DeepSeek"]').first
    if textarea.count() > 0:
        content = textarea.input_value()
        print(f"\nFinal textarea content: '{content}'")
        if content.strip():
            print("⚠️ Textarea still contains text – last message may not have been sent.")
        else:
            print("✅ Textarea is empty – last message was sent.")
    else:
        print("❌ Textarea not found.")

    input("\nPress Enter to close browser...")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()