#!/usr/bin/env python3
"""
Complete test suite for deepseek_lib.py.
Tests functions in isolation where possible, and runs upload/remove sequentially last.
"""

import tempfile
import os
import sys
from deepseek_lib import (
    connect_to_browser,
    find_deepseek_page,
    upload_file,
    remove_file,
    is_file_attached,
    send_message,
    wait_for_response,
    full_consult,
)

def test_connect():
    """Test connection to Chrome."""
    print("\n=== Testing connect_to_browser ===")
    try:
        browser, playwright = connect_to_browser()
        print("✅ Connection successful")
        browser.close()
        playwright.stop()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_find_page():
    """Test finding (or creating) a DeepSeek page."""
    print("\n=== Testing find_deepseek_page ===")
    try:
        browser, playwright = connect_to_browser()
        page = find_deepseek_page(browser, force_referral=True)
        assert page is not None, "No page returned"
        print(f"✅ Found page: {page.url}")
        browser.close()
        playwright.stop()
        return True
    except Exception as e:
        print(f"❌ find_deepseek_page failed: {e}")
        return False

def test_send_and_wait():
    """Test sending a message and waiting for response."""
    print("\n=== Testing send_message and wait_for_response ===")
    try:
        browser, playwright = connect_to_browser()
        page = find_deepseek_page(browser, force_referral=True)
        # Send a trivial message
        assert send_message(page, "Say 'ok'"), "send_message failed"
        response = wait_for_response(page, timeout=30)
        assert response and len(response) > 0, "No response or empty"
        print(f"✅ Response received: {response[:50]}...")
        browser.close()
        playwright.stop()
        return True
    except Exception as e:
        print(f"❌ send/wait failed: {e}")
        return False

def test_upload_remove():
    """Test upload and removal in sequence."""
    print("\n=== Testing upload_file and remove_file ===")
    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("test content")
        path = f.name

    try:
        # Upload
        assert upload_file(page, path), "upload_file failed"
        assert is_file_attached(page), "File not attached after upload"
        print("✅ Upload succeeded")

        # Remove
        assert remove_file(page), "remove_file failed"
        assert not is_file_attached(page), "File still attached after removal"
        print("✅ Removal succeeded – page clean")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        os.unlink(path)
        browser.close()
        playwright.stop()
    return True

def main():
    tests = [
        ("Connect", test_connect),
        ("Find page", test_find_page),
        ("Send & Wait", test_send_and_wait),
        ("Upload & Remove", test_upload_remove),
    ]
    for name, func in tests:
        if not func():
            print(f"\n❌ {name} failed. Stopping.")
            sys.exit(1)
    print("\n✅ All tests passed.")

if __name__ == "__main__":
    main()