#!/usr/bin/env python3
"""
Meta‑agent: uses DeepSeek via the persistent session to improve tools.
Now with iterative loop.
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
MAX_ITER = 10  # safety limit

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
    """Extract action blocks from AI response. Handles [ACTION]...[/ACTION]."""
    actions = []
    # Standard pattern
    standard = re.findall(r'\[ACTION\](.*?)\[/ACTION\]', text, re.DOTALL)
    for match in standard:
        try:
            actions.append(json.loads(match.strip()))
        except json.JSONDecodeError:
            print(f"Warning: could not parse action JSON: {match[:100]}")
    return actions

def main():
    print("Meta‑agent started. Connecting to session server...")
    iteration = 0
    conversation_history = []

    # Initial system prompt (we'll reuse this)
    system_prompt = """
You are an AI tasked with bringing all tools in this project into compliance with a standard contract. You have access to the following operations via the session server:

- run_nativeclaw: execute a nativeclaw subcommand (e.g., list-capabilities, semantic ...)
- get_file: retrieve the content of a file
- apply_plan: apply a change plan (safe, creates a session for review)
- consult: send a file and prompt to DeepSeek (your own interface)

Your goal: improve tools by ensuring they have proper tool.yaml, JSON input/output, etc. To request an action, you must output the exact tags [ACTION] and [/ACTION] surrounding a JSON command. For example:

[ACTION]
{ "operation": "run_nativeclaw", "subcommand": "list-capabilities" }
[/ACTION]

Make sure these tags appear in your final response as plain text. After each action, you will receive the result. You may also ask the user for input if needed.

Proceed step by step. Start by listing all tools and their current status.
"""
    # Write system prompt to a temp file (we'll reuse this file for each consult)
    prompt_file = PROJECT_ROOT / "ai_context" / "meta_prompt.txt"
    prompt_file.write_text(system_prompt, encoding='utf-8')

    # Initial user message
    user_message = "Please begin."

    while iteration < MAX_ITER:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        # Combine history? For simplicity, we'll just send the current user message.
        # A more sophisticated agent would maintain a conversation history.
        response = consult_deepseek(str(prompt_file), user_message)
        if response.get("status") != "success":
            print(f"Consult failed: {response}")
            break
        ai_message = response["data"]
        print("\nAI:", ai_message)

        actions = extract_actions(ai_message)
        if not actions:
            print("No action blocks found. Assuming done or asking for input.")
            break

        for action in actions:
            print(f"\nExecuting: {action}")
            try:
                result = send_command(action)
                print(f"Result: {json.dumps(result, indent=2)}")
                # Append result to conversation? We'll incorporate it into the next user message.
                # For now, we'll just store it and continue.
            except Exception as e:
                print(f"Error executing action: {e}")
                break

        # Prepare next user message – could be as simple as "Continue." or we could include results.
        # To keep context, we'll append the results to the prompt file? That's messy.
        # Instead, we'll use a simple "Continue." and rely on the AI to remember conversation.
        # A better approach is to maintain a conversation log and send it as a file each time.
        # For simplicity, we'll just send "Continue." and see if the AI remembers.
        user_message = "Continue."

    print("\nMeta‑agent finished.")

if __name__ == "__main__":
    main()