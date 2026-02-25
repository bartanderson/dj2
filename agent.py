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
    log_event,
    semantic_search
)

TOOL_DESCRIPTIONS = """
- analyze_tools(): returns a dictionary with analysis of all tools (capabilities, imports, hotspots, orphans, duplicates, etc.)
- semantic_search(query, limit=5): returns a list of files relevant to the natural language query, with relevance scores. Uses the embedding index.
- arch_context(query, level='standard'): generates a rich context package (file snippets, behavioral contracts) for the given query using arch_recon.py. The level can be 'brief', 'standard', or 'deep'. Returns JSON.
- deepseek_consult(prompt, file=None, data=None, timeout=3600): send a prompt and optional context to DeepSeek, waits up to `timeout` seconds for response. Use a large timeout for long-running tasks. Returns response string.
- read_file(path): returns content of file as string (path relative to project root).
- read_files(file_paths): takes a list of file paths and returns a dict of path -> content.
- write_file(path, content): writes content to file (creates backup). Use with caution.
- search_files(query, limit=10, group=None): returns a list of file paths (relative to project root) matching the query. Uses the existing ai.py search command.
- create_branch(branch_name): creates a new git branch and switches to it.
- commit_changes(message): commits all changes with message.
- show_diff(): returns git diff of current changes.
"""

def get_plan_from_deepseek(prompt, max_retries=3):
    """Send a custom prompt to DeepSeek and return a list of tool calls."""
    for attempt in range(max_retries):
        raw = deepseek_consult(prompt=prompt)
        json_str = extract_json_array(raw)
        if json_str:
            try:
                plan = json.loads(json_str)
                if isinstance(plan, dict):
                    plan = [plan]
                if isinstance(plan, list):
                    # Validate each step
                    for step in plan:
                        if 'tool' not in step:
                            raise ValueError("Step missing 'tool'")
                        if 'arguments' not in step:
                            step['arguments'] = {}
                    return plan
            except Exception as e:
                log_event('plan_parse_error', {'error': str(e), 'json_str': json_str})
        if attempt < max_retries - 1:
            prompt = f"Your previous response was not valid JSON. Please output a JSON array of tool calls. Raw: {raw}"
    return []
    
def extract_json_array(text):
    """Extract JSON by trimming leading text to first '{' or '[' and trailing text after last '}' or ']'. Then try to parse, adding outer brackets if needed."""
    # Remove markdown fences
    text = re.sub(r'^```json\s*', '', text.strip(), flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Find first '{' or '['
    start = -1
    for i, ch in enumerate(text):
        if ch in '{[':
            start = i
            break
    if start == -1:
        return None

    # Find last '}' or ']'
    end = -1
    for i in range(len(text)-1, -1, -1):
        if text[i] in '}]':
            end = i
            break
    if end == -1 or end <= start:
        return None

    candidate = text[start:end+1]

    # Try parsing as is
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, list):
            return candidate
        elif isinstance(parsed, dict):
            # Single object, wrap in array
            return f"[{candidate}]"
    except json.JSONDecodeError:
        pass

    # Try adding outer brackets
    try:
        parsed = json.loads('[' + candidate + ']')
        if isinstance(parsed, list):
            return '[' + candidate + ']'
    except json.JSONDecodeError:
        pass

    # Fallback: use raw_decode to find the first JSON value
    try:
        decoder = json.JSONDecoder()
        obj, end = decoder.raw_decode(text)
        if isinstance(obj, dict):
            # Found a single object, wrap it
            return f"[{text[:end]}]"
        elif isinstance(obj, list):
            return text[:end]
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
        elif tool_name == 'semantic_search':
            return semantic_search(**resolved)
        elif tool_name == 'arch_context':
            return arch_context(**resolved)
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
    """Process a goal with user approval at each step. After each plan, automatically asks DeepSeek for next steps."""
    print(f"\nGoal: {goal}\n")
    max_iterations = 10
    iteration = 0
    original_goal = goal
    context = session_context.copy()
    next_plan = None  # plan for next iteration, if any

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        # Determine the plan for this iteration
        if next_plan is not None:
            plan = next_plan
            next_plan = None
        else:
            print("Planning...")
            plan = call_deepseek_for_plan(original_goal)
            if not plan:
                print("Could not generate a plan.")
                break

        # Show proposed plan
        print("\nProposed plan:")
        for i, step in enumerate(plan):
            print(f"  {i+1}. {step['tool']} with args {step.get('arguments', {})}")
            if 'store_as' in step:
                print(f"     → store as '{step['store_as']}'")

        # Ask for approval
        response = input("\nExecute this plan? (y/n/modify/stop): ").strip().lower()
        if response == 'stop':
            break
        elif response == 'modify':
            print("Enter new plan as JSON array, or type 'auto' to let AI regenerate:")
            new_plan_input = input("> ").strip()
            if new_plan_input == 'auto':
                continue  # will regenerate in next loop iteration
            try:
                plan = json.loads(new_plan_input)
                if not isinstance(plan, list):
                    plan = [plan]
                for step in plan:
                    if 'tool' not in step:
                        raise ValueError("Step missing 'tool'")
                    if 'arguments' not in step:
                        step['arguments'] = {}
            except Exception as e:
                print(f"Invalid JSON: {e}. Using original plan.")
        elif response != 'y':
            print("Skipping plan.")
            break

        # Execute the plan
        print("\nExecuting plan:")
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
                # Show result summary
                result_str = str(result)
                print(f"  Result length: {len(result_str)} chars")
                if len(result_str) > 500:
                    print(f"  Preview: {result_str[:500]}...")
                else:
                    print(f"  Result: {result_str}")
            except Exception as e:
                print(f"  Error: {e}")
                cont = input("Continue with next steps? (y/n): ").strip().lower()
                if cont != 'y':
                    break

        # After execution, check if we have a final answer
        final = context.get('final_answer') or context.get('result')
        if final:
            print("\n=== Final Answer ===")
            print(final)
            save = input("Save final answer to file? (y/n): ").strip().lower()
            if save == 'y':
                from datetime import datetime
                filename = f"final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(final))
                print(f"Saved to {filename}")
            break

        # No final answer yet – ask DeepSeek for the next step
        print("\nDetermining next step...")
        next_plan_prompt = f"The original goal is: '{original_goal}'. The current results are stored in these variables: {list(context.keys())}. Based on these, what is the next logical step to achieve the original goal? Output a JSON array of tool calls."
        next_plan = get_plan_from_deepseek(next_plan_prompt)
        if not next_plan:
            print("Could not determine next step. Stopping.")
            break

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
            print("\nInterrupted.")
            cont = input("Continue? (y/n): ").strip().lower()
            if cont != 'y':
                break
        except Exception as e:
            print(f"Error: {e}")
            log_event('fatal_error', str(e))

if __name__ == '__main__':
    main()