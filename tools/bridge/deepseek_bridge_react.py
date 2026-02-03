# tools/bridge/deepseek_bridge_react.py
"""
DeepSeek Bridge - Simulates real typing with React event handling
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
from datetime import datetime

PROFILE_PATH = r"C:\Users\bartl\AppData\Local\Google\Chrome\User Data\DeepSeekAI"

class DeepSeekBridgeReact:
    def __init__(self, verbose=True):
        self.profile_path = PROFILE_PATH
        self.driver = None
        self._connected = False
        self.verbose = verbose
        
    def log(self, message: str):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] {message}")
        else:
            print(message)
        
    def connect(self):
        try:
            options = Options()
            options.add_argument(f"--user-data-dir={self.profile_path}")
            self.driver = webdriver.Chrome(options=options)
            self.driver.get("https://chat.deepseek.com")
            time.sleep(3)
            self._connected = True
            self.log("✅ Connected to DeepSeek")
            return True
        except Exception as e:
            self.log(f"❌ Connection failed: {e}")
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

    def _paste_text_via_javascript(self, text):
        """Set text using JavaScript to simulate paste - avoids React re-renders"""
        try:
            script = """
            // Find the main input textarea
            const textareas = document.querySelectorAll('textarea');
            let mainTextarea = null;
            
            // Look for the visible, enabled textarea that's likely the input
            for (const ta of textareas) {
                if (ta.offsetParent !== null && 
                    ta.style.display !== 'none' &&
                    !ta.disabled) {
                    mainTextarea = ta;
                    break;
                }
            }
            
            if (!mainTextarea && textareas.length > 0) {
                // Fallback to last textarea
                mainTextarea = textareas[textareas.length - 1];
            }
            
            if (mainTextarea) {
                // Set the value
                mainTextarea.value = arguments[0];
                
                // Trigger React events
                mainTextarea.dispatchEvent(new Event('input', { bubbles: true }));
                mainTextarea.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Trigger focus and blur to ensure React updates
                mainTextarea.focus();
                mainTextarea.blur();
                mainTextarea.focus();
                
                return true;
            }
            return false;
            """
            
            success = self.driver.execute_script(script, text)
            if success:
                self.log(f"✅ Set text via JavaScript paste: {len(text)} chars")
                # Wait a moment for React to update UI
                import time
                time.sleep(0.5)
                return True
            return False
            
        except Exception as e:
            self.log(f"❌ JavaScript paste failed: {e}")
            return False
    
    def _simulate_real_typing(self, text):
        """
        Simulate real human typing with proper React event handling
        This is the key to making DeepSeek's React state update
        """
        textarea = self._get_textarea()
        if not textarea:
            return False
        
        self.log(f"Simulating real typing of {len(text)} chars...")
        
        # Click to focus (important for React)
        textarea.click()
        time.sleep(0.5)
        
        # Clear any existing text
        textarea.clear()
        time.sleep(0.5)
        
        # Split text into realistic typing chunks
        # Humans type ~50-100 characters at a time, not all at once
        chunk_size = 40
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        self.log(f"Will type in {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            self.log(f"Chunk {i+1}/{len(chunks)}: {len(chunk)} chars")
            
            # For each character in the chunk, simulate keypress
            for char in chunk:
                try:
                    # Type the character
                    textarea.send_keys(char)
                    
                    # Add tiny random delay (like human typing)
                    time.sleep(0.01 + (0.005 if i % 10 == 0 else 0))
                    
                except Exception as e:
                    self.log(f"Error typing char: {e}")
                    # Try to re-find textarea if stale
                    textarea = self._get_textarea()
                    if not textarea:
                        return False
                    textarea.send_keys(char)
            
            # Pause between chunks (like human thinking/typing rhythm)
            time.sleep(0.1)
        
        self.log("✅ Typing complete")
        return True

    def _find_and_click_send(self):
        """Just press Enter - button state doesn't matter for sending"""
        self.log("Pressing Enter to send (bypassing button check)...")
        try:
            from selenium.webdriver.common.keys import Keys
            
            textarea = self._get_textarea()
            if textarea:
                textarea.send_keys(Keys.RETURN)
                self.log("✅ Enter key pressed")
                return True
        except Exception as e:
            self.log(f"❌ Error pressing Enter: {e}")
        return False

    def send(self, text):
        """Compatibility method for context_manager"""
        return self.send_message(text)

    def receive(self):
        """Get the latest response"""
        return self._get_response_text()

    def _find_send_button(self):
        """Find the send button"""
        send_selectors = [
            'button[aria-label*="send" i]',
            'button[title*="send" i]', 
            'button[type="submit"]',
            'div[role="button"][aria-label*="send" i]',
            'button:has(svg)',
            'button.ds-button'
        ]
        
        for selector in send_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
            except:
                continue
        return None

    def send_via_file_upload(self, text, filename="context.txt"):
        """Send long text via file upload"""
        import tempfile
        import os
        
        # Save text to temp file
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                         suffix=filename, delete=False) as f:
            f.write(text)
            temp_file_path = f.name
        
        try:
            self.log(f"Created temp file: {temp_file_path} ({len(text)} chars)")
            
            # Upload file
            file_input = self.driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
            file_input.send_keys(temp_file_path)
            self.log("✅ File uploaded")
            
            # Wait for file to appear
            time.sleep(3)
            
            # Send instruction in English
            textarea = self.driver.find_element(By.TAG_NAME, "textarea")
            textarea.click()
            time.sleep(0.5)
            
            instruction = "Please read the uploaded file and provide analysis in English."
            textarea.send_keys(instruction)
            
            # Find and click send button
            send_button = self._find_send_button()
            if send_button:
                send_button.click()
                self.log("✅ Send button clicked")
            else:
                # Fallback to Enter
                textarea.send_keys(Keys.RETURN)
                self.log("✅ Enter pressed")
            
            # Wait for send confirmation
            time.sleep(2)
            
            return True
            
        except Exception as e:
            self.log(f"❌ File upload failed: {e}")
            return False
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def send_message(self, text, max_retries=2):
        """Send message - use file upload for long text"""
        for attempt in range(max_retries):
            self.log(f"\n{'='*60}")
            self.log(f"Send attempt {attempt + 1}/{max_retries}")
            self.log(f"{'='*60}")
            
            # Use file upload for long text (> 200 chars)
            if len(text) > 200:
                self.log(f"Text is long ({len(text)} chars), using file upload...")
                if self.send_via_file_upload(text, "context.txt"):
                    self.log("✅ Message sent via file upload")
                    return True
                else:
                    self.log("❌ File upload failed")
                    continue
            else:
                # Use existing method for short text
                if not self._simulate_real_typing(text):
                    self.log("❌ Failed to type message")
                    continue
                
                if self._find_and_click_send():
                    self.log("✅ Message sent")
                    return True
            
            self.log(f"❌ Send attempt {attempt + 1} failed")
            
            if attempt < max_retries - 1:
                self.log("Clearing and retrying...")
                self._clear_textarea()
                time.sleep(1)
        
        return False
    
    def ask(self, message, timeout=180):
        """Main entry point"""
        if not self.send_message(message):
            self.log("❌ Failed to send message after all attempts")
            return None
        
        # Wait for response
        self.log(f"\n⏳ Waiting for response (max {timeout}s)")
        return self._wait_for_response(timeout)
    
    def _wait_for_response(self, timeout=120):
        """Wait for response - simplified version"""
        start_time = time.time()
        last_response = ""
        no_change_count = 0
        
        while time.time() - start_time < timeout:
            response = self._get_response_text()
            
            if response and response != last_response:
                # Response changed
                self.log(f"Response updated: {len(response)} chars")
                last_response = response
                no_change_count = 0
                time.sleep(2)
            elif response:
                # Response stable
                no_change_count += 1
                if no_change_count >= 2:  # Stable for 2 checks (4 seconds)
                    self.log(f"✅ Response complete: {len(response)} chars")
                    return response
                time.sleep(2)
            else:
                # No response yet
                if time.time() - start_time > 30:
                    self.log("Taking a while to respond...")
                time.sleep(2)
        
        self.log(f"⚠️ Timeout after {timeout}s")
        return last_response    
    def _get_response_text(self):
        """Get the latest response text with improved detection"""
        try:
            # Try multiple selectors for response
            selectors = [
                ".ds-markdown",
                '[class*="markdown"]',
                '[class*="message"][class*="assistant"]',
                '[class*="chat"][class*="item"]:last-child',
                '[data-testid="conversation-turn"]:last-child',
                'div[role="presentation"]:last-child'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in reversed(elements):
                        if element.is_displayed():
                            text = element.text.strip()
                            if text and len(text) > 20:  # Require more text
                                # Clean up the text (remove timestamps, etc.)
                                lines = text.split('\n')
                                # Keep only lines that look like content
                                content_lines = [line for line in lines 
                                               if len(line) > 10 
                                               and not line.strip().isdigit() 
                                               and ':' not in line[:5]]  # Skip timestamp-like lines
                                return '\n'.join(content_lines)
                except:
                    continue
            
            # Fallback: look for any substantial text that appeared recently
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            
            # Try to find response (usually the last substantial text block)
            for line in reversed(lines):
                if len(line) > 50 and not line.startswith('http'):
                    return line
            
            return ""
            
        except Exception as e:
            self.log(f"Error getting response: {e}")
            return ""
    
    def close(self):
        if self.driver:
            self.driver.quit()
            self._connected = False
            self.log("Closed browser")

def test_react_bridge():
    """Test the React-aware bridge"""
    # Simple test message
    test_message = "Hello! Please respond with 'React bridge test successful' and nothing else."
    
    print("Testing React-aware bridge...")
    print(f"Message: {len(test_message)} chars")
    
    bridge = DeepSeekBridgeReact(verbose=True)
    
    try:
        if not bridge.connect():
            return None
        
        print("\nStarting test...")
        
        # Run test
        response = bridge.ask(test_message, timeout=120)
        
        if response:
            print(f"\n✅ Response received: {len(response)} chars")
            print(f"\nResponse:")
            print(response[:500])
            
            # Check if test was successful
            if "React bridge test successful" in response:
                print("\n🎉 TEST CONFIRMED SUCCESSFUL!")
            else:
                print("\n⚠️ Response received but doesn't contain confirmation")
            
            # Save response
            with open("react_bridge_response.txt", "w", encoding="utf-8") as f:
                f.write(response)
            print(f"\nResponse saved to react_bridge_response.txt")
        else:
            print("\n❌ No response received")
        
        return response
        
    finally:
        bridge.close()

if __name__ == "__main__":
    response = test_react_bridge()
    if response and "React bridge test successful" in response:
        print("\n🎉 REACT BRIDGE TEST SUCCESSFUL!")
        exit(0)
    else:
        print("\n❌ REACT BRIDGE TEST FAILED")
        exit(1)