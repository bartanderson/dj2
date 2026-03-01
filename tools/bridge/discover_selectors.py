#!/usr/bin/env python3
"""
Discover both the file container and the remove button selectors.
Run this after manually uploading a file.
"""

import sys
import time
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from deepseek_lib import connect_to_browser, find_deepseek_page

def find_container(page):
    """Find the container that holds the file icon and file size text."""
    # Find the file icon (stable class)
    file_icon = page.locator('.ds-icon').first
    if file_icon.count() == 0:
        print("❌ No file icon (.ds-icon) found. Is a file uploaded?")
        return None

    # Find an element that contains size text like "PY 5.92KB" – this is likely the container.
    # We'll search for any element containing text matching a pattern like "PY \d+\.\d+KB"
    size_text = page.locator('text=/\w+ \d+\.\d+KB/').first
    if size_text.count() == 0:
        # fallback: look for any element containing "KB"
        size_text = page.locator('text=/KB/').first
    if size_text.count() == 0:
        print("⚠️ Could not find size text. Using heuristic based on file icon parent.")
        # fallback: go up from file icon until we find a div with multiple children
        current = file_icon
        for _ in range(5):
            parent = current.locator('xpath=..').first
            if parent.count() == 0:
                break
            child_count = parent.locator('*').count()
            if child_count >= 3:
                return parent
            current = parent
        return None

    # The container is likely the common ancestor of file_icon and size_text
    # We'll use XPath to find the nearest ancestor that contains both.
    # A simple way: get the parent of size_text and check if it contains file_icon
    candidate = size_text.locator('xpath=..').first
    for _ in range(5):
        if candidate.locator('.ds-icon').count() > 0:
            return candidate
        candidate = candidate.locator('xpath=..').first
        if candidate.count() == 0:
            break
    return None

def main():
    print("\n=== DISCOVER FILE CONTAINER AND REMOVE BUTTON ===")
    print("Please ensure a file is already uploaded to DeepSeek.")
    input("Press Enter when ready...")

    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    # Step 1: Find container
    container = find_container(page)
    if container is None:
        print("❌ Could not determine container automatically.")
        browser.close()
        playwright.stop()
        return

    # Output container info
    tag = container.evaluate('el => el.tagName.toLowerCase()')
    classes = container.get_attribute('class') or ''
    print(f"\n✅ Found container: <{tag} class=\"{classes}\">")
    # Suggest a simple selector using the first class (most stable)
    first_class = classes.split()[0] if classes else ''
    container_selector = f"{tag}.{first_class}" if first_class else tag
    print(f"Suggested container selector: {container_selector}")

    # Step 2: Discover remove button
    print("\nHovering over container to reveal remove button...")
    container.hover()
    time.sleep(0.5)

    children = container.locator('*').all()
    print(f"Found {len(children)} child elements. Clicking each until file disappears...\n")

    for i, child in enumerate(children):
        tag_c = child.evaluate('el => el.tagName.toLowerCase()')
        classes_c = child.get_attribute('class') or ''
        visible = child.is_visible()
        print(f"\n--- Candidate {i+1} ---")
        print(f"Tag: {tag_c}, Classes: {classes_c}, Visible: {visible}")

        if not visible:
            print("Skipping (not visible)")
            continue

        try:
            child.click()
            time.sleep(0.5)  # wait for UI update
        except Exception as e:
            print(f"Click failed: {e}")
            continue

        # Check if file is gone (container disappeared)
        if page.locator(container_selector).count() == 0:
            print(f"\n✅✅ SUCCESS! Candidate {i+1} removed the file.")
            print(f"Remove button selector: {tag_c}.{classes_c.split()[0] if classes_c else tag_c}")
            browser.close()
            playwright.stop()
            return

    print("\n❌ No element removed the file. You may need to inspect manually.")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()