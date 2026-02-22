#!/usr/bin/env python3
"""
Simple AI agent that uses tools to answer questions about your codebase.
Usage: python agent.py "your goal here"
"""

import sys
import json
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

def call_deepseek_for_plan(goal, max_retries=3):
    """Ask DeepSeek for a plan, with aggressive cleaning and correction."""
    system_prompt = """You are a strict JSON generator. You output only valid JSON arrays.
Never include explanations, markdown, or any other text."""
    example = """
Example of valid output:
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
        # Clean the response: remove markdown fences, leading/trailing text
        cleaned = re.sub(r'^```json\s*', '', raw_response.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        # Find the first '[' and last ']'
        start = cleaned.find('[')
        end = cleaned.rfind(']')
        if start != -1 and end != -1 and end > start:
            json_str = cleaned[start:end+1]
        else:
            json_str = cleaned  # fallback

        try:
            plan = json.loads(json_str)
            if isinstance(plan, list):
                return plan
            else:
                raise ValueError("Not a list")
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                # Send corrective prompt
                user_prompt = f"""Your previous response was not valid JSON. It was:
{raw_response}

Please output ONLY a JSON array for the goal: "{goal}"
Follow this exact format:
[
  {{"tool": "tool_name", "arguments": {{}}, "store_as": "var"}}
]
No other text."""
            else:
                print(f"Final raw response:\n{raw_response}")
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

    # Dispatch
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

def main():
    if len(sys.argv) < 2:
        print("Usage: agent.py <goal>")
        sys.exit(1)
    goal = sys.argv[1]

    print(f"Goal: {goal}\n")

    print("Planning...")
    plan = call_deepseek_for_plan(goal)
    if not plan:
        print("Could not generate a plan.")
        return

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

if __name__ == '__main__':
    main()