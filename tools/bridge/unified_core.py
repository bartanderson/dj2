# tools/bridge/unified_core.py - UPDATED
# coding=utf-8
"""
Unified bridge core - Internal implementation used by compatibility wrappers
"""

import tempfile
import os
import time
from datetime import datetime
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys  # <-- ADD THIS for sending keys
import re

PROFILE_PATH = r"C:\Users\bartl\AppData\Local\Google\Chrome\User Data\DeepSeekAI"

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
                # Try to quit the old driver if it still exists
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

        # Create new driver
        try:
            options = Options()
            options.add_argument("--log-level=3") #disable most logs but thats fine with me (gets rid of gcm deprecated errors)
            options.add_argument(f"--user-data-dir={self.profile_path}")
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://chat.deepseek.com")
            time.sleep(3)
            self._connected = True
            self._log("✅ Connected to DeepSeek")
            return True
        except Exception as e:
            self._log(f"❌ Connection failed: {e}")
            return False

    def upload_file(self, content: str, filename: str = "context.txt") -> bool:
        """
        Upload content as a file AND send instruction to analyze it
        Returns True if upload and instruction appear successful
        """
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                           suffix=filename, delete=False) as f:
                f.write(content)
                temp_path = f.name
            
            self._log(f"Uploading file: {len(content)} chars")
            
            # Find file input
            try:
                file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            except:
                file_input = self.driver.find_element(By.XPATH, '//input[@type="file"]')
            
            file_input.send_keys(temp_path)
            self._log("File selected for upload")
            
            # Wait for upload
            upload_success = self._wait_for_upload_complete(filename, timeout=60)
            
            if not upload_success:
                self._log("⚠️ Upload timeout or not detected")
                # Continue anyway - sometimes the detection fails but upload worked
            
            # Wait a moment for UI to settle
            time.sleep(5)
            
            # CRITICAL FIX: Send instruction to analyze the file
            instruction_sent = self._send_instruction("Thoroughly and deeply comprehend and respond.")
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            return upload_success or instruction_sent  # Return True if either succeeded
            
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