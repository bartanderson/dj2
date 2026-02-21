#!/usr/bin/env python3
"""
Shared library for DeepSeek bridge operations.
Contains functions for file upload, prompt sending, and response retrieval.
"""

import tempfile
import time
import sys
import os
import re
from pathlib import Path
from selenium.webdriver.common.keys import Keys

# Import the core driver and helper functions (we'll restructure unified_core later)
# For now, we'll assume we have a driver object passed in.

def wait_for_upload_complete(driver, filename: str, timeout: int = 180) -> bool:
    """Wait for file upload to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            body = driver.find_element("tag name", "body")
            visible_text = body.text
            if filename not in visible_text:
                time.sleep(2)
                continue
            # Look for file type indicators
            matches = re.findall(r'\b(PY|TXT)\b\s*\d*\.?\d*\s*[KM]?B?', visible_text, re.IGNORECASE)
            if matches:
                time.sleep(2)  # stability
                return True
        except Exception:
            pass
        time.sleep(2)
    return False

def send_instruction(driver, instruction: str) -> bool:
    """Type instruction into textarea and press Enter."""
    try:
        textarea = driver.find_element("tag name", "textarea")
        textarea.clear()
        time.sleep(1)
        for char in instruction:
            textarea.send_keys(char)
            time.sleep(0.02)
        time.sleep(0.5)
        textarea.send_keys(Keys.RETURN)
        time.sleep(5)
        if textarea.get_attribute('value') == '':
            return True
        else:
            textarea.send_keys(Keys.RETURN)
            time.sleep(3)
            return True
    except Exception as e:
        print(f"Error sending instruction: {e}", file=sys.stderr)
        return False

def consult(driver, file_path: Path, prompt: str, timeout: int = 7200) -> str:
    """
    Perform a full consultation:
    - Upload the file
    - Send the prompt
    - Wait for response
    - Return response text
    """
    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                     suffix=file_path.name, delete=False) as tmp:
        tmp.write(content)
        temp_path = tmp.name

    try:
        # Upload file
        file_input = driver.find_element("css selector", 'input[type="file"]')
        file_input.send_keys(temp_path)

        # Wait for upload to appear
        wait_for_upload_complete(driver, file_path.name, timeout=360)

        time.sleep(2)

        # Send the prompt
        send_instruction(driver, prompt)

        # Wait for response (using the driver's method – we'll need to make this available)
        # For now, we'll use a simple polling loop (copied from BridgeCore.wait_for_response)
        response = wait_for_response(driver, timeout)
        print("DEBUG: raw response from wait_for_response:", repr(response), file=sys.stderr)
        return response
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass

def wait_for_response(driver, timeout: int = 3600) -> str:
    """Wait for and extract response text."""
    start_time = time.time()
    last_response = ""
    stable_count = 0

    time.sleep(5)  # initial wait

    while time.time() - start_time < timeout:
        response = _get_response_text(driver)
        if response and response != last_response:
            last_response = response
            stable_count = 0
        elif response:
            stable_count += 1
            if stable_count >= 3:
                return response
        time.sleep(3)

    return last_response if last_response else ""

def _get_response_text(driver) -> str:
    """Extract response text from page. Returns raw text without filtering."""
    try:
        selectors = [
            ".ds-markdown",
            '[class*="markdown"]',
            '[class*="message"][class*="assistant"]',
            '[class*="chat"][class*="item"]:last-child'
        ]
        for selector in selectors:
            try:
                elements = driver.find_elements("css selector", selector)
                for element in reversed(elements):
                    if element.is_displayed():
                        text = element.text.strip()
                        if text:
                            # Return raw text without filtering short lines
                            return text
            except:
                continue
        # Fallback – return full body text
        body_text = driver.find_element("tag name", "body").text
        return body_text
    except Exception as e:
        print(f"Error in _get_response_text: {e}", file=sys.stderr)
        return ""