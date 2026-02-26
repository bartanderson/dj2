# tools/bridge/unified_core.py - UPDATED
# coding=utf-8
"""
Unified bridge core - Internal implementation used by compatibility wrappers
"""

import tempfile
import re
import os
import time
from datetime import datetime
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # <-- ADD THIS for sending keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BridgeCore:
    """
    Core bridge implementation with file upload capability.
    Used internally by compatibility wrappers.
    """
    
    def __init__(self, verbose=True):
        self.profile_path = PROFILE_PATH
        self.verbose = verbose
        self.driver = None
        self._connected = False
    
    def _log(self, message: str):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] {message}")

    def connect(self) -> bool:
        """Ensure we have a live connection. If already connected and alive, return True."""
        if self._connected and self.driver:
            try:
                # Quick health check – try to access current_url
                self.driver.current_url
                self._log("Already connected and alive")
                return True
            except Exception:
                self._log("Driver lost, will reconnect")
                self._connected = False
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

        # Connect to existing Chrome via CDP instead of launching new
        try:
            options = Options()
            options.add_argument("--log-level=3")
            # Connect to running Chrome on port 9222 instead of launching new
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            self.driver = webdriver.Chrome(options=options)
            
            # Navigate to DeepSeek if not already there
            if "chat.deepseek.com" not in self.driver.current_url:
                self.driver.get("https://chat.deepseek.com ")
                time.sleep(3)
            
            self._connected = True
            self._log("✅ Connected to DeepSeek via existing Chrome")
            return True
        except Exception as e:
            self._log(f"❌ Connection failed: {e}")
            return False

    def upload_file(self, content: str, filename: str = "context.txt") -> bool:
        """
        Upload content as a file AND send instruction to analyze it.
        Uses stable SVG path locators for paperclip and send buttons.
        """
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                             suffix=filename, delete=False) as f:
                f.write(content)
                temp_path = f.name

            self._log(f"Uploading file: {len(content)} chars")

            # ----- Click the paperclip button (its SVG path is stable) -----
            paperclip_path = (
                "M5.5498 9.75V5H6.9502V9.75C6.9502 10.3299 7.4201 10.7998 8 10.7998"
                "C8.5799 10.7998 9.0498 10.3299 9.0498 9.75V4.5C9.0498 2.9536 7.7964 1.7002"
                "6.25 1.7002C4.7036 1.7002 3.4502 2.9536 3.4502 4.5V9.75C3.4502 12.2629 5.4871"
                "14.2998 8 14.2998C10.5129 14.2998 12.5498 12.2629 12.5498 9.75V4H13.9502V9.75"
                "C13.9502 13.0361 11.2861 15.7002 8 15.7002C4.71391 15.7002 2.0498 13.0361"
                "2.0498 9.75V4.5C2.04981 2.1804 3.9304 0.299806 6.25 0.299805C8.5696 0.299805"
                "10.4502 2.1804 10.4502 4.5V9.75C10.4502 11.1031 9.3531 12.2002 8 12.2002"
                "C6.6469 12.2002 5.5498 11.1031 5.5498 9.75Z"
            )
            # XPath: find the SVG with that exact 'd' attribute, then go up to its clickable parent (a div with role="button")
            paperclip_xpath = f"//*[local-name()='svg' and @d='{paperclip_path}']/ancestor::div[@role='button']"

            paperclip = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, paperclip_xpath))
            )
            paperclip.click()
            self._log("Clicked paperclip button")

            # ----- Wait for the file input to be present (it may be added dynamically) -----
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
            file_input.send_keys(temp_path)
            self._log("File selected for upload")

            # ----- Click the send button (arrow) – it becomes enabled after file selection -----
            send_path = (
                "M8.3125 0.981587C8.66767 1.0545 8.97902 1.20558 9.2627 1.43374C9.48724 1.61438"
                "9.73029 1.85933 9.97949 2.10854L14.707 6.83608L13.293 8.25014L9 3.95717V15.0431H7"
                "V3.95717L2.70703 8.25014L1.29297 6.83608L6.02051 2.10854C6.26971 1.85933 6.51277"
                "1.61438 6.7373 1.43374C6.97662 1.24126 7.28445 1.04542 7.6875 0.981587C7.8973"
                "0.94841 8.1031 0.956564 8.3125 0.981587Z"
            )
            # XPath: find the enabled send button (without 'disabled' class) via its SVG path
            send_xpath = f"//*[local-name()='svg' and @d='{send_path}']/ancestor::div[@role='button' and not(contains(@class,'disabled'))]"

            send_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, send_xpath))
            )
            send_button.click()
            self._log("Clicked send button to upload file")

            # ----- Wait for the upload to complete (filename appears in UI) -----
            upload_success = self._wait_for_upload_complete(filename, timeout=60)

            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)

            # ----- Send the instruction (e.g., "Thoroughly and deeply comprehend and respond.") -----
            instruction_sent = self._send_instruction("Thoroughly and deeply comprehend and respond.")

            return upload_success or instruction_sent

        except Exception as e:
            self._log(f"File upload failed: {e}")
            return False

    def _send_instruction(self, instruction: str) -> bool:
        """Send text instruction, re‑finding textarea each time."""
        from selenium.common.exceptions import StaleElementReferenceException
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                textarea = self.driver.find_element(By.TAG_NAME, "textarea")
                textarea.clear()
                time.sleep(1)
                for char in instruction:
                    textarea.send_keys(char)
                    time.sleep(0.02)
                time.sleep(0.5)
                textarea.send_keys(Keys.RETURN)
                self._log(f"Instruction sent (attempt {attempt+1})")
                time.sleep(5)
                # Re-find to check if cleared
                textarea = self.driver.find_element(By.TAG_NAME, "textarea")
                if textarea.get_attribute('value') == '':
                    self._log("✅ Message sent successfully")
                    return True
                else:
                    self._log("⚠️ Textarea not cleared, pressing Enter again")
                    textarea.send_keys(Keys.RETURN)
                    time.sleep(3)
                    return True
            except StaleElementReferenceException:
                self._log(f"Stale element, retrying ({attempt+1}/{max_attempts})")
                time.sleep(2)
                continue
            except Exception as e:
                self._log(f"Error sending instruction: {e}")
                return False
        self._log("Failed to send instruction after retries")
        return False
    
    def _wait_for_upload_complete(self, filename: str, timeout: int = 60) -> bool:
        """Wait for file upload to complete"""
        self._log(f"Waiting for '{filename}' upload...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                visible_text = body.text
                
                if filename not in visible_text:
                    time.sleep(2)
                    continue
                
                # Look for file type indicators
                matches = re.findall(r'\b(PY|TXT)\b\s*\d*\.?\d*\s*[KM]?B?', visible_text, re.IGNORECASE)
                
                if matches:
                    self._log(f"✅ File uploaded: {matches[0]}")
                    time.sleep(2)  # Extra wait for stability
                    return True
                    
            except Exception as e:
                self._log(f"Upload check error: {e}")
            
            time.sleep(2)
        
        self._log(f"⚠️ Upload timeout after {timeout}s")
        return False
    
    def wait_for_response(self, timeout: int = 3600) -> Optional[str]: # an hour timeout should be fine
        """Wait for and extract response with better patience"""
        self._log(f"Waiting for response (timeout: {timeout}s)...")
        start_time = time.time()
        last_response = ""
        stable_count = 0
        
        # Wait a bit before starting checks (AI needs time to start)
        time.sleep(5)
        
        while time.time() - start_time < timeout:
            response = self._get_response_text()
            
            if response and response != last_response:
                self._log(f"Response updated: {len(response)} chars")
                last_response = response
                stable_count = 0
            elif response:
                stable_count += 1
                if stable_count >= 3:  # Response unchanged for 3 checks
                    self._log(f"✅ Response complete: {len(response)} chars")
                    return response
            else:
                # No response yet
                elapsed = time.time() - start_time
                if elapsed > 15 and elapsed % 15 < 1:  # Update every 15 seconds
                    self._log(f"Waiting... ({elapsed:.0f}s elapsed)")
            
            time.sleep(3)  # Check every 3 seconds
        
        self._log(f"⚠️ Response timeout after {timeout}s")
        return last_response if last_response else None
    
    def _get_response_text(self) -> str:
        """Extract response text from page"""
        try:
            # Try multiple selectors
            selectors = [
                ".ds-markdown",
                '[class*="markdown"]',
                '[class*="message"][class*="assistant"]',
                '[class*="chat"][class*="item"]:last-child'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in reversed(elements):
                        if element.is_displayed():
                            text = element.text.strip()
                            if text and len(text) > 20:
                                # Clean up text
                                lines = text.split('\n')
                                content_lines = [line for line in lines 
                                               if len(line) > 10 
                                               and not line.strip().isdigit()]
                                return '\n'.join(content_lines)
                except:
                    continue
            
            # Fallback
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            
            for line in reversed(lines):
                if len(line) > 50 and not line.startswith('http'):
                    return line
            
            return ""
            
        except Exception as e:
            self._log(f"Error getting response: {e}")
            return ""
    
    def close(self):
        """Close connection"""
        if self.driver:
            self.driver.quit()
            self._connected = False
            self._log("Connection closed")