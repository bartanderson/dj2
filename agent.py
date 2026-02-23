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
    read_files,
    write_file,
    search_files,
    create_branch,
    commit_changes,
    show_diff,
    log_event
)

TOOL_DESCRIPTIONS = """
- analyze_tools(): returns a dictionary with analysis of all tools (capabilities, imports, hotspots, orphans, duplicates, etc.)
- deepseek_consult(prompt, file=None, data=None): send a prompt and optional context to DeepSeek, returns response.
- read_file(path): returns content of file as string (path relative to project root).
- read_files(file_paths): takes a list of file paths and returns a dict of path -> content.
- write_file(path, content): writes content to file (creates backup). Use with caution.
- search_files(query, limit=10, group=None): returns a list of file paths (relative to project root) matching the query. Uses the existing ai.py search command.
- create_branch(branch_name): creates a new git branch and switches to it.
- commit_changes(message): commits all changes with message.
- show_diff(): returns git diff of current changes.
"""

def extract_json_array(text):
    """
    Extract a JSON array or object from text. If a single object is found,
    it will be wrapped in an array. Returns the JSON string or None.
    """
    # Remove markdown fences and strip
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Strategy 1: Try to parse the whole text as JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return text
        elif isinstance(parsed, dict):
            # Single object – wrap in array
            return f"[{text}]"
    except json.JSONDecodeError:
        pass

    # Strategy 2: Find first '[' and matching ']'
    stack = []
    start = -1
    for i, ch in enumerate(text):
        if ch == '[':
            if not stack:
                start = i
            stack.append(ch)
        elif ch == ']':
            if stack:
                stack.pop()
                if not stack:
                    candidate = text[start:i+1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        # Not valid, continue
                        pass
    # Strategy 3: Use raw_decode to find the first JSON object
    try:
        decoder = json.JSONDecoder()
        obj, end = decoder.raw_decode(text)
        if isinstance(obj, dict):
            # Found a single object, wrap it
            return f"[{text[:end]}]"
    except:
        pass

    return None

def call_deepseek_for_plan(goal, max_retries=3):
    """Ask DeepSeek for a plan, with aggressive cleaning and correction."""
    system_prompt = """You are a strict JSON generator. You output only valid JSON arrays.
A JSON array starts with '[' and ends with ']' and contains a list of objects.
Never include explanations, markdown, or any other text.

IMPORTANT RULES:
- DeepSeek cannot directly read files. If file contents are needed, you MUST use the 'read_file' or 'read_files' tool first.
- When you have a list of file paths from a previous step, you cannot pass them directly to deepseek_consult and expect DeepSeek to read them. Instead, first use 'read_files' to get the content, then include that content in the prompt to deepseek_consult (e.g., as data).
- If a step's output is needed later, store it with "store_as".
- You may chain multiple tool calls to achieve the goal.

Available tools:
{descriptions}
"""
    example = """
Example of valid output (note the outer brackets):
[
  {{"tool": "analyze_tools", "arguments": {{}}, "store_as": "analysis"}},
  {{"tool": "deepseek_consult", "arguments": {{"prompt": "Summarize", "data": "$analysis"}}, "store_as": "summary"}}
]
"""
    base_prompt = system_prompt + "\n" + example + "\nNow output only the JSON array for the user's goal (no other text):"
    user_prompt = base_prompt.format(descriptions=TOOL_DESCRIPTIONS) + f"\n\nThe user's goal: \"{goal}\""

    for attempt in range(max_retries):
        raw_response = deepseek_consult(prompt=user_prompt)
        print(f"\nDEBUG: Raw response (attempt {attempt+1}):\n{raw_response}\n")
        log_event('raw_plan_response', raw_response)

        json_str = extract_json_array(raw_response)
        if json_str:
            try:
                plan = json.loads(json_str)
                if isinstance(plan, dict):
                    plan = [plan]  # wrap single object
                if isinstance(plan, list):
                    # Validate each step has required fields
                    for step in plan:
                        if 'tool' not in step:
                            raise ValueError(f"Step missing 'tool': {step}")
                        if 'arguments' not in step:
                            step['arguments'] = {}  # default empty
                    return plan
            except Exception as e:
                log_event('plan_parse_error', {'error': str(e), 'json_str': json_str})

        print(f"Attempt {attempt+1} failed to extract valid JSON.")
        if attempt < max_retries - 1:
            # Corrective prompt – also escape braces
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

    # Log the tool call
    log_event('tool-call', {'tool': tool_name, 'args': resolved})

    try:
        if tool_name == 'analyze_tools':
            result = analyze_tools(**resolved)
        elif tool_name == 'deepseek_consult':
            result = deepseek_consult(**resolved)
        elif tool_name == 'read_file':
            result = read_file(**resolved)
        elif tool_name == 'read_files':
            result = read_files(**resolved)
        elif tool_name == 'write_file':
            result = write_file(**resolved)
        elif tool_name == 'search_files':
            result = search_files(**resolved)
        elif tool_name == 'create_branch':
            result = create_branch(**resolved)
        elif tool_name == 'commit_changes':
            result = commit_changes(**resolved)
        elif tool_name == 'show_diff':
            result = show_diff(**resolved)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        log_event('tool-result', {'tool': tool_name, 'result': result})
        return result
    except Exception as e:
        log_event('error', f"Tool {tool_name} failed: {e}")
        raise

def process_goal(goal, session_context):
    """Process a single goal, update session_context, return new session_context."""
    print(f"\nGoal: {goal}\n")
    print("Planning...")
    plan = call_deepseek_for_plan(goal)
    if not plan:
        print("Could not generate a plan.")
        return session_context

    print("\nExecuting plan:")
    # Start with session context, will be updated with step results
    context = session_context.copy()
    for i, step in enumerate(plan):
        tool = step.get('tool')
        args = step.get('arguments', {})
        store = step.get('store_as')
        print(f"\nStep {i+1}: {tool} with {args}")
        try:
            result = execute_tool(tool, args, context)
            if store:
                context[store] = result
                print(f"  Stored as '{store}'")
            # Display result
            result_str = str(result)
            print(f"  Result length: {len(result_str)} chars")
            if len(result_str) > 500:
                save = input("Result is long. Save to file? (y/n): ").strip().lower()
                if save == 'y':
                    from datetime import datetime
                    filename = f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(result_str)
                    print(f"  Saved to {filename}")
                else:
                    print(f"  Preview (first 500 chars):\n{result_str[:500]}")
            else:
                print(f"  Result:\n{result_str}")
        except Exception as e:
            print(f"  Error: {e}")
            cont = input("Continue? (y/n): ").strip().lower()
            if cont != 'y':
                break

    # After plan, check for a final answer
    final = context.get('final_answer') or context.get('result')
    if final:
        print("\n=== Final Answer ===")
        final_str = str(final)
        print(final_str)
        if len(final_str) > 500:
            save = input("Final answer is long. Save to file? (y/n): ").strip().lower()
            if save == 'y':
                from datetime import datetime
                filename = f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(final_str)
                print(f"Saved to {filename}")

    return context

def main():
    print("Interactive AI Agent. Type your goals, or 'exit' to quit.")
    session_context = {}
    while True:
        try:
            goal = input("\n🎯 Goal: ").strip()
            if goal.lower() in ('exit', 'quit', 'q'):
                break
            if not goal:
                continue
            session_context = process_goal(goal, session_context)
        except KeyboardInterrupt:
            print("\nExiting.")
            break
        except Exception as e:
            import traceback
            traceback.print_exc()
            log_event('fatal_error', {'message': str(e), 'traceback': traceback.format_exc()})

if __name__ == '__main__':
    main()