# tools\model_client.py
import atexit
from abc import ABC, abstractmethod

from ollama_client import get_ollama_client

class ModelClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def close(self):
        pass


class OllamaClient(ModelClient):
    def __init__(self, model_name: str, max_tokens: int = 16000, temperature: float = 0.2):
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = get_ollama_client()
        if not self.client.ensure_running():
            raise RuntimeError("Ollama is not available.")
    
    def generate(self, prompt: str, **kwargs) -> str:
        model = kwargs.get('model', self.model_name)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        temperature = kwargs.get('temperature', self.temperature)
        response = self.client.generate(prompt, model=model, max_tokens=max_tokens, temperature=temperature)
        return response.text.strip()
    
    def close(self):
        pass


class DeepSeekClient(ModelClient):
    _bridge = None

    def __init__(self, timeout: int = 3600):
        self.timeout = timeout
        self._ensure_bridge()
    
    @classmethod
    def _ensure_bridge(cls):
        if cls._bridge is None:
            from tools.bridge.bridge_controller import BridgeController
            cls._bridge = BridgeController()
            atexit.register(cls._close_bridge)
    
    @classmethod
    def _close_bridge(cls):
        if cls._bridge:
            try:
                cls._bridge.close()
            except Exception:
                pass
            cls._bridge = None
    
    def generate(self, prompt: str, **kwargs) -> str:
        self._ensure_bridge()
        response = self._bridge.ask_deepseek(prompt, use_tools=False)
        if response is None:
            raise RuntimeError("DeepSeek returned no response.")
        return response.strip()
    
    def close(self):
        pass