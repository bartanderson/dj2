#!/usr/bin/env python3
"""
Enhanced Ollama Client - Production-ready with auto-start, streaming, and fallback

Features:
- Auto-start Ollama service if not running (default behavior)
- Both /api/generate (simple) and /api/chat (conversation)
- Streaming support for real-time responses
- DeepSeek fallback when Ollama unavailable
"""

import requests
import json
import time
import subprocess
import sys
import os
from typing import Optional, Dict, Any, List, Generator, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


class OllamaError(Exception):
    """Base Ollama error with actionable messages"""
    pass


class ServiceNotRunningError(OllamaError):
    """Ollama service not running and couldn't be started"""
    pass


class ModelNotFoundError(OllamaError):
    """Model not found locally"""
    pass


class GenerationError(OllamaError):
    """Error during generation"""
    pass


@dataclass
class GenerationResult:
    """Structured generation result with metadata"""
    text: str
    model: str
    total_duration_ms: float
    load_duration_ms: float
    prompt_eval_count: int
    eval_count: int
    done: bool
    error: Optional[str] = None
    
    @property
    def tokens_per_second(self) -> float:
        """Calculate generation speed"""
        if self.total_duration_ms > 0:
            return (self.prompt_eval_count + self.eval_count) / (self.total_duration_ms / 1000)
        return 0.0


@dataclass
class Conversation:
    """Simple conversation manager"""
    messages: List[Dict[str, str]] = field(default_factory=list)
    max_history: int = 10
    
    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self._trim()
    
    def add_assistant(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self._trim()
    
    def add_system(self, content: str):
        # Insert system message at start, or replace existing
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0]["content"] = content
        else:
            self.messages.insert(0, {"role": "system", "content": content})
    
    def _trim(self):
        """Keep only last max_history messages (excluding system)"""
        system_msgs = [m for m in self.messages if m["role"] == "system"]
        other_msgs = [m for m in self.messages if m["role"] != "system"]
        
        if len(other_msgs) > self.max_history:
            other_msgs = other_msgs[-self.max_history:]
        
        self.messages = system_msgs + other_msgs
    
    def clear(self):
        """Clear conversation (keep system message if present)"""
        system_msgs = [m for m in self.messages if m["role"] == "system"]
        self.messages = system_msgs


