#!/usr/bin/env python3
"""
Three cycles: upload, wait for correct container, send, verify. Minimal sleeps.
"""
import sys
import tempfile
import time
import os
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page, upload_file, send_message, wait_for_response, wait_for_upload_complete

def create_temp_file(content):
    fd, path = tempfile.mkstemp(suffix='.txt', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path

def main():
    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    messages = ["First", "Second", "Third"]
    for i, msg in enumerate(messages, 1):
        print(f"\n--- Cycle {i} ---")
        file_path = create_temp_file(f"Test file {i} content.")
        print(f"Uploading: {file_path}")

        if not upload_file(page, file_path):
            print("❌ Upload failed")
            break
        if not wait_for_upload_complete(page, os.path.basename(file_path)):
            print("⚠️ Upload not confirmed – continuing anyway")

        print(f"Sending: {msg}")
        if send_message(page, msg):
            print("  ✅ Sent")
        else:
            print("  ❌ Send failed")
            os.unlink(file_path)
            break

        response = wait_for_response(page, timeout=60)
        print(f"  Response received ({len(response)} chars)")

        # Clean up temp file only – file container will be replaced by next upload
        os.unlink(file_path)

    input("\nPress Enter to close browser...")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()