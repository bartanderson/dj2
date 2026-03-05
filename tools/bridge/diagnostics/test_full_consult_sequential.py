#!/usr/bin/env python3
"""
Test two full consultations sequentially with small file uploads.
Includes robust file cleanup and async‑avoidance advice.
"""
import sys
import tempfile
import time
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page, full_consult, is_file_attached

def create_temp_file(content):
    """Create a temporary file and return its path."""
    fd, path = tempfile.mkstemp(suffix='.txt', text=True)
    os.close(fd)  # Close the file descriptor immediately
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path

def safe_unlink(path):
    """Delete a file if it exists, ignoring errors."""
    try:
        if path and os.path.exists(path):
            os.unlink(path)
            print(f"Cleaned up: {path}")
    except Exception as e:
        print(f"Warning: could not delete {path}: {e}")

def main():
    print("=== SEQUENTIAL FULL CONSULT TEST ===")
    print("If you see Playwright async errors, please run this script in a fresh terminal.")
    browser = None
    playwright = None
    temp_files = []
    try:
        browser, playwright = connect_to_browser()
        page = find_deepseek_page(browser, force_referral=True)

        if is_file_attached(page):
            print("⚠️ Starting with a file attached – please clear manually and restart.")
            return

        messages = [
            ("First consultation", "Analyze this: first test file."),
            ("Second consultation", "Analyze this: second test file.")
        ]

        for i, (file_content, prompt) in enumerate(messages, 1):
            print(f"\n=== Consultation {i} ===")
            file_path = create_temp_file(file_content)
            temp_files.append(file_path)
            print(f"Uploading: {file_path}")
            try:
                response = full_consult(prompt=prompt, file_path=file_path, timeout=120)
                print(f"Response received (first 100 chars): {response[:100]}...")
            except Exception as e:
                print(f"❌ Consultation {i} failed: {e}")
                break
            finally:
                safe_unlink(file_path)
                if file_path in temp_files:
                    temp_files.remove(file_path)

            # Small pause between consultations
            time.sleep(2)

        # Final check: is a file attached?
        if is_file_attached(page):
            print("\n⚠️ A file is still attached after both consultations.")
        else:
            print("\n✅ No file attached – clean state.")

    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        # Clean up any remaining temp files
        for path in temp_files:
            safe_unlink(path)
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

if __name__ == "__main__":
    main()