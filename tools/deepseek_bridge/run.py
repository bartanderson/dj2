#!/usr/bin/env python3
"""
DeepSeek Bridge Tool – Sends context file and prompt to DeepSeek, returns response.
Uses the same browser automation as the existing bridge but with custom prompt.
"""

import sys
import json
import tempfile
import os
import time
import re
from pathlib import Path

# Add project root to path to import bridge core
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.bridge.unified_core import BridgeCore

def wait_for_upload_complete(driver, filename: str, timeout: int = 60) -> bool:
    """Wait for file upload to complete (copied from BridgeCore)."""
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
        textarea.send_keys("\n")  # using RETURN might need Keys.RETURN; but \n works?
        # Actually we need Keys.RETURN from selenium.webdriver.common.keys
        from selenium.webdriver.common.keys import Keys
        textarea.send_keys(Keys.RETURN)
        time.sleep(5)
        # Check if textarea cleared (message sent)
        if textarea.get_attribute('value') == '':
            return True
        else:
            textarea.send_keys(Keys.RETURN)
            time.sleep(3)
            return True
    except Exception as e:
        print(f"Error sending instruction: {e}", file=sys.stderr)
        return False

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "error": "No input"}))
        return

    raw_input = ' '.join(sys.argv[1:])
    # Remove matching surrounding quotes if present
    if raw_input.startswith(("'", '"')) and raw_input.endswith(("'", '"')):
        raw_input = raw_input[1:-1]
    input_str = raw_input
    
    try:
        params = json.loads(input_str)
    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "error": "Invalid JSON"}))
        return

    file_path = params.get('file')
    prompt = params.get('prompt', '')

    if not file_path:
        print(json.dumps({"status": "error", "error": "Missing 'file'"}))
        return

    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        print(json.dumps({"status": "error", "error": f"File not found: {path}"}))
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"Read error: {e}"}))
        return

    # Initialize bridge core (headless? no, visible for debugging)
    core = BridgeCore(verbose=False)
    if not core.connect():
        print(json.dumps({"status": "error", "error": "Connection failed"}))
        return

    driver = core.driver

    # Create temp file
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         suffix=path.name, delete=False) as tmp:
            tmp.write(content)
            temp_path = tmp.name
    except Exception as e:
        core.close()
        print(json.dumps({"status": "error", "error": f"Temp file error: {e}"}))
        return

    # Upload file
    try:
        file_input = driver.find_element("css selector", 'input[type="file"]')
    except:
        file_input = driver.find_element("xpath", '//input[@type="file"]')
    file_input.send_keys(temp_path)

    # Wait for upload
    upload_ok = wait_for_upload_complete(driver, path.name, timeout=60)
    if not upload_ok:
        # Continue anyway; sometimes detection fails but upload worked
        pass

    time.sleep(2)

    # Send the user's prompt (or a default if empty)
    if not prompt:
        prompt = "Please analyze the uploaded file and provide recommendations."
    instruction_ok = send_instruction(driver, prompt)

    # Clean up temp file
    try:
        os.unlink(temp_path)
    except:
        pass

    # Wait for response
    response = core.wait_for_response(timeout=180)

    core.close()

    if response:
        result = {"status": "success", "data": response}
    else:
        result = {"status": "error", "error": "No response"}

    print(json.dumps(result))

if __name__ == "__main__":
    main()