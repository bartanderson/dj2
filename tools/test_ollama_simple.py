# tools/test_ollama_simple.py
import requests

print("Testing direct Ollama call...")
try:
    # Simple direct call - no wrapper
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.2:3b",
            "prompt": "Say 'Hello World'",
            "stream": False
        },
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json().get("response", "")
        print(f"Response: {result}")
    else:
        print(f"Error: {response.text[:100]}")
        
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")