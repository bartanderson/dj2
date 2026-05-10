#!/usr/bin/env python3
"""
Find the current remove button selector using the stable SVG path.
Run this after a file is uploaded (so the remove button appears on hover).
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page

# Stable SVG path for the remove (X) icon (verified)
REMOVE_PATH = "M10.6074 4.40278L8.00978 6.99973L10.6074 9.59739L9.59739 10.6074L6.99973 8.00978L4.40278 10.6074L3.39273 9.59739L5.98969 6.99973L3.39273 4.40278L4.40278 3.39273L6.99973 5.98969L9.59739 3.39273L10.6074 4.40278Z"

def main():
    print("\n=== FIND REMOVE BUTTON ===")
    print("Please ensure a file is already uploaded to DeepSeek.")
    input("Press Enter when ready...")

    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    # First, locate the file container (optional, but hover may be needed)
    container = page.locator('div.d2d04dae').first
    if container.count() == 0:
        print("⚠️ Container 'div.d2d04dae' not found. The UI may have changed.")
    else:
        container.hover()
        print("Hovered over container to reveal remove button.")
        time.sleep(0.5)

    # Construct XPath to find the SVG with the exact path, then get its clickable ancestor
    xpath = f"//*[local-name()='svg' and @d='{REMOVE_PATH}']/ancestor::*[self::button or self::div[@role='button']]"
    candidates = page.locator(f'xpath={xpath}').all()

    if not candidates:
        print("❌ No remove button found via XPath.")
        # Fallback: search all SVGs with that path and print their structure
        svgs = page.locator(f"//*[local-name()='svg' and contains(@d, '10.6074')]").all()
        print(f"Found {len(svgs)} SVGs containing the remove path. Their ancestors:")
        for svg in svgs:
            parent = svg.locator('xpath=..').first
            print(f"  Parent tag: {parent.evaluate('el => el.tagName')}, classes: {parent.get_attribute('class')}")
            grand = parent.locator('xpath=..').first
            if grand.count() > 0:
                print(f"    Grandparent: {grand.evaluate('el => el.tagName')}, classes: {grand.get_attribute('class')}")
    else:
        print(f"✅ Found {len(candidates)} candidate(s).")
        for i, btn in enumerate(candidates):
            tag = btn.evaluate('el => el.tagName')
            classes = btn.get_attribute('class') or ''
            print(f"\nCandidate {i+1}: <{tag} class=\"{classes}\">")
            print(f"  Visible: {btn.is_visible()}, Enabled: {btn.is_enabled()}")
            # Suggest a simple CSS selector
            if classes:
                first_class = classes.split()[0]
                print(f"  Suggested CSS: {tag.lower()}.{first_class}")
            else:
                print(f"  Suggested CSS: {tag.lower()}")
        # Optionally, try clicking the first candidate (ask user)
        if candidates:
            print("\nTo test removal, run in console:")
            js = f"document.evaluate(\"{xpath}\", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click();"
            print(js)

    input("\nPress Enter to close browser...")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()