#!/usr/bin/env python3
"""
Interactive AI agent that uses tools to answer questions about your codebase.
Usage: python agent.py  (then type goals interactively)
"""

import sys
import json
import re
from agent_tools import (
    analyze_tools,
    deepseek_consult,
    read_file,
    write_file,
    create_branch,
    commit_changes,
    show_diff
)

TOOL_DESCRIPTIONS = """
- analyze_tools(): returns a dictionary with analysis of all tools (capabilities, imports, hotspots, orphans, duplicates, etc.)
- deepseek_consult(prompt, file=None, data=None): send a prompt and optional context to DeepSeek, returns response.
- read_file(path): returns content of file as string (path relative to project root).
- write_file(path, content): writes content to file (creates backup). Use with caution.
- create_branch(branch_name): creates a new git branch and switches to it.
- commit_changes(message): commits all changes with message.
- show_diff(): returns git diff of current changes.
"""

def extract_json_array(text):
    """Extract the first valid JSON array from text, ignoring surrounding content."""
    # Remove markdown fences first
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)

    # Strategy 1: raw_decode
    try:
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(text):
            while idx < len(text) and text[idx].isspace():
                idx += 1
            if idx >= len(text):
                break
            try:
                obj, end = decoder.raw_decode(text, idx)
                if isinstance(obj, list):
                    return text[idx:end]
                idx = end
            except json.JSONDecodeError:
                idx += 1
    except Exception:
        pass

    # Strategy 2: bracket matching with retry
    stack = []
    start = -1
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '[' and not stack:
            start = i
            stack.append(ch)
        elif ch == '[' and stack:
            stack.append(ch)
        elif ch == ']' and stack:
            stack.pop()
            if not stack:
                candidate = text[start:i+1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    i = start + 1
                    stack = []
                    start = -1
                    continue
        i += 1

    # Strategy 3: Fallback for missing outer brackets (comma‑separated objects)
    # Regex: optional whitespace, then { ... }, then comma, then { ... }, etc.
    if re.match(r'^\s*\{.*\}\s*,\s*\{.*\}\s*$', text, re.DOTALL):
        candidate = f"[{text}]"
        try:
            json.loads(candidate)
            print("DEBUG: Added missing brackets, valid JSON")
            return candidate
        except:
            pass

    return None

def call_deepseek_for_plan(goal, max_retries=3):
    """Ask DeepSeek for a plan, with aggressive cleaning and correction."""
    system_prompt = """You are a strict JSON generator. You output only valid JSON arrays.
A JSON array starts with '[' and ends with ']' and contains a list of objects.
Never include explanations, markdown, or any other text."""
    example = """
Example of valid output (note the outer brackets):
[
  {"tool": "analyze_tools", "arguments": {}, "store_as": "analysis"},
  {"tool": "deepseek_consult", "arguments": {"prompt": "Summarize", "data": "$analysis"}, "store_as": "summary"}
]
"""
    user_prompt = f"""{system_prompt}

Available tools:
{TOOL_DESCRIPTIONS}

The user's goal: "{goal}"

{example}

Now output only the JSON array for the user's goal (no other text):"""

    for attempt in range(max_retries):
        raw_response = deepseek_consult(prompt=user_prompt)
        print(f"\nDEBUG: Raw response (attempt {attempt+1}):\n{raw_response}\n")

        json_str = extract_json_array(raw_response)
        if json_str:
            try:
                plan = json.loads(json_str)
                if isinstance(plan, list):
                    return plan
            except json.JSONDecodeError:
                pass

        print(f"Attempt {attempt+1} failed to extract valid JSON.")
        if attempt < max_retries - 1:
            # Send corrective prompt
            user_prompt = f"""Your previous response was not valid JSON. It was:
{raw_response}

Please output ONLY a JSON array for the goal: "{goal}"
The array must start with '[' and end with ']' and contain objects with fields "tool", "arguments", and optionally "store_as".
Example:
[
  {{"tool": "analyze_tools", "arguments": {{}}, "store_as": "analysis"}}
]
No other text, no markdown, no explanation."""
        else:
            return []
    return []

def execute_tool(tool_name, args, context):
    """Call the actual Python function with resolved arguments."""
    # Resolve any $var references in args
    resolved = {}
    for k, v in args.items():
        if isinstance(v, str) and v.startswith('$'):
            var_name = v[1:]
            resolved[k] = context.get(var_name, v)
        else:
            resolved[k] = v

    if tool_name == 'analyze_tools':
        return analyze_tools(**resolved)
    elif tool_name == 'deepseek_consult':
        return deepseek_consult(**resolved)
    elif tool_name == 'read_file':
        return read_file(**resolved)
    elif tool_name == 'write_file':
        return write_file(**resolved)
    elif tool_name == 'create_branch':
        return create_branch(**resolved)
    elif tool_name == 'commit_changes':
        return commit_changes(**resolved)
    elif tool_name == 'show_diff':
        return show_diff(**resolved)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")

def process_goal(goal):
    """Process a single goal and return True if successful."""
    print(f"\nGoal: {goal}\n")
    print("Planning...")
    plan = call_deepseek_for_plan(goal)
    if not plan:
        print("Could not generate a plan.")
        return False

    print("\nExecuting plan:")
    context = {}
    for i, step in enumerate(plan):
        tool = step.get('tool')
        args = step.get('arguments', {})
        store = step.get('store_as')
        print(f"\nStep {i+1}: {tool} with {args}")
        try:
            result = execute_tool(tool, args, context)
            if store:
                context[store] = result
            preview = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
            print(f"  Result: {preview}")
        except Exception as e:
            print(f"  Error: {e}")
            cont = input("Continue? (y/n): ").strip().lower()
            if cont != 'y':
                break

    final = context.get('final_answer') or context.get('result')
    if final:
        print("\n=== Final Answer ===")
        print(final)
    return True

def main():
    print("Interactive AI Agent. Type your goals, or 'exit' to quit.")
    while True:
        try:
            goal = input("\n🎯 Goal: ").strip()
            if goal.lower() in ('exit', 'quit', 'q'):
                break
            if not goal:
                continue
            process_goal(goal)
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    main()