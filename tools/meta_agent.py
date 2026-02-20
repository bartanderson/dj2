#!/usr/bin/env python3
"""
Meta‑agent: uses DeepSeek via the persistent session to improve tools.
"""

import socket
import json
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path.cwd()
SESSION_DIR = PROJECT_ROOT / "ai_context" / "session"
PORT_FILE = SESSION_DIR / "port.txt"

def send_command(cmd):
    """Send a JSON command to the session server and return the response."""
    if not PORT_FILE.exists():
        raise Exception("Session server not running. Start with 'nativeclaw session start'.")
    with open(PORT_FILE, 'r') as f:
        port = int(f.read().strip())
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', port))
    s.sendall((json.dumps(cmd) + '\n').encode('utf-8'))
    data = s.recv(65536)
    s.close()
    return json.loads(data.decode('utf-8'))

def consult_deepseek(file_path, prompt):
    """Send a consult request to the session server."""
    cmd = {
        "operation": "consult",
        "file": file_path,
        "prompt": prompt
    }
    return send_command(cmd)

def main():
    print("Meta‑agent started. Connecting to session server...")
    # Optionally start session if not running (you could call `nativeclaw session start` here)

    # Initial system prompt
    system_prompt = """
You are an AI tasked with bringing all tools in this project into compliance with a standard contract. You have access to the following operations via the session server:

- run_nativeclaw: execute a nativeclaw subcommand (e.g., list-capabilities, semantic ...)
- get_file: retrieve the content of a file
- apply_plan: apply a change plan (safe, creates a session for review)
- consult: send a file and prompt to DeepSeek (your own interface)

Your goal: improve tools by ensuring they have proper tool.yaml, JSON input/output, etc. You may propose changes by outputting [ACTION] blocks containing JSON commands. After each action, you will receive the result. You may also ask the user for input if needed.

Proceed step by step. Start by listing all tools and their current status.
"""
    # Write system prompt to a temp file
    temp_file = PROJECT_ROOT / "ai_context" / "meta_prompt.txt"
    temp_file.write_text(system_prompt, encoding='utf-8')

    # Send initial consult
    response = consult_deepseek(str(temp_file), "Please begin.")
    if response.get("status") != "success":
        print(f"Initial consult failed: {response}")
        return
    ai_message = response["data"]
    print("AI:", ai_message)

    # Main loop: parse [ACTION] blocks and execute
    import re
    while True:
        # Extract action blocks
        actions = re.findall(r'\[ACTION\](.*?)\[/ACTION\]', ai_message, re.DOTALL)
        if not actions:
            print("No action blocks found. Waiting for user input or exit.")
            # Could break or ask user
            break

        for action_json in actions:
            try:
                action = json.loads(action_json)
                print(f"Executing: {action}")
                result = send_command(action)
                print(f"Result: {result}")
                # Feed result back to AI via another consult
                # We need to append result to conversation context
                # For simplicity, we'll just print and continue; a full agent would maintain context.
                # This is a minimal skeleton – you'd normally send the result back in a follow‑up prompt.
            except Exception as e:
                print(f"Error executing action: {e}")

        # In a real agent, you'd now send the results back to DeepSeek to continue.
        # For now, we'll break after first batch.
        break

if __name__ == "__main__":
    main()