class OllamaClient:
    """
    Production-ready Ollama client with auto-start and streaming.
    
    Usage:
        client = OllamaClient()  # Auto-start is ON by default
        result = client.generate("Hello, how are you?")
        print(result.text)
        
        # Conversation with history
        conv = client.create_conversation()
        response = client.chat(conv, "What is Python?")
        print(response.text)
        
        # Streaming for real-time output
        for chunk in client.generate_stream("Write a story..."):
            print(chunk, end='', flush=True)
    """
    
    _instance = None
    _service_process = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, host: str = "http://localhost:11434", 
                 default_model: str = "llama3.2:3b",
                 auto_start: bool = True,
                 fallback_to_deepseek: bool = False):
        """
        Initialize Ollama client.
        
        Args:
            host: Ollama API endpoint
            default_model: Default model to use
            auto_start: Try to start service if not running (default: True)
            fallback_to_deepseek: Use DeepSeek when Ollama fails
        """
        if not hasattr(self, '_initialized'):
            self.base_url = host.rstrip('/')
            self.default_model = default_model
            self.auto_start = auto_start
            self.fallback_to_deepseek = fallback_to_deepseek
            self._session = requests.Session()
            self._deepseek_bridge = None  # Lazy load
            self._initialized = True
    
    def _test_connection(self, timeout: int = 5) -> bool:
        """Test if Ollama is responding."""
        try:
            response = self._session.get(
                f"{self.base_url}/api/tags", 
                timeout=timeout
            )
            return response.status_code == 200
        except:
            return False
    
    def is_available(self) -> bool:
        """Check if Ollama service is available."""
        return self._test_connection()
    
    def start_service(self, wait_time: int = 15) -> bool:
        """
        Start Ollama service in background.
        
        Returns True if service is running (started or already running).
        """
        if self._test_connection():
            return True
        
        print("[=>] Starting Ollama service...")
        
        try:
            if sys.platform == 'win32':
                process = subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                process = subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            self._service_process = process
            print(f"  Process started (PID: {process.pid})")
            
            print(f"  Waiting up to {wait_time}s for service...")
            for i in range(wait_time):
                time.sleep(1)
                if self._test_connection():
                    print(f"  ✓ Ollama ready!")
                    return True
                if i % 3 == 0:
                    print(f"  ... {i}s")
            
            print("  [WARN] Service starting but not responding yet")
            return False
            
        except FileNotFoundError:
            print("   'ollama' command not found. Is Ollama installed?")
            print("     Download: https://ollama.ai ")
            return False
        except Exception as e:
            print(f"  [FAIL] Failed to start: {e}")
            return False
    
    def quick_start(self, model: Optional[str] = None, timeout: int = 60) -> bool:
        """
        Quick-start using 'ollama run' (4-minute window method).
        """
        model_name = model or self.default_model
        
        if self._test_connection():
            return self.ensure_model_loaded(model_name)
        
        print(f"[=>] Quick-starting with 'ollama run {model_name}'...")
        print(f"   (4-minute fast-response window)")
        
        try:
            # Start ollama run, but timeout quickly
            # We just need it to start, not complete
            result = subprocess.run(
                ['ollama', 'run', model_name],
                input='/bye\\n',  # Exit immediately
                text=True,
                capture_output=True,
                timeout=timeout
            )
            
            time.sleep(2)
            if self._test_connection():
                print("  [OK] Ollama is running")
                return True
            else:
                print("  [WARN] Process started but service not responding")
                return False
                
        except subprocess.TimeoutExpired:
            print("  [WARN] Timed out (service may still be starting)")
            time.sleep(3)
            return self._test_connection()
        except FileNotFoundError:
            print("  [FAIL] 'ollama' command not found")
            return False
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            return False
    
    def ensure_running(self, method: str = "auto", timeout: int = 30) -> bool:
        """
        Ensure Ollama is running, trying multiple methods.
        
        Args:
            method: "auto", "serve" (background), "quick" (4-min window), or "check-only"
            timeout: Maximum time to spend trying
        
        Returns:
            True if Ollama is available
        """
        # Already running?
        if self._test_connection():
            return True
        
        if method == "check-only":
            return False
        
        start_time = time.time()
        
        # Try quick start first (faster if it works)
        if method in ("auto", "quick"):
            if self.quick_start(timeout=min(60, timeout)):
                return True
        
        if time.time() - start_time >= timeout:
            return False
        
        # Try background service
        if method in ("auto", "serve"):
            remaining = timeout - (time.time() - start_time)
            if remaining > 5:
                if self.start_service(wait_time=int(remaining)):
                    return True
        
        return False
    
    def ensure_model_loaded(self, model_name: Optional[str] = None, 
                           keep_alive: str = "5m") -> bool:
        """Preload a model to prevent lazy-loading delays."""
        if not self._test_connection():
            return False
        
        model = model_name or self.default_model
        
        payload = {
            "model": model,
            "prompt": "Hi",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 10},
            "keep_alive": keep_alive
        }
        
        try:
            response = self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30
            )
            return response.status_code == 200
        except:
            return False
    
    def _request_with_retry(self, endpoint: str, payload: Dict, 
                           max_retries: int = 2) -> Optional[Dict]:
        """Make request with exponential backoff."""
        delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                response = self._session.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    error_data = response.json() if response.text else {}
                    error_msg = error_data.get('error', 'Unknown error')
                    if "model" in error_msg.lower():
                        raise ModelNotFoundError(f"Model not found: {error_msg}")
                    raise GenerationError(f"Not found: {error_msg}")
                else:
                    raise GenerationError(f"HTTP {response.status_code}: {response.text[:100]}")
                    
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == max_retries:
                    raise ServiceNotRunningError(f"Cannot connect to Ollama: {e}")
                time.sleep(delay)
                delay *= 2
            except (ModelNotFoundError, GenerationError):
                raise
            except Exception as e:
                if attempt == max_retries:
                    raise GenerationError(f"Request failed: {e}")
                time.sleep(delay)
                delay *= 2
        
        return None
    
    def generate(self, prompt: str, model: Optional[str] = None,
                system: Optional[str] = None, temperature: float = 0.7,
                max_tokens: int = 500, **options) -> GenerationResult:
        """
        Generate text using /api/generate (simple, single-turn).
        
        Auto-starts Ollama if configured. Falls back to DeepSeek if enabled.
        """
        # Ensure service is running
        if self.auto_start and not self.ensure_running():
            if self.fallback_to_deepseek:
                return self._fallback_generate(prompt, system, temperature, max_tokens)
            raise ServiceNotRunningError(
                "Ollama not running. Try:\n"
                "  1. Start manually: ollama serve\n"
                "  2. Or set auto_start=True\n"
                "  3. Or install Ollama: https://ollama.ai"
            )
        
        model = model or self.default_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **options
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            result = self._request_with_retry("/api/generate", payload)
            
            if result:
                return GenerationResult(
                    text=result.get("response", "").strip(),
                    model=result.get("model", model),
                    total_duration_ms=result.get("total_duration", 0) / 1_000_000,
                    load_duration_ms=result.get("load_duration", 0) / 1_000_000,
                    prompt_eval_count=result.get("prompt_eval_count", 0),
                    eval_count=result.get("eval_count", 0),
                    done=result.get("done", True)
                )
            else:
                raise GenerationError("Empty response from Ollama")
                
        except ServiceNotRunningError:
            if self.fallback_to_deepseek:
                return self._fallback_generate(prompt, system, temperature, max_tokens)
            raise
    
    def generate_stream(self, prompt: str, model: Optional[str] = None,
                       system: Optional[str] = None, temperature: float = 0.7,
                       max_tokens: int = 500, **options) -> Generator[str, None, None]:
        """
        Generate text with streaming (yields chunks as they arrive).
        
        Usage:
            for chunk in client.generate_stream("Write a story..."):
                print(chunk, end='', flush=True)
        """
        if not self.ensure_running():
            raise ServiceNotRunningError("Ollama not running")
        
        model = model or self.default_model
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **options
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=120
            )
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            raise GenerationError(f"Streaming failed: {e}")
    
    def create_conversation(self, system: Optional[str] = None) -> Conversation:
        """Create a new conversation with optional system prompt."""
        conv = Conversation()
        if system:
            conv.add_system(system)
        return conv
    
    def chat(self, conversation: Conversation, message: str,
            model: Optional[str] = None, **options) -> GenerationResult:
        """
        Send a message in a conversation (uses /api/chat with history).
        
        Args:
            conversation: Conversation object to maintain history
            message: User message
            model: Model to use (default if None)
            **options: Additional options (temperature, etc.)
        
        Returns:
            GenerationResult with response and metadata
        """
        if not self.ensure_running():
            raise ServiceNotRunningError("Ollama not running")
        
        model = model or self.default_model
        
        # Add user message
        conversation.add_user(message)
        
        payload = {
            "model": model,
            "messages": conversation.messages,
            "stream": False,
            "options": options
        }
        
        try:
            result = self._request_with_retry("/api/chat", payload)
            
            if result and "message" in result:
                content = result["message"].get("content", "").strip()
                # Add assistant response to history
                conversation.add_assistant(content)
                
                return GenerationResult(
                    text=content,
                    model=result.get("model", model),
                    total_duration_ms=result.get("total_duration", 0) / 1_000_000,
                    load_duration_ms=result.get("load_duration", 0) / 1_000_000,
                    prompt_eval_count=result.get("prompt_eval_count", 0),
                    eval_count=result.get("eval_count", 0),
                    done=result.get("done", True)
                )
            else:
                raise GenerationError("Empty chat response")
                
        except Exception as e:
            # Remove user message on failure to avoid corrupt history
            conversation.messages.pop() if conversation.messages else None
            raise
    
    def quick_chat(self, prompt: str, max_lines: int = 3, **kwargs) -> str:
        """Ultra-simple wrapper for concise tasks (backward compatible)."""
        system = f"You are a helpful assistant. Be extremely concise ({max_lines} lines max)."
        result = self.generate(prompt, system=system, max_tokens=200, **kwargs)
        return result.text
    
    def list_models(self) -> List[str]:
        """Get list of available models."""
        if not self.ensure_running():
            return []
        
        try:
            response = self._session.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m.get("name", "") for m in models]
        except:
            pass
        return []
    
    def _fallback_generate(self, prompt: str, system: Optional[str] = None,
                          temperature: float = 0.7, max_tokens: int = 500) -> GenerationResult:
        """Fallback to DeepSeek when Ollama fails."""
        print("[WARN]  Ollama unavailable, falling back to DeepSeek...")
        
        # Lazy load DeepSeek bridge
        if self._deepseek_bridge is None:
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from bridge.deepseek_bridge_react import DeepSeekBridgeReact
                self._deepseek_bridge = DeepSeekBridgeReact()
            except ImportError:
                raise ServiceNotRunningError(
                    "Ollama not available and DeepSeek bridge not found"
                )
        
        # Build full prompt
        full_prompt = prompt
        if system:
            full_prompt = f"System: {system}\n\nUser: {prompt}"
        
        try:
            if self._deepseek_bridge.connect():
                response = self._deepseek_bridge.ask(full_prompt, timeout=180)
                self._deepseek_bridge.close()
                
                return GenerationResult(
                    text=response or "",
                    model="deepseek-web",
                    total_duration_ms=0,
                    load_duration_ms=0,
                    prompt_eval_count=0,
                    eval_count=0,
                    done=True
                )
            else:
                raise ServiceNotRunningError("Cannot connect to DeepSeek")
        except Exception as e:
            raise ServiceNotRunningError(f"Fallback failed: {e}")


