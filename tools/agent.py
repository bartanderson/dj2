#!/usr/bin/env python3
"""
Multi‑turn ReAct agent for test generation.
Supports --one-shot mode to stop after first tool call.
Uses XML tags: <tool>tool_name(args)</tool> and <final>answer</final>.
"""

import json
import re
import sys
import argparse
from pathlib import Path
import importlib.util

# ----------------------------------------------------------------------
# Path setup – find project root (parent of tools directory)
# ----------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent          # tools/
project_root = script_dir.parent                       # project root (dj2/)
scripts_dir = project_root / "scripts"
tools_dir = project_root / "tools"

for d in [scripts_dir, tools_dir]:
    if d.exists() and str(d) not in sys.path:
        sys.path.insert(0, str(d))

# ----------------------------------------------------------------------
# Imports (now that paths are set)
# ----------------------------------------------------------------------
from tools.model_client import OllamaClient, DeepSeekClient

def load_module_from_file(file_path: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def format_tools_for_prompt(tools):
    lines = []
    for t in tools:
        name = t["function"]["name"]
        desc = t["function"]["description"]
        params = t["function"]["parameters"]["properties"]
        param_str = ", ".join(params.keys())
        lines.append(f"- {name}({param_str}): {desc}")
    return "\n".join(lines)

# ----------------------------------------------------------------------
# New parsing functions for XML tags
# ----------------------------------------------------------------------
def extract_tool_calls(text):
    """
    Return list of (tool_name, args_str) from <tool>...</tool> tags.
    Example: <tool>search_files(query="python", limit=5)</tool>
    """
    pattern = r'<tool>(.*?)</tool>'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    tool_calls = []
    for match in matches:
        # match is like "search_files(query="python", limit=5)"
        m = re.match(r'(\w+)\((.*)\)', match.strip(), re.DOTALL)
        if m:
            tool_name = m.group(1)
            args_str = m.group(2).strip()
            tool_calls.append((tool_name, args_str))
    return tool_calls

def extract_final(text):
    """Return content of first <final>...</final> tag, or None."""
    match = re.search(r'<final>(.*?)</final>', text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None

def parse_args_string(args_str):
    """
    Parse key=value pairs from a string like 'query="python", limit=5'.
    Returns a dictionary with keys and string values (numbers remain strings).
    Handles quoted values and trailing commas.
    """
    args_dict = {}
    # Find all key=value pairs: key = value (value may be quoted or unquoted)
    pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s]+))'
    for match in re.finditer(pattern, args_str):
        key = match.group(1)
        # Value is one of the three capture groups: double-quoted, single-quoted, or unquoted
        value = match.group(2) or match.group(3) or match.group(4)
        # Remove any trailing comma that might have been captured
        if value.endswith(','):
            value = value[:-1].rstrip()
        args_dict[key] = value
    return args_dict

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tools", required=False, help="Path to tools module (if omitted, uses default tools)")
    parser.add_argument("--prompt", required=False, default=str(project_root / "prompts" / "agent.txt"),
                        help="Path to system prompt file (default: prompts/agent.txt)")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--db", default="ai_context/scout.db")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--model", default="llama3.2:3b")
    parser.add_argument("--max-turns", type=int, default=15)
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument("--one-shot", action="store_true", help="Stop after first tool call")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Load tools
    # ------------------------------------------------------------------
    if args.tools:
        tools_path = Path(args.tools)
        if not tools_path.exists():
            print(f"❌ Tools file not found: {tools_path}")
            return 1
        tools_mod = load_module_from_file(str(tools_path), "tools_mod")
    else:
        import tools.default_tools as tools_mod

    tools = tools_mod.TOOLS
    get_handlers = tools_mod.get_handlers

    # Prepare handlers (ignore db_path and project_root for now)
    handlers = get_handlers(db_path=None, project_root=project_root)

    # ------------------------------------------------------------------
    # Load prompt and prepare system message
    # ------------------------------------------------------------------
    prompt_path = Path(args.prompt)
    if not prompt_path.exists():
        print(f"❌ Prompt file not found: {prompt_path}")
        return 1
    sys_prompt = prompt_path.read_text(encoding='utf-8')
    tools_desc = format_tools_for_prompt(tools)
    full_sys_prompt = sys_prompt + "\n\nAvailable tools:\n" + tools_desc

    messages = [
        {"role": "system", "content": full_sys_prompt},
        {"role": "user", "content": args.input}
    ]

    # ------------------------------------------------------------------
    # Initialize model client
    # ------------------------------------------------------------------
    if args.model.lower() == 'deepseek':
        client = DeepSeekClient(timeout=args.max_tokens)
    else:
        client = OllamaClient(
            model_name=args.model,
            max_tokens=args.max_tokens,
            temperature=0.2
        )

    # ------------------------------------------------------------------
    # Main loop (ReAct)
    # ------------------------------------------------------------------
    for turn in range(args.max_turns):
        print(f"\n--- Turn {turn+1} ---")
        
        # Build prompt from conversation
        prompt = ""
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            prompt += f"{role}: {content}\n"
        prompt += "ASSISTANT:"

        print("\n=== PROMPT ===")
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print("==============")

        text = client.generate(prompt)
        print(f"\n=== RAW RESPONSE ===\n{text}\n===================")

        # Add assistant response to history
        messages.append({"role": "assistant", "content": text})

        # 1. Check for final answer first
        final = extract_final(text)
        if final:
            if args.output:
                Path(args.output).write_text(final, encoding='utf-8')
                print(f"✅ Result written to {args.output}")
            else:
                print("\n" + "="*40)
                print(final)
                print("="*40)
            return 0

        # 2. Check for tool calls
        tool_calls = extract_tool_calls(text)
        if tool_calls:
            print(f"\nFound {len(tool_calls)} tool call(s)")
            
            for tool_name, args_str in tool_calls:
                # Parse arguments string into dictionary
                args_dict = parse_args_string(args_str)
                
                # Check for nested tool calls (crude injection prevention)
                nested = False
                for val in args_dict.values():
                    if isinstance(val, str) and re.search(r'\w+\s*\(', val):
                        nested = True
                        break
                
                if nested:
                    result = f"Error: Nested tool call detected in arguments: {args_dict}"
                else:
                    print(f"Executing: {tool_name}({args_dict})")
                    handler = handlers.get(tool_name)
                    if not handler:
                        result = f"Unknown tool: {tool_name}"
                    else:
                        # Pass the dictionary as keyword arguments
                        result = handler(**args_dict)
                
                print(f"Result: {str(result)[:200]}...")
                messages.append({"role": "user", "content": f"TOOL_RESULT: {result}"})
            
            # After executing tools, continue to next turn
            if args.one_shot:
                print("\n--- One-shot mode: stopping after first tool call ---")
                return 0
            continue  # Go to next turn to process tool results

        # 3. No tool calls, no final tag – treat as implicit final answer
        final = text.strip()
        if final:
            if args.output:
                Path(args.output).write_text(final, encoding='utf-8')
                print(f"✅ Result written to {args.output}")
            else:
                print("\n" + "="*40)
                print(final)
                print("="*40)
            return 0

    print("❌ Max turns reached without final output.")
    return 1

if __name__ == "__main__":
    sys.exit(main())