# tools/ollama_client.py
"""
Unified Ollama Client - Single source of truth for all Ollama interactions
Replaces duplicated code in watchdog, context_builder, ai_workflow, etc.
"""

import requests
import json
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

class OllamaClient:
    """Centralized Ollama API client with lifecycle management and retry logic."""
    
    _instance = None  # Singleton instance
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, host: str = "http://localhost:11434", default_model: str = "llama3.2:3b"):
        if not hasattr(self, '_initialized'):
            self.base_url = host.rstrip('/')
            self.default_model = default_model
            self._session = requests.Session()
            self._initialized = True
            
            # Test connection on init
            self._test_connection()
    
    def _test_connection(self):
        """Test connection to Ollama and list available models."""
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                print(f"✓ Ollama connected. Available models: {[m.get('name') for m in models]}")
                return True
            else:
                print(f"⚠️ Ollama returned HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to Ollama. Ensure 'ollama serve' is running.")
            return False
        except Exception as e:
            print(f"⚠️ Ollama connection test failed: {e}")
            return False
    
    def _request_with_retry(self, endpoint: str, payload: Dict, 
                           max_retries: int = 2, initial_delay: float = 2.0) -> Optional[Dict[str, Any]]:
        """Robust request handler with exponential backoff."""
        delay = initial_delay
        
        for attempt in range(max_retries + 1):
            try:
                response = self._session.post(
                    f"{self.base_url}{endpoint}", 
                    json=payload, 
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in [404, 500]:  # Model loading errors
                    if attempt == max_retries:
                        return {"error": f"API error {response.status_code} after {max_retries} retries"}
                    print(f"  Model loading... retrying in {delay}s (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(delay)
                    delay *= 1.5  # Exponential backoff
                    continue
                else:
                    return {"error": f"HTTP {response.status_code}: {response.text[:100]}"}
                    
            except requests.exceptions.ConnectionError:
                if attempt == max_retries:
                    return {"error": "Cannot connect to Ollama. Ensure 'ollama serve' is running."}
                time.sleep(delay)
                delay *= 1.5
            except Exception as e:
                return {"error": f"Request failed: {str(e)}"}
        
        return None
    
    def ensure_model_loaded(self, model_name: Optional[str] = None, 
                           keep_alive: str = "5m") -> bool:
        """Preload a model to prevent lazy-loading delays."""
        model = model_name or self.default_model
        
        # First check if model exists
        try:
            tags_response = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            if tags_response.status_code == 200:
                models = tags_response.json().get("models", [])
                model_exists = any(model in m.get('name', '') for m in models)
                if not model_exists:
                    print(f"⚠️ Model '{model}' not found. Run: ollama pull {model.split(':')[0]}")
                    return False
        except:
            pass
        
        # Warm-up request
        payload = {
            "model": model,
            "prompt": "Hello",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 10},
            "keep_alive": keep_alive
        }
        
        result = self._request_with_retry("/api/generate", payload)
        if result and "error" not in result:
            print(f"✓ Model '{model}' loaded and kept alive for {keep_alive}")
            return True
        else:
            error = result.get('error', 'Unknown error') if result else 'No response'
            print(f"✗ Failed to load model '{model}': {error}")
            return False
    
    def generate(self, prompt: str, model_name: Optional[str] = None, 
                system: Optional[str] = None, temperature: float = 0.1,
                max_tokens: int = 500) -> str:
        """Main method to generate a response."""
        model = model_name or self.default_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system:
            payload["system"] = system
        
        result = self._request_with_retry("/api/generate", payload)
        
        if result and "response" in result:
            return result["response"].strip()
        else:
            error_msg = result.get('error', 'Unknown error') if result else 'No response'
            return f"[Ollama Error] {error_msg}"
    
    def quick_chat(self, prompt: str, max_lines: int = 3) -> str:
        """Simple wrapper for concise tasks."""
        system_prompt = f"You are a code analysis assistant. Be extremely concise ({max_lines} lines max)."
        return self.generate(prompt, system=system_prompt, max_tokens=200)
    
    def list_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m.get('name', '') for m in models]
        except:
            pass
        return []
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        return self._test_connection()


# Convenience function for easy import
def get_ollama_client(model: str = "llama3.2:3b") -> OllamaClient:
    """Get or create the singleton Ollama client."""
    return OllamaClient(default_model=model)


# Test function
def test_ollama_client():
    """Quick test of the Ollama client."""
    print("Testing OllamaClient...")
    client = get_ollama_client()
    
    if client.is_available():
        print("✓ Connection successful")
        
        # Test quick generation
        response = client.quick_chat("Say 'Hello World' if working.")
        print(f"✓ Generation test: {response[:50]}...")
        
        # List models
        models = client.list_models()
        print(f"✓ Available models: {models}")
        
        return True
    else:
        print("✗ Connection failed")
        return False


if __name__ == "__main__":
    test_ollama_client()