#!/usr/bin/env python3
"""
Meta‑agent: uses DeepSeek via the persistent session to improve tools.
"""

import socket
import json
import time
import re
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

def extract_actions(text):
    """Extract action blocks from AI response. Handles [ACTION]...[/ACTION] and also bare [ACTION] lines."""
    actions = []
    # First try the standard pattern with closing tag
    standard = re.findall(r'\[ACTION\](.*?)\[/ACTION\]', text, re.DOTALL)
    for match in standard:
        try:
            actions.append(json.loads(match.strip()))
        except json.JSONDecodeError:
            print(f"Warning: could not parse action JSON: {match[:100]}")
    if standard:
        return actions

    # If no standard blocks, look for lines starting with [ACTION] and then a JSON object
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        if '[ACTION]' in lines[i]:
            # Collect following lines until we find a line that looks like the end of a JSON object
            block = []
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('[') and not lines[j].strip().startswith(']'):
                block.append(lines[j])
                j += 1
            if block:
                json_str = '\n'.join(block).strip()
                try:
                    actions.append(json.loads(json_str))
                except json.JSONDecodeError:
                    # Try to find JSON by looking for braces
                    full_text = '\n'.join(lines[i:j])
                    brace_match = re.search(r'\{.*\}', full_text, re.DOTALL)
                    if brace_match:
                        try:
                            actions.append(json.loads(brace_match.group()))
                        except:
                            pass
            i = j
        else:
            i += 1
    return actions

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

Your goal: improve tools by ensuring they have proper tool.yaml, JSON input/output, etc. You may propose changes by outputting an [ACTION] block containing a JSON command. Always use the exact format:
[ACTION]
{ "operation": "...", ... }
[/ACTION]

After each action, you will receive the result. You may also ask the user for input if needed.

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

    # Main loop: extract and execute actions
    actions = extract_actions(ai_message)
    if not actions:
        print("No action blocks found. You can manually enter a command or let the AI try again.")
        # Optionally, you could send a follow‑up prompt asking for proper formatting
        # For now, exit.
        return

    for action in actions:
        print(f"Executing: {action}")
        try:
            result = send_command(action)
            print(f"Result: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"Error executing action: {e}")

if __name__ == "__main__":
    main()