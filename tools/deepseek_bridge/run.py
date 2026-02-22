#!/usr/bin/env python3
"""
DeepSeek Bridge Tool - One-shot consultation.
Starts service if needed, executes, returns JSON.
"""

import sys
import json
import subprocess
import time
import os
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SERVICE_URL = "http://localhost:8000"

def ensure_service():
    try:
        if requests.get(f"{SERVICE_URL}/health", timeout=2).status_code == 200:
            return True
    except:
        pass
    
    service_script = Path(__file__).parent / "deepseek_service.py"
    cdp = os.getenv("DEEPSEEK_CDP_URL", "")
    
    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            [sys.executable, str(service_script), "--cdp-url", cdp],
            creationflags=DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.Popen(
            [sys.executable, str(service_script), "--cdp-url", cdp],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    
    for _ in range(30):
        try:
            if requests.get(f"{SERVICE_URL}/health", timeout=2).status_code == 200:
                return True
        except:
            time.sleep(1)
    
    raise RuntimeError("Service failed to start")

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "error": "No input"}))
        return 1

    raw = ' '.join(sys.argv[1:])
    if raw.startswith(("'", '"')) and raw.endswith(("'", '"')):
        raw = raw[1:-1]
    
    try:
        params = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"status": "error", "error": "Invalid JSON"}))
        return 1

    file_path = params.get('file')
    prompt = params.get('prompt', '')

    if not file_path:
        print(json.dumps({"status": "error", "error": "Missing 'file'"}))
        return 1

    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        print(json.dumps({"status": "error", "error": f"File not found: {path}"}))
        return 1

    try:
        ensure_service()
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"Service failed: {e}"}))
        return 1

    try:
        # Create session
        r = requests.post(f"{SERVICE_URL}/session/create", timeout=5)
        r.raise_for_status()
        sid = r.json()["session_id"]
        
        # Consult
        r = requests.post(
            f"{SERVICE_URL}/session/{sid}/consult",
            json={"prompt": prompt, "file_path": str(path)},
            timeout=7200
        )
        r.raise_for_status()
        result = r.json()
        
        output = {
            "status": "success" if result.get("success") else "error",
            "data": result.get("response", "")
        }
        if result.get("extracted_data"):
            output["structured"] = result["extracted_data"]
        if result.get("status") == "completed":
            output["done"] = True
            
        print(json.dumps(output))
        return 0
        
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        return 1

if __name__ == "__main__":
    sys.exit(main())