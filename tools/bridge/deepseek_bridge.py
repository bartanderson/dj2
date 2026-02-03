# tools/bridge/deepseek_bridge.py
"""
DeepSeek Bridge - React-aware version that simulates real typing
REPLACES THE ORIGINAL BRIDGE
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime

PROFILE_PATH = r"C:\Users\bartl\AppData\Local\Google\Chrome\User Data\DeepSeekAI"

class DeepSeekBridge:
    def __init__(self, deepthink: bool = True, search: bool = False, verbose=True):
        self.profile_path = PROFILE_PATH
        self.driver = None
        self.last_message_count = 0
        self._connected = False
        # Store desired state for reference (don't act on it)
        self.want_deepthink = deepthink
        self.want_search = search
        self.verbose = verbose
        
    def _log(self, message: str):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] {message}")
        else:
            print(message)
        
    def connect(self):
        """Connect and trust profile has correct toggle state"""
        if self._connected:
            return True
            
        try:
            options = Options()
            options.add_argument(f"--user-data-dir={self.profile_path}")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://chat.deepseek.com")
            time.sleep(3)
            
            self.last_message_count = self._count_messages()
            self._connected = True
            
            self._log("Connected to DeepSeek")
            self._log(f"[TRUST] Assuming toggles: DeepThink={'ON' if self.want_deepthink else 'OFF'}, "
                  f"Search={'ON' if self.want_search else 'OFF'} (profile memory)")
            
            return True
            
        except Exception as e:
            self._log(f"Connection failed: {e}")
            return False

    def _get_textarea(self):
        """Get the main textarea"""
        try:
            textarea = self.driver.find_element(By.TAG_NAME, "textarea")
            if textarea.is_displayed():
                return textarea
            return None
        except:
            return None

    def send(self, message, max_retries=2):
        """Send message with retry logic - MAIN SEND METHOD"""
        for attempt in range(max_retries):
            self._log(f"\n{'='*60}")
            self._log(f"Send attempt {attempt + 1}/{max_retries}")
            self._log(f"{'='*60}")
            
            # Step 1: Type the message
            if not self._simulate_real_typing(message):
                self._log("❌ Failed to type message")
                continue
            
            # Step 2: Try to send
            time.sleep(0.5)  # Let UI update
            
            if self._find_and_click_send():
                # Check if message was actually sent
                time.sleep(2)  # Wait for UI to update
                
                # Look for indication that message was sent
                try:
                    textarea = self._get_textarea()
                    if textarea:
                        current_text = textarea.get_attribute("value") or ""
                        if len(current_text) < len(message) * 0.1:  # Most text cleared
                            self._log("✅ Message appears to have been sent")
                            return True
                except:
                    # If we can't check, assume success
                    self._log("✅ Send attempt completed")
                    return True
            
            self._log(f"❌ Send attempt {attempt + 1} failed")
            
            # Clear and retry
            if attempt < max_retries - 1:
                self._log("Clearing and retrying...")
                textarea = self._get_textarea()
                if textarea:
                    textarea.clear()
                time.sleep(1)
        
        return False

    def _simulate_real_typing(self, text):
        """Simulate real human typing with proper React event handling"""
        textarea = self._get_textarea()
        if not textarea:
            return False
        
        self._log(f"Simulating real typing of {len(text)} chars...")
        
        # Click to focus (important for React)
        textarea.click()
        time.sleep(0.5)
        
        # Clear any existing text
        textarea.clear()
        time.sleep(0.5)
        
        # Split text into realistic typing chunks
        chunk_size = 80
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        self._log(f"Will type in {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            self._log(f"Chunk {i+1}/{len(chunks)}: {len(chunk)} chars")
            
            # For each character in the chunk, simulate keypress
            for char in chunk:
                try:
                    # Type the character
                    textarea.send_keys(char)
                    
                    # Add tiny random delay (like human typing)
                    time.sleep(0.01 + (0.005 if i % 10 == 0 else 0))
                    
                except Exception as e:
                    self._log(f"Error typing char: {e}")
                    # Try to re-find textarea if stale
                    textarea = self._get_textarea()
                    if not textarea:
                        return False
                    textarea.send_keys(char)
            
            # Pause between chunks
            time.sleep(0.1)
        
        self._log("✅ Typing complete")
        return True

    def _find_and_click_send(self):
        """Find and click the send element"""
        self._log("Looking for send element...")
        
        # Method 1: Press Enter in textarea (most reliable)
        self._log("Trying Enter key press...")
        try:
            textarea = self._get_textarea()
            if textarea:
                # First ensure focus
                textarea.click()
                time.sleep(0.2)
                
                # Press Enter
                textarea.send_keys(Keys.RETURN)
                self._log("✅ Enter key pressed")
                return True
        except Exception as e:
            self._log(f"Enter press failed: {e}")
        
        # Method 2: Look for any clickable send element
        send_selectors = [
            '[data-testid="send-button"]',
            '[aria-label*="send" i]',
            '[title*="send" i]',
            'button:has(svg)',
            '.ds-button',
            'button[type="submit"]',
            'div[role="button"]'
        ]
        
        for selector in send_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed():
                        self._log(f"Found send element with selector: {selector}")
                        
                        # Check if it looks enabled
                        disabled = elem.get_attribute("disabled") or \
                                  elem.get_attribute("aria-disabled") or \
                                  "disabled" in elem.get_attribute("class")
                        
                        if not disabled:
                            self._log("Element appears enabled, clicking...")
                            elem.click()
                            time.sleep(1)
                            return True
                        else:
                            self._log("Element is disabled")
            except:
                continue
        
        return False

    def receive(self):
        """Get the latest response text"""
        return self._get_response_text()

    def _wait_for_response(self, timeout=180):
        """Wait for response with intelligent detection"""
        start_time = time.time()
        last_response = ""
        last_response_length = 0
        stable_count = 0
        
        while time.time() - start_time < timeout:
            try:
                # Get current response
                response = self._get_response_text()
                current_length = len(response) if response else 0
                
                # Check for typing indicators
                html = self.driver.page_source.lower()
                typing_indicators = ["typing", "thinking", "正在输入", "正在思考", "生成中"]
                is_typing = any(indicator in html for indicator in typing_indicators)
                
                if response and response != last_response:
                    # Response is changing
                    change = abs(current_length - last_response_length)
                    self._log(f"Response updated: {current_length} chars (+{change})")
                    last_response = response
                    last_response_length = current_length
                    stable_count = 0
                elif response and not is_typing:
                    # Response is stable and no typing
                    stable_count += 1
                    self._log(f"Response stable for {stable_count} checks")
                    
                    # If stable for 3 checks (6 seconds), consider complete
                    if stable_count >= 3:
                        self._log(f"✅ Response complete: {current_length} chars")
                        return True
                elif not response and not is_typing:
                    # No response yet and not typing
                    self._log("Waiting for response to start...")
                
                # Log typing status
                if is_typing:
                    self._log("DeepSeek is typing...")
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                self._log(f"Error during wait: {e}")
                time.sleep(2)
        
        self._log(f"⚠️ Timeout after {timeout}s")
        return False

    def _get_response_text(self):
        """Get the latest response text with improved detection"""
        try:
            # Try multiple selectors for response
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
                                return text
                except:
                    continue
            
            # Fallback
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            
            # Try to find response (usually the last substantial text block)
            for line in reversed(lines):
                if len(line) > 50 and not line.startswith('http'):
                    return line
            
            return ""
            
        except Exception as e:
            self._log(f"Error getting response: {e}")
            return ""

    def _count_messages(self):
        try:
            return len(self.driver.find_elements(
                By.CSS_SELECTOR, "[class*='message'], [class*='chat-item']"
            ))
        except:
            return 0

    def ask(self, message):
        """Send a message and get response - MAIN ENTRY POINT"""
        if not self.send(message):
            return None
        
        if not self._wait_for_response():
            self._log("[WARN] Response timeout, returning partial")
        
        return self.receive()

    def close(self):
        if self.driver:
            self.driver.quit()
            self._connected = False
            self._log("Connection closed")

    # ========================================
    # FUTURE: Toggle detection (keep for backward compatibility)
    # ========================================
    def _get_toggle_state(self, toggle_name: str) -> bool:
        """
        FUTURE USE: Check if toggle is ON/OFF
        """
        try:
            elems = self.driver.find_elements(By.XPATH, 
                f"//*[contains(text(), '{toggle_name}')]")
            for e in elems:
                if not e.is_displayed():
                    continue
                classes = e.get_attribute("class") or ""
                return (
                    "active" in classes.lower() or
                    e.get_attribute("aria-checked") == "true" or
                    "bg-blue" in classes
                )
            return False
        except:
            return False