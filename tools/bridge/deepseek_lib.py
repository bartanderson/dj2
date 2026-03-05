#!/usr/bin/env python3
"""
DeepSeek automation library – stable, container‑based selectors.
All functions use only reliable class names that were discovered iteratively.
"""

import logging
import time
import os
import tempfile
from playwright.sync_api import sync_playwright

logger = logging.getLogger("deepseek_lib")

CDP_URL = "http://127.0.0.1:9222"
DEEPSEEK_URL = "https://chat.deepseek.com"
GOOGLE_URL = "https://www.google.com"

MAX_RETRIES = 3
RETRY_DELAY = 2

# ----------------------------------------------------------------------
# Connection and page finding
# ----------------------------------------------------------------------
def connect_to_browser(cdp_url=CDP_URL):
    logger.info(f"Connecting to Chrome at {cdp_url}")
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        logger.info("Connected successfully")
        return browser, playwright
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        playwright.stop()
        raise

def find_deepseek_page(browser, force_referral=False):
    logger.info("Looking for existing DeepSeek page...")
    for context in browser.contexts:
        for page in context.pages:
            if DEEPSEEK_URL in page.url:
                logger.info(f"Found existing DeepSeek page: {page.url}")
                return page

    if force_referral:
        logger.info("No DeepSeek page found, creating via Google referral...")
        if browser.contexts:
            context = browser.contexts[0]
        else:
            context = browser.new_context()
        page = context.new_page()

        page.goto(GOOGLE_URL)
        page.wait_for_timeout(1000)
        page.fill('input[name="q"]', "deepseek chat")
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)
        link = page.locator('a:has-text("DeepSeek")').first
        if link.count() == 0:
            raise Exception("No DeepSeek link found in search results")
        link.click()
        page.wait_for_timeout(3000)
        logger.info(f"Now on: {page.url}")
        return page
    else:
        raise Exception("No DeepSeek page found and force_referral=False")

# ----------------------------------------------------------------------
# File attachment detection and removal (stable selectors)
# ----------------------------------------------------------------------
def is_file_attached(page):
    """
    Return True if the file attachment container (div.d2d04dae) is present.
    This container appears only when a file is uploaded.
    """
    return page.locator('div.d2d04dae').count() > 0

# this should not normally be called this should only be called if upload fails
def remove_existing_file(page, timeout=10):
    """
    Remove any attached file by:
      1. Checking for the container div.d2d04dae (indicates file attached).
      2. Hovering over it to reveal the remove button.
      3. Clicking the element with class '_35730b2' inside that container (the actual remove button).
      4. Waiting for the container to disappear.
    Returns True if removal succeeded (or no file), False otherwise.
    """
    container = page.locator('div.d2d04dae').first
    if container.count() == 0:
        logger.info("No file attached (container not found)")
        return True

    # Hover to reveal the remove button (if needed)
    container.hover()
    page.wait_for_timeout(500)

    # Find the remove button with class _35730b2 inside the container
    remove_btn = container.locator('div._35730b2').first
    if remove_btn.count() == 0:
        logger.error("Remove button (_35730b2) not found after hover")
        return False

    remove_btn.click()
    logger.info("Clicked remove button")

    # Wait for the container to disappear (file removed)
    start = time.time()
    while time.time() - start < timeout:
        if page.locator('div.d2d04dae').count() == 0:
            logger.info("File removed successfully")
            return True
        page.wait_for_timeout(200)
    logger.error("File still present after removal timeout")
    return False

# ----------------------------------------------------------------------
# Upload (direct file input, wait for container)
# ----------------------------------------------------------------------
def upload_file(page, file_path, timeout=30):
    """
    Upload a file by directly setting the file input.
    Assumes any existing file has been removed.
    Waits for the container div.d2d04dae to appear as confirmation.
    """
    logger.info(f"Uploading file: {file_path}")

    # Find the file input (directly, without clicking paperclip)
    file_input = page.locator('input[type="file"]').first
    if file_input.count() == 0:
        logger.error("File input not found")
        return False

    try:
        file_input.set_input_files(file_path)
        logger.info("File selected")
    except Exception as e:
        logger.error(f"Failed to set input files: {e}")
        return False

    # Wait for the container to appear (upload confirmed)
    start = time.time()
    while time.time() - start < timeout:
        if page.locator('div.d2d04dae').count() > 0:
            logger.info("Upload confirmed (container appeared)")
            return True
        page.wait_for_timeout(500)

    logger.error("Upload confirmation timeout")
    return False