def get_ollama_client(model: str = "llama3.2:3b", 
                     auto_start: bool = True) -> OllamaClient:
    """Get or create the singleton Ollama client."""
    return OllamaClient(default_model=model, auto_start=auto_start)


def test_ollama_client():
    """Test the enhanced Ollama client."""
    print("="*70)
    print("TESTING ENHANCED OLLAMA CLIENT")
    print("="*70)
    
    client = OllamaClient(auto_start=True)
    
    print("\n[TEST 1] Checking availability...")
    if client.is_available():
        print("[OK] Ollama is running")
    else:
        print("[WARN] Ollama not running, trying to start...")
        if client.ensure_running():
            print("[OK] Started successfully")
        else:
            print("[FAIL] Could not start Ollama")
            return False
    
    print("\n[TEST 2] Simple generation...")
    try:
        result = client.generate("Say 'Hello World' if working.", max_tokens=20)
        print(f"[OK] Response: {result.text}")
        print(f"  Speed: {result.tokens_per_second:.1f} tokens/sec")
    except Exception as e:
        print(f"[FAIL] Generation failed: {e}")
        return False
    
    print("\n[TEST 3] Streaming generation...")
    try:
        print("  Response: ", end='', flush=True)
        for chunk in client.generate_stream("Count: 1, 2, 3", max_tokens=10):
            print(chunk, end='', flush=True)
        print(" [OK]")
    except Exception as e:
        print(f"\n✗ Streaming failed: {e}")
    
    print("\n[TEST 4] Conversation...")
    try:
        conv = client.create_conversation("You are a helpful coding assistant.")
        result = client.chat(conv, "What is Python?")
        print(f"[OK] Response: {result.text[:100]}...")
        
        result = client.chat(conv, "Give me a simple example")
        print(f"[OK] Follow-up: {result.text[:100]}...")
    except Exception as e:
        print(f"[FAIL] Conversation failed: {e}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    return True


if __name__ == "__main__":
    test_ollama_client()