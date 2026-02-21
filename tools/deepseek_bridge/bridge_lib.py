#!/usr/bin/env python3
"""
Shared library for DeepSeek bridge operations.
"""

import json
import requests
import tempfile
import os
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
SERVICE_URL = "http://localhost:8000"

class DeepSeekClient:
    def __init__(self, service_url: str = SERVICE_URL):
        self.service_url = service_url
        self.session_id: Optional[str] = None
    
    def _ensure_session(self):
        if not self.session_id:
            r = requests.post(f"{self.service_url}/session/create", timeout=10)
            r.raise_for_status()
            self.session_id = r.json()["session_id"]
    
    def consult(self, file_path: Optional[Path], prompt: str, timeout: int = 7200) -> str:
        self._ensure_session()
        
        if file_path and not file_path.is_absolute():
            file_path = PROJECT_ROOT / file_path
        
        r = requests.post(
            f"{self.service_url}/session/{self.session_id}/consult",
            json={
                "prompt": prompt,
                "file_path": str(file_path) if file_path else None
            },
            timeout=timeout
        )
        r.raise_for_status()
        result = r.json()
        
        return json.dumps({
            "status": "success" if result.get("success") else "error",
            "data": result.get("response"),
            "extracted": result.get("extracted_data"),
            "done": result.get("status") == "completed",
            "turn": result.get("turn")
        })

# Backward compatibility
def consult(driver, file_path: Path, prompt: str, timeout: int = 7200) -> str:
    client = DeepSeekClient()
    return client.consult(file_path, prompt, timeout)

def wait_for_upload_complete(driver, filename: str, timeout: int = 60) -> bool:
    return True

def send_instruction(driver, instruction: str) -> bool:
    raise NotImplementedError("Use consult()")

def wait_for_response(driver, timeout: int = 7200) -> str:
    raise NotImplementedError("Use consult()")

def _get_response_text(driver) -> str:
    raise NotImplementedError("Use consult()")