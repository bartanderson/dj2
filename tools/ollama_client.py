#!/usr/bin/env python3
"""
Enhanced Ollama Client - Supports tool calling, auto-start, streaming, and fallback.

Features:
- Auto-start Ollama service if not running
- /api/generate for simple completions
- /api/chat for conversations with tool support
- Tool calling compatible with OpenAI format
- Streaming support
- DeepSeek fallback (optional)
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
    """Base Ollama error."""
    pass


class ServiceNotRunningError(OllamaError):
    """Ollama service not running and couldn't be started."""
    pass


class ModelNotFoundError(OllamaError):
    """Model not found locally."""
    pass


class GenerationError(OllamaError):
    """Error during generation."""
    pass


@dataclass
class GenerationResult:
    """Structured generation result with metadata."""
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
        if self.total_duration_ms > 0:
            return (self.prompt_eval_count + self.eval_count) / (self.total_duration_ms / 1000)
        return 0.0


@dataclass
class ChatMessage:
    """Represents a message in a conversation."""
    role: str  # 'system', 'user', 'assistant', 'tool'
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ChatResult:
    """Result of a chat completion."""
    message: ChatMessage
    model: str
    total_duration_ms: float
    load_duration_ms: float
    prompt_eval_count: int
    eval_count: int
    done: bool


class OllamaClient:
    """
    Production-ready Ollama client with tool support.
    
    Usage:
        client = OllamaClient()
        
        # Simple generation
        result = client.generate("Hello")
        
        # Conversation with tools
        tools = [...]  # OpenAI tool definitions
        messages = [{"role": "user", "content": "What's the weather?"}]
        response = client.chat(messages, tools=tools)
        if response.message.tool_calls:
            # handle tool calls
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
        if not hasattr(self, '_initialized'):
            self.base_url = host.rstrip('/')
            self.default_model = default_model
            self.auto_start = auto_start
            self.fallback_to_deepseek = fallback_to_deepseek
            self._session = requests.Session()
            self._deepseek_bridge = None
            self._initialized = True
    
    def _test_connection(self, timeout: int = 5) -> bool:
        try:
            response = self._session.get(f"{self.base_url}/api/tags", timeout=timeout)
            return response.status_code == 200
        except:
            return False
    
    def is_available(self) -> bool:
        return self._test_connection()
    
    def start_service(self, wait_time: int = 15) -> bool:
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
            return False
        except Exception as e:
            print(f"  [FAIL] Failed to start: {e}")
            return False
    
    def quick_start(self, model: Optional[str] = None, timeout: int = 60) -> bool:
        model_name = model or self.default_model
        if self._test_connection():
            return self.ensure_model_loaded(model_name)
        print(f"[=>] Quick-starting with 'ollama run {model_name}'...")
        try:
            result = subprocess.run(
                ['ollama', 'run', model_name],
                input='/bye\n',
                text=True,
                capture_output=True,
                timeout=timeout
            )
            time.sleep(2)
            return self._test_connection()
        except subprocess.TimeoutExpired:
            time.sleep(3)
            return self._test_connection()
        except FileNotFoundError:
            return False
        except Exception:
            return False
    
    def ensure_running(self, method: str = "auto", timeout: int = 30) -> bool:
        if self._test_connection():
            return True
        if method == "check-only":
            return False
        start_time = time.time()
        if method in ("auto", "quick"):
            if self.quick_start(timeout=min(60, timeout)):
                return True
        if time.time() - start_time >= timeout:
            return False
        if method in ("auto", "serve"):
            remaining = timeout - (time.time() - start_time)
            if remaining > 5:
                if self.start_service(wait_time=int(remaining)):
                    return True
        return False
    
    def ensure_model_loaded(self, model_name: Optional[str] = None, keep_alive: str = "5m") -> bool:
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
            response = self._session.post(f"{self.base_url}/api/generate", json=payload, timeout=30)
            return response.status_code == 200
        except:
            return False
    
    def _request_with_retry(self, endpoint: str, payload: Dict, max_retries: int = 2) -> Optional[Dict]:
        delay = 1.0
        for attempt in range(max_retries + 1):
            try:
                response = self._session.post(f"{self.base_url}{endpoint}", json=payload, timeout=60)
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
        if self.auto_start and not self.ensure_running():
            if self.fallback_to_deepseek:
                return self._fallback_generate(prompt, system, temperature, max_tokens)
            raise ServiceNotRunningError("Ollama not running.")
        model = model or self.default_model
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens, **options}
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
    
    def chat(self, messages: List[Dict[str, Any]], model: Optional[str] = None,
            tools: Optional[List[Dict]] = None, temperature: float = 0.7,
            max_tokens: int = 500, **options) -> ChatResult:
        """
        Send a chat completion request with optional tools.
        
        Args:
            messages: List of message dicts with 'role' and 'content' (and optional 'tool_calls' etc.)
            model: Model name
            tools: List of OpenAI-style tool definitions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **options: Additional Ollama options
        
        Returns:
            ChatResult containing the assistant's message (possibly with tool_calls)
        """
        if self.auto_start and not self.ensure_running():
            raise ServiceNotRunningError("Ollama not running.")
        model = model or self.default_model
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens, **options}
        }
        if tools:
            payload["tools"] = tools
        try:
            result = self._request_with_retry("/api/chat", payload)
            if result and "message" in result:
                msg_data = result["message"]
                # Convert to our ChatMessage format
                message = ChatMessage(
                    role=msg_data.get("role", "assistant"),
                    content=msg_data.get("content"),
                    tool_calls=msg_data.get("tool_calls"),
                    tool_call_id=msg_data.get("tool_call_id"),
                    name=msg_data.get("name")
                )
                return ChatResult(
                    message=message,
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
            raise GenerationError(f"Chat failed: {e}")
    
    def chat_stream(self, messages: List[Dict[str, Any]], model: Optional[str] = None,
                   tools: Optional[List[Dict]] = None, temperature: float = 0.7,
                   max_tokens: int = 500, **options) -> Generator[Dict, None, None]:
        """Streaming version of chat."""
        if not self.ensure_running():
            raise ServiceNotRunningError("Ollama not running")
        model = model or self.default_model
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens, **options}
        }
        if tools:
            payload["tools"] = tools
        try:
            response = self._session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=120
            )
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        yield data
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise GenerationError(f"Streaming failed: {e}")
    
    def _fallback_generate(self, prompt: str, system: Optional[str] = None,
                          temperature: float = 0.7, max_tokens: int = 500) -> GenerationResult:
        # (Fallback to DeepSeek – unchanged)
        print("[WARN] Ollama unavailable, falling back to DeepSeek...")
        if self._deepseek_bridge is None:
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from bridge.deepseek_bridge_react import DeepSeekBridgeReact
                self._deepseek_bridge = DeepSeekBridgeReact()
            except ImportError:
                raise ServiceNotRunningError("DeepSeek bridge not found")
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


def get_ollama_client(model: str = "llama3.2:3b", auto_start: bool = True) -> OllamaClient:
    return OllamaClient(default_model=model, auto_start=auto_start)