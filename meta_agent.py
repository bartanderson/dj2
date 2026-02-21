#!/usr/bin/env python3
"""
Meta‑agent: uses DeepSeek via the persistent session to improve tools.
Maintains a conversation loop, feeding results back to the AI.
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
MAX_ITERATIONS = 20  # safety limit

def send_command(cmd):
    """Send a JSON command to the session server and return the response."""
    if not PORT_FILE.exists():
        raise Exception("Session server not running. Start with 'nativeclaw session start'.")
    with open(PORT_FILE, 'r') as f:
        port = int(f.read().strip())
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('localhost', port))
    s.sendall((json.dumps(cmd) + '\n').encode('utf-8'))
    s.shutdown(socket.SHUT_WR)

    # Read length prefix (4 bytes)
    len_bytes = s.recv(4)
    if not len_bytes:
        raise Exception("Server closed connection without sending length")
    expected_len = int.from_bytes(len_bytes, 'big')

    # Read exactly expected_len bytes
    data_parts = []
    remaining = expected_len
    while remaining > 0:
        chunk = s.recv(min(65536, remaining))
        if not chunk:
            break
        data_parts.append(chunk)
        remaining -= len(chunk)
    s.close()

    if remaining != 0:
        raise Exception(f"Incomplete response: expected {expected_len} bytes, got {expected_len - remaining}")

    full_data = b''.join(data_parts).decode('utf-8')
    try:
        return json.loads(full_data)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response: {e}")
        print(f"Response preview: {full_data[:500]}")
        raise

def consult_deepseek(file_path, prompt):
    """Send a consult request to the session server."""
    cmd = {
        "operation": "consult",
        "file": file_path,
        "prompt": prompt
    }
    return send_command(cmd)

def extract_actions(text):
    """Extract action blocks from AI response."""
    actions = []
    # Standard pattern with closing tag
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

    # Initial system prompt
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

Make sure these tags appear in your final response as plain text. After each action, you will receive the result. You may also ask the user for input if needed. When you are finished, include the word "DONE" in your response.

Proceed step by step. Start by listing all tools and their current status.
"""
    # Write system prompt to a temp file
    prompt_file = PROJECT_ROOT / "ai_context" / "meta_prompt.txt"
    prompt_file.write_text(system_prompt, encoding='utf-8')

    # Conversation history as a list of (role, content) pairs
    # We'll simulate by storing prompts and responses, but since we use files,
    # we need to accumulate context in a single file or pass it as a multi‑turn prompt.
    # For simplicity, we'll maintain a context file that grows.
    context_file = PROJECT_ROOT / "ai_context" / "meta_context.txt"
    context_file.write_text(system_prompt + "\n\nNow begin.\n", encoding='utf-8')

    iteration = 0
    while iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        # Send consult with the current context file
        response = consult_deepseek(str(context_file), "Continue with your plan.")
        if response.get("status") != "success":
            print(f"Consult failed: {response}")
            break
        ai_message = response["data"]
        print("AI:", ai_message)

        # Check for termination condition
        if "DONE" in ai_message:
            print("AI indicates completion. Stopping.")
            break

        # Extract and execute actions
        actions = extract_actions(ai_message)
        if not actions:
            print("No action blocks found. Checking if AI is done...")
            if "DONE" in ai_message.upper():
                print("AI indicates completion. Stopping.")
                break
            else:
                print("Automatically continuing...")
                with open(context_file, 'a', encoding='utf-8') as f:
                    f.write("\n[System]: No action blocks detected. Please provide the next step or indicate DONE.\n")
                continue

        # Execute actions and collect results
        results_summary = []
        for action in actions:
            print(f"Executing: {action}")
            try:
                result = send_command(action)
                print(f"Result: {json.dumps(result, indent=2)}")
                results_summary.append(f"Action: {action}\nResult: {json.dumps(result)}")
            except Exception as e:
                print(f"Error executing action: {e}")
                results_summary.append(f"Action: {action}\nError: {e}")

        # Append results to context
        with open(context_file, 'a', encoding='utf-8') as f:
            f.write(f"\n[AI]: {ai_message}\n")
            f.write("[Actions executed]:\n")
            for s in results_summary:
                f.write(s + "\n")
            f.write("\n[Continue]\n")

    print("Meta‑agent finished.")

if __name__ == "__main__":
    main()