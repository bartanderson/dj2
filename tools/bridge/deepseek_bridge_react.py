#!/usr/bin/env python3
"""
DeepSeek Bridge - browser-use version (replaces Selenium)
Connects to existing Chrome on port 9222
"""

import asyncio
import tempfile
import os
from typing import Optional
import requests

from browser_use import Agent, ChatOpenAI, Browser

CDP_URL = "http://127.0.0.1:9222"


class DeepSeekBridgeReact:
    """Minimal bridge using browser-use instead of Selenium"""
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.browser: Optional[Browser] = None
        self._connected = False
        self._last_response: Optional[str] = None

    def get_current_page_url(self):
        """Get URL from CDP to avoid empty navigation."""
        try:
            r = requests.get('http://127.0.0.1:9222/json/list', timeout=3)
            pages = r.json()
            for p in pages:
                if p.get('type') == 'page' and not p.get('url', '').startswith('chrome://'):
                    return p['url']
        except Exception as e:
            self._log(f"Could not get current URL: {e}")
        return 'https://chat.deepseek.com'
        
    def _log(self, message: str):
        if self.verbose:
            print(f"[Bridge] {message}")
    
    def connect(self) -> bool:
        """Connect to existing Chrome via CDP"""
        if self._connected and self.browser:
            return True
            
        try:
            # Browser 0.12.0 accepts cdp_url directly in constructor
            self.browser = Browser(cdp_url=CDP_URL)
            self._connected = True
            self._log("Connected to Chrome")
            return True
        except Exception as e:
            self._log(f"Connection failed: {e}")
            return False

    def send_via_file_upload(self, text: str, filename: str = "context.txt") -> bool:
        """Upload using direct Playwright CDP connection."""
        import tempfile
        import os
        import time
        from playwright.sync_api import sync_playwright
        
        if getattr(self, '_upload_in_progress', False):
            self._log("Upload already in progress, skipping")
            return False
        
        self._upload_in_progress = True
        
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         suffix=filename, delete=False) as f:
            f.write(text)
            temp_path = f.name
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                
                # Find DeepSeek page
                target_page = None
                for context in browser.contexts:
                    for page in context.pages:
                        if 'chat.deepseek.com' in page.url:
                            target_page = page
                            break
                
                if not target_page:
                    self._log("No DeepSeek page found")
                    return False
                
                page = target_page
                page.bring_to_front()
                
                # DEBUG: Check current state
                self._log(f"Page URL: {page.url}")
                self._log(f"Page title: {page.title()}")
                
                # Upload file if not already there
                try:
                    if page.locator('text=analysis_context.txt').count() == 0:
                        file_input = page.locator('input[type="file"]').first
                        if file_input.count() > 0:
                            file_input.set_input_files(temp_path)
                            self._log("File uploaded")
                            time.sleep(2)  # Wait for file to register
                    else:
                        self._log("File already present")
                except Exception as e:
                    self._log(f"Upload issue: {e}")
                
                # DEBUG: Check if file is visible
                file_visible = page.locator('text=analysis_context.txt').count() > 0
                self._log(f"File visible in UI: {file_visible}")
                
                # TYPE AND SEND WITH DEBUG TIMING
                try:
                    # Find textarea
                    textarea = None
                    for selector in ['textarea', '[contenteditable="true"]', 'div[role="textbox"]']:
                        loc = page.locator(selector).first
                        if loc.count() > 0:
                            textarea = loc
                            self._log(f"Found textarea with: {selector}")
                            break
                    
                    if not textarea:
                        self._log("No textarea found!")
                        return False
                    
                    # Click to focus
                    self._log("Clicking textarea...")
                    textarea.click()
                    time.sleep(0.5)
                    
                    # Clear
                    self._log("Clearing textarea...")
                    textarea.fill("")
                    time.sleep(0.3)
                    
                    # Type message
                    message = "Please analyze this file thoroughly."
                    self._log(f"Typing message: '{message}'")
                    textarea.fill(message)
                    
                    # DEBUG: Verify text entered
                    entered = textarea.input_value()
                    self._log(f"Text in textarea after fill: '{entered}'")
                    self._log(f"Text length: {len(entered) if entered else 0}")
                    
                    time.sleep(0.5)  # Let it settle
                    
                    # Try to send
                    if entered and len(entered) > 5:
                        self._log("Text confirmed, attempting send...")
                        
                        # Method 1: Ctrl+Enter
                        self._log("Trying Ctrl+Enter...")
                        textarea.press('Control+Enter')
                        time.sleep(1)
                        
                        # Check if cleared
                        after_send = textarea.input_value()
                        self._log(f"Text after Ctrl+Enter: '{after_send}' (len={len(after_send) if after_send else 0})")
                        
                        if after_send and len(after_send) > 0:
                            # Method 2: Just Enter
                            self._log("Ctrl+Enter didn't work, trying Enter...")
                            textarea.press('Enter')
                            time.sleep(1)
                            
                            after_enter = textarea.input_value()
                            self._log(f"Text after Enter: '{after_enter}' (len={len(after_enter) if after_enter else 0})")
                            
                            if after_enter and len(after_enter) > 0:
                                # Method 3: Click send button
                                self._log("Enter didn't work, trying send button...")
                                send_btn = page.locator('button:has-text("Send"), button svg path[d*="arrow"], button.primary').first
                                if send_btn.count() > 0:
                                    self._log(f"Found send button, clicking...")
                                    send_btn.click()
                                    time.sleep(1)
                                else:
                                    self._log("No send button found!")
                        else:
                            self._log("Ctrl+Enter worked - text cleared")
                    else:
                        self._log(f"Text not entered properly, skipping send")
                        return False
                    
                except Exception as e:
                    self._log(f"Send failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
                
                # Wait for response
                self._log("Waiting for AI response...")
                time.sleep(10)
                
                # Poll for response
                last_response = ""
                for i in range(36):
                    try:
                        response = page.locator('.ds-markdown, .chat-message-assistant, [class*="assistant"]').last.inner_text()
                        if response and response != last_response:
                            self._log(f"Response updated: {len(response)} chars")
                            last_response = response
                        elif response == last_response and len(response) > 200:
                            self._log("Response complete")
                            break
                    except:
                        pass
                    time.sleep(5)
                
                self._last_response = last_response
                browser.close()
                return True
                
        except Exception as e:
            self._log(f"Failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            self._upload_in_progress = False
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def _wait_for_response(self, timeout: int = 180) -> Optional[str]:
        """Return last response (agent already waited)"""
        return self._last_response
    
    def receive(self) -> str:
        """Get latest response"""
        return self._last_response or ""
    
    def close(self):
        """Disconnect from Chrome (Chrome keeps running)"""
        if self.browser:
            try:
                asyncio.run(self.browser.close())
            except:
                pass
            self.browser = None
            self._connected = False
            self._log("Disconnected")