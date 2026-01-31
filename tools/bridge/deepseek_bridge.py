#tools/bridge/deepseek_bridge.py
"""
DeepSeek Bridge - Simplified version
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Config - change this for different profiles
PROFILE_NAME = "DeepSeekAI"
PROFILE_PATH = rf"C:\Users\bartl\AppData\Local\Google\Chrome\User Data\{PROFILE_NAME}"

class DeepSeekBridge:
    def __init__(self, profile_name=None, deepthink: bool = True, search: bool = False):
        """
        Initialize DeepSeek bridge.
        
        Args:
            profile_name: Chrome profile name (default: "DeepSeekAI")
            deepthink: Click DeepThink toggle to enable (default: True)
            search: Click Search toggle to enable (default: False)
        """
        if profile_name:
            self.profile_path = rf"C:\Users\bartl\AppData\Local\Google\Chrome\User Data\{profile_name}"
        else:
            self.profile_path = PROFILE_PATH
        
        self.driver = None
        self.last_message_count = 0
        self._connected = False
        self.enable_deepthink = deepthink
        self.enable_search = search
        self._toggles_set = False  # Track if we've already clicked toggles

    def set_enhancements(self, deepthink: bool = None, search: bool = None):
        """
        Click toggles to set DeepThink and Search.
        Simple click - assumes you know current state.
        """
        try:
            if not self._connected:
                print("⚠️ Not connected - connect first before setting toggles")
                return False
            
            print("🎛️ Setting DeepSeek enhancements...")
            
            # Function to click toggle by text
            def click_toggle(toggle_name):
                try:
                    # Find elements containing the text
                    elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{toggle_name}')]")
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            print(f"  Clicking {toggle_name}...")
                            elem.click()
                            time.sleep(1)  # Wait for toggle animation
                            return True
                    print(f"  ⚠️ {toggle_name} toggle not found or not clickable")
                    return False
                except Exception as e:
                    print(f"  ❌ Error clicking {toggle_name}: {e}")
                    return False
            
            # Set DeepThink if specified
            if deepthink is not None:
                click_toggle("DeepThink")
            
            # Set Search if specified  
            if search is not None:
                click_toggle("Search")
            
            self._toggles_set = True
            print("✅ Toggles clicked (assume they are now ON)")
            return True
            
        except Exception as e:
            print(f"❌ Error setting enhancements: {e}")
            return False

    def connect(self):
        """Connect to DeepSeek (already logged in)"""
        if self._connected:
            return True
            
        try:
            options = Options()
            options.add_argument(f"--user-data-dir={self.profile_path}")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://chat.deepseek.com")
            time.sleep(3)
            
            # Count initial messages
            self.last_message_count = self._count_messages()
            
            self._connected = True
            print("✅ Connected to DeepSeek")
            
            # Set toggles if requested
            if self.enable_deepthink or self.enable_search:
                time.sleep(1)
                self.set_enhancements(
                    deepthink=self.enable_deepthink,
                    search=self.enable_search
                )
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def send(self, message):
        """Send message to DeepSeek"""
        try:
            # Find input
            textarea = self.driver.find_element(By.TAG_NAME, "textarea")
            textarea.clear()
            textarea.send_keys(message)
            textarea.send_keys(Keys.RETURN)
            
            print(f"📤 To DeepSeek: {message[:50]}...")
            
            # Wait for DeepSeek to start responding
            time.sleep(3)
            
            # Wait for response to complete
            self._wait_for_response()
            
            return True
            
        except Exception as e:
            print(f"❌ Send error: {e}")
            return False
    
    def receive(self):
        """Get DeepSeek's latest response - SIMPLE VERSION"""
        try:
            # Wait for response to render
            time.sleep(2)
            
            print("🔍 Getting response text...")
            
            # METHOD 1: Just get the fucking ds-markdown text
            try:
                markdown_elements = self.driver.find_elements(By.CLASS_NAME, "ds-markdown")
                if markdown_elements:
                    latest = markdown_elements[-1]
                    text = latest.text.strip()
                    if text:
                        print(f"📨 Response: {text[:150]}...")
                        return text
            except:
                pass
            
            # METHOD 2: Fallback to ds-message text
            try:
                message_elements = self.driver.find_elements(By.CLASS_NAME, "ds-message")
                if len(message_elements) >= 2:
                    # Last message should be AI, second to last is us
                    ai_message = message_elements[-1]
                    text = ai_message.text.strip()
                    if text and len(text) > 10:  # More than just UI noise
                        print(f"📨 Response (fallback): {text[:150]}...")
                        return text
            except:
                pass
            
            # METHOD 3: Last resort - get all text and return the last non-empty line
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                lines = [line.strip() for line in body_text.split('\n') if line.strip()]
                if lines:
                    print(f"📨 Response (last resort): {lines[-1][:150]}...")
                    return lines[-1]
            except:
                pass
            
            print("⚠️ No text found")
            return None
            
        except Exception as e:
            print(f"❌ Receive error: {e}")
            return None

    def _looks_like_response(self, text: str) -> bool:
        """Check if text looks like a meaningful response"""
        if not text:
            return False
        
        # Very short but could be valid (like "4", "Yes", "No")
        if len(text) <= 10:
            return text.isdigit() or text in ['Yes', 'No', 'OK', 'True', 'False']
        
        # Longer text should have some structure
        return len(text.split()) > 2 or '.' in text or '?' in text or '!' in text

    def ask(self, question):
        """Ask DeepSeek and get response - AUTO-CONNECTS IF NEEDED"""
        # Ensure we're connected
        if not self._connected:
            print("🔗 Auto-connecting to DeepSeek...")
            if not self.connect():
                return None
        
        # Adjust wait time based on whether DeepThink is enabled
        if self.enable_deepthink:
            print("🧠 DeepThink enabled - allowing more time for response...")
        
        # Send the question
        if self.send(question):
            # Wait for response with dynamic timing
            wait_time = 10 if self.enable_deepthink else 5
            print(f"⏳ Waiting {wait_time}s for response...")
            time.sleep(wait_time)
            return self.receive()
        return None
    
    def _count_messages(self):
        """Count visible messages"""
        try:
            messages = self.driver.find_elements(
                By.CSS_SELECTOR, 
                "[class*='message'], [class*='chat-item']"
            )
            return len(messages)
        except:
            return 0

    def _wait_for_response(self):
        """Wait for DeepSeek to finish responding"""
        print("⏳ Waiting for response...")
        
        # Wait for typing indicator to appear and disappear
        start_time = time.time()
        while time.time() - start_time < 30:  # Max 30 seconds
            time.sleep(1)
            
            # Check if DeepSeek is still typing
            page_html = self.driver.page_source.lower()
            if "typing" not in page_html and "thinking" not in page_html:
                # Also check if new message appeared
                current_count = self._count_messages()
                if current_count > self.last_message_count:
                    self.last_message_count = current_count
                    print("✅ Response received")
                    return True
        
        print("⚠️ Response timeout")
        return False

    def close(self):
        """Close the connection"""
        if self.driver:
            self.driver.quit()
            self._connected = False
            print("🔌 Connection closed")