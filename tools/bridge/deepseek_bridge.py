#tools/bridge/deepseek_bridge.py
"""
DeepSeek Bridge - Trusts profile memory, minimal fuss
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

PROFILE_PATH = r"C:\Users\bartl\AppData\Local\Google\Chrome\User Data\DeepSeekAI"

class DeepSeekBridge:
    def __init__(self, deepthink: bool = True, search: bool = False):
        self.profile_path = PROFILE_PATH
        self.driver = None
        self.last_message_count = 0
        self._connected = False
        # Store desired state for reference (don't act on it)
        self.want_deepthink = deepthink
        self.want_search = search

    def connect(self):
        """Connect and trust profile has correct toggle state"""
        if self._connected:
            return True
            
        try:
            options = Options()
            options.add_argument(f"--user-data-dir={self.profile_path}")
            # Optional: run headless once working? Nah, keep visible for now.
            # options.add_argument("--headless=new")
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://chat.deepseek.com")
            time.sleep(3)
            
            self.last_message_count = self._count_messages()
            self._connected = True
            
            print("Connected to DeepSeek")
            print(f"[TRUST] Assuming toggles: DeepThink={'ON' if self.want_deepthink else 'OFF'}, "
                  f"Search={'ON' if self.want_search else 'OFF'} (profile memory)")
            
            # Future: add --verify-toggles flag to check actual state here
            # For now: trust but verify visually if needed
            
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def send(self, message):
        """Send message with retry on stale element"""
        for attempt in range(3):
            try:
                # Always find fresh (DOM may have changed)
                textarea = self.driver.find_element(By.TAG_NAME, "textarea")
                textarea.clear()
                
                # Send in chunks if huge (prevent truncation)
                chunk_size = 2000
                for i in range(0, len(message), chunk_size):
                    textarea.send_keys(message[i:i+chunk_size])
                    time.sleep(0.05)
                
                textarea.send_keys(Keys.RETURN)
                print(f"[SENT] {len(message)} chars")
                return True
                
            except Exception as e:
                if "stale" in str(e).lower() and attempt < 2:
                    print(f"[RETRY] Stale element, waiting...")
                    time.sleep(2)
                    continue
                print(f"[ERROR] Send failed: {e}")
                return False
        return False

    def receive(self):
        """Get latest response text"""
        try:
            time.sleep(2)  # Let it render
            
            # Try markdown first
            md = self.driver.find_elements(By.CLASS_NAME, "ds-markdown")
            if md:
                text = md[-1].text.strip()
                if text:
                    return text
            
            # Fallback to message container
            msgs = self.driver.find_elements(By.CLASS_NAME, "ds-message")
            if len(msgs) >= 2:
                text = msgs[-1].text.strip()
                if len(text) > 10:
                    return text
            
            # Last resort
            body = self.driver.find_element(By.TAG_NAME, "body").text
            lines = [l.strip() for l in body.split('\n') if l.strip()]
            return lines[-1] if lines else None
            
        except Exception as e:
            print(f"[ERROR] Receive: {e}")
            return None

    def _wait_for_response(self):
        """Wait for generation to complete (120s max)"""
        start = time.time()
        while time.time() - start < 120:
            time.sleep(1)
            html = self.driver.page_source.lower()
            if "typing" not in html and "thinking" not in html:
                curr = self._count_messages()
                if curr > self.last_message_count:
                    self.last_message_count = curr
                    return True
        return False  # Timeout, but may still have partial

    def _count_messages(self):
        try:
            return len(self.driver.find_elements(
                By.CSS_SELECTOR, "[class*='message'], [class*='chat-item']"
            ))
        except:
            return 0

    def close(self):
        if self.driver:
            self.driver.quit()
            self._connected = False
            print("Connection closed")

    # ========================================
    # FUTURE: Toggle detection (keep for later)
    # ========================================
    def _get_toggle_state(self, toggle_name: str) -> bool:
        """
        FUTURE USE: Check if toggle is ON/OFF
        Call this from connect() if you want to verify state
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