# ----------------------------------------------------------------------
# Send message and wait for response
# ----------------------------------------------------------------------
def send_message(page, prompt, timeout=30):
    logger.info(f"Sending message: {prompt[:50]}...")
    try:
        textarea = page.locator('textarea[placeholder*="Message DeepSeek"]').first
        if textarea.count() == 0:
            textarea = page.locator('[contenteditable="true"]').first
        if textarea.count() == 0:
            logger.error("No input field found")
            return False

        textarea.wait_for(state="attached", timeout=5000)
        textarea.scroll_into_view_if_needed()
        textarea.click()
        page.wait_for_timeout(300)

        # Clear any existing text to ensure a clean slate
        textarea.press('Control+A')
        page.wait_for_timeout(200)
        textarea.press('Delete')
        textarea.fill("")
        page.wait_for_timeout(200)

        textarea.fill(prompt)
        logger.info("Prompt entered")
        page.wait_for_timeout(500)

        textarea.press('Enter')
        logger.debug("Enter pressed")

        start = time.time()
        while time.time() - start < timeout:
            current = textarea.input_value()
            if not current or len(current.strip()) == 0:
                logger.info(f"Textarea cleared after {time.time()-start:.1f}s")
                return True
            time.sleep(0.5)

        logger.warning(f"Textarea did not clear within {timeout}s")
        return False
    except Exception as e:
        logger.error(f"Send failed: {e}")
        return False
            
def wait_for_response(page, timeout=180):
    """
    Wait for the assistant's response to appear and stabilize.
    Returns the response text, or None if timeout.
    """
    logger.info(f"Waiting for response (timeout: {timeout}s)...")
    start = time.time()
    last_text = ""
    stable_count = 0
    while time.time() - start < timeout:
        # Try multiple selectors for assistant messages
        selectors = ['.ds-markdown', '[class*="markdown"]', '[class*="message"][class*="assistant"]']
        for selector in selectors:
            elements = page.locator(selector).all()
            if elements:
                latest = elements[-1].inner_text()
                if latest and latest != last_text:
                    last_text = latest
                    stable_count = 0
                    logger.debug(f"Response updated ({len(latest)} chars)")
                elif latest and latest == last_text:
                    stable_count += 1
                    if stable_count >= 3:
                        logger.info(f"Response complete ({len(latest)} chars)")
                        return latest
                break
        time.sleep(2)
    logger.warning("Response timeout")
    return last_text if last_text else None

def wait_for_upload_complete(page, expected_filename, timeout=15):
    """
    Wait for a file container that contains the expected filename and a file size.
    Returns True if found within timeout, False otherwise.
    """
    import re
    start = time.time()
    while time.time() - start < timeout:
        containers = page.locator('div.d2d04dae').all()
        for c in containers:
            text = c.text_content()
            if text and expected_filename in text and re.search(r'\d+(\.\d+)?\s*(B|KB|MB)', text):
                return True
        time.sleep(0.2)
    logger.warning(f"Upload completion not confirmed for '{expected_filename}' within {timeout}s")
    return False

# ----------------------------------------------------------------------
# High‑level consultation (orchestrates everything)
# ----------------------------------------------------------------------
def full_consult(prompt, file_path=None, file_content=None, filename=None, timeout=180):
    """
    Complete consultation: connect, find page, optionally upload, send, wait.
    Returns response text.
    """
    browser = None
    playwright = None
    temp_path = None
    try:
        browser, playwright = connect_to_browser()
        page = find_deepseek_page(browser, force_referral=True)

        upload_this = None
        if file_path:
            upload_this = file_path
            logger.info(f"Uploading existing file: {upload_this}")
        elif file_content:
            if filename:
                temp_dir = tempfile.gettempdir()
                if not filename.endswith('.txt'):
                    filename += '.txt'
                temp_path = os.path.join(temp_dir, filename)
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
            else:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(file_content)
                    temp_path = f.name
            upload_this = temp_path
            logger.info(f"Uploading temp file: {upload_this}")

        if upload_this:
            if not upload_file(page, upload_this):
                raise Exception("File upload failed")
            # Wait for upload to complete using the file's basename
            expected_name = os.path.basename(upload_this)
            if not wait_for_upload_complete(page, expected_name, timeout=15):
                logger.warning("Upload completion not confirmed, but continuing")
            # No extra sleep – next step will poll as needed

        if not send_message(page, prompt):
            raise Exception("Failed to send message")

        response = wait_for_response(page, timeout)
        if not response:
            raise Exception("No response received")

        return response
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
            logger.info(f"Temp file deleted: {temp_path}")
        if browser:
            browser.close()
        if playwright:
            playwright.stop()
            
# Alias for backward compatibility (at module level, no indent)
remove_file = remove_existing_file