#!/usr/bin/env python3
"""
Test full DeepSeek consultation with file upload.
Usage: python tools/bridge/diagnostics/test_full_consult.py
"""
import sys
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page, upload_file, send_message, wait_for_response, remove_existing_file

def main():
    print("=== DEEPSEEK FULL CONSULTATION TEST ===")
    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    # Ensure no file is attached
    remove_existing_file(page)

    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file. Please summarize its content.")
        temp_path = f.name
    print(f"Temp file: {temp_path}")

    # Upload
    if not upload_file(page, temp_path):
        print("❌ Upload failed")
        return
    print("✅ File uploaded")

    # Send prompt
    prompt = "Summarize the attached file."
    if not send_message(page, prompt):
        print("❌ Send failed")
        return
    print("✅ Message sent")

    # Wait for response
    response = wait_for_response(page, timeout=60)
    if response:
        print(f"Response: {response}")
    else:
        print("❌ No response")

    # Cleanup
    os.unlink(temp_path)
    input("Press Enter to close browser...")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()