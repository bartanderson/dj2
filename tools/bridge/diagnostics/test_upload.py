#!/usr/bin/env python3
"""
Minimal upload test: uploads a temp file and reports success/failure.
"""
import sys
import tempfile
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page, upload_file, is_file_attached, remove_existing_file

def create_temp_file(content="Test upload content."):
    """Create a temporary file and return its path, ensuring the file handle is closed."""
    fd, path = tempfile.mkstemp(suffix='.txt', text=True)
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path

def wait_for_upload_complete(page, timeout=15):
    """Wait for file container to show file size (indicating upload done)."""
    start = time.time()
    container = page.locator('div.d2d04dae').first
    if container.count() == 0:
        print("No file container found.")
        return False
    print("Container found, waiting for size...")
    while time.time() - start < timeout:
        # Check for size text like "5.2 KB" or "1 B"
        size_elements = container.locator('text=/\d+(\.\d+)?\s*(B|KB|MB)/').all()
        if len(size_elements) > 0:
            print(f"Size detected: {size_elements[0].inner_text()}")
            return True
        time.sleep(0.5)
    # Print container HTML for debugging
    print("Timeout waiting for size. Container HTML:")
    print(container.evaluate('el => el.outerHTML')[:500])
    return False

def safe_unlink(path, max_attempts=5):
    """Try to delete a file, retrying with delays."""
    for i in range(max_attempts):
        try:
            os.unlink(path)
            print(f"Deleted {path}")
            return True
        except PermissionError:
            print(f"Permission error deleting {path}, attempt {i+1}/{max_attempts}")
            time.sleep(1)
    print(f"Failed to delete {path} after {max_attempts} attempts.")
    return False

def main():
    print("=== MINIMAL UPLOAD TEST ===")
    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    # Optionally remove any existing file (comment out if you want to test with existing)
    if is_file_attached(page):
        print("Existing file found, removing...")
        remove_existing_file(page)
        time.sleep(1)

    file_path = create_temp_file()
    print(f"Temp file: {file_path}")

    print("Uploading...")
    if upload_file(page, file_path):
        print("✅ upload_file returned True")
        if wait_for_upload_complete(page):
            print("✅ File size detected – upload confirmed.")
        else:
            print("⚠️ File container appeared but size not detected within timeout.")
    else:
        print("❌ upload_file returned False")

    # Clean up temp file (retry if needed)
    safe_unlink(file_path)

    input("\nPress Enter to close browser...")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()