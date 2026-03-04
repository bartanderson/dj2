#!/usr/bin/env python3
"""
Test the new remove button selector without modifying deepseek_lib.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.bridge.deepseek_lib import connect_to_browser, find_deepseek_page

def main():
    print("=== TEST NEW REMOVE SELECTOR ===")
    browser, playwright = connect_to_browser()
    page = find_deepseek_page(browser, force_referral=True)

    # Locate the container
    container = page.locator('div.d2d04dae').first
    if container.count() == 0:
        print("No file attached. Please upload a file and press Enter.")
        input("Press Enter when file is uploaded...")
        container = page.locator('div.d2d04dae').first
        if container.count() == 0:
            print("Still no container. Exiting.")
            browser.close()
            playwright.stop()
            return

    # Hover to reveal the remove button
    container.hover()
    time.sleep(0.5)

    # Try the new CSS selector
    remove_btn = page.locator('div.d2d04dae > div._35730b2').first
    if remove_btn.count() == 0:
        print("❌ Remove button not found with selector 'div.d2d04dae > div._35730b2'")
    else:
        print(f"✅ Remove button found. Visible: {remove_btn.is_visible()}, Enabled: {remove_btn.is_enabled()}")
        input("Press Enter to click it...")
        remove_btn.click()
        print("Clicked. Waiting for removal...")
        time.sleep(2)
        if page.locator('div.d2d04dae').count() == 0:
            print("✅ File removed successfully.")
        else:
            print("❌ File still present.")

    input("Press Enter to close browser...")
    browser.close()
    playwright.stop()

if __name__ == "__main__":
    main()