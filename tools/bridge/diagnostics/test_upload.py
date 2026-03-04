#!/usr/bin/env python3
"""
Test file upload to DeepSeek.
Usage: python tools/bridge/diagnostics/test_upload.py
"""
import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page, upload_file, remove_existing_file

def main():
    print("=== DEEPSEEK UPLOAD TEST ===")
    # Connect to browser
    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    # Ensure no file is attached
    remove_existing_file(page)

    # Create a temporary text file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file content for upload.")
        temp_path = f.name
    print(f"Created temp file: {temp_path}")

    # Upload the file
    success = upload_file(page, temp_path)
    if success:
        print("✅ Upload successful")
    else:
        print("❌ Upload failed")

    # Cleanup
    os.unlink(temp_path)
    input("Press Enter to exit...")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()