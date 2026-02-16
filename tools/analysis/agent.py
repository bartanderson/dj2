#!/usr/bin/env python3
"""
Multi‑turn ReAct agent for test generation.
Supports --one-shot mode to stop after first tool call.
"""
import json
import re
import sys
import argparse
import shlex
from pathlib import Path
import importlib.util

# ----------------------------------------------------------------------
# Path setup
# ----------------------------------------------------------------------
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
scripts_dir = project_root / "scripts"
if scripts_dir.exists() and str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
tools_dir = project_root / "tools"
if tools_dir.exists() and str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from ollama_client import get_ollama_client

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

def find_tool_calls(text):
    """Return list of (tool_name, args_list) from any TOOL_CALL: lines."""
    tool_calls = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("TOOL_CALL:"):
            match = re.match(r"TOOL_CALL:\s*(\w+)\((.*)\)", line, re.DOTALL)
            if match:
                tool_name = match.group(1)
                args_str = match.group(2).strip()
                try:
                    args_list = shlex.split(args_str)
                except:
                    args_list = [a.strip() for a in args_str.split(",") if a.strip()]
                tool_calls.append((tool_name, args_list))
    return tool_calls

def build_args_dict(tool_name, args_list, tools):
    """Convert argument list to dictionary, handling multiple keyword arguments."""
    # Get expected parameter names for this tool
    param_names = []
    for t in tools:
        if t["function"]["name"] == tool_name:
            param_names = list(t["function"]["parameters"]["properties"].keys())
            break
    args_dict = {}
    # First, try to parse as keyword arguments
    for token in args_list:
        token = token.strip()
        if '=' in token:
            key, value = token.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            if key in param_names:
                args_dict[key] = value
            else:
                # Unexpected key – ignore
                pass
        else:
            # If any token is not a keyword, we'll fall back to positional for all
            args_dict = {}
            break
    # If we couldn't parse as keywords, assume positional
    if not args_dict:
        for i, token in enumerate(args_list):
            token = token.strip().strip('"\'')
            if i < len(param_names):
                args_dict[param_names[i]] = token
    return args_dict

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tools", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    parser.add_argument("--db", default="ai_context/scout.db")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--model", default="llama3.2:3b")
    parser.add_argument("--max-turns", type=int, default=15)
    parser.add_argument("--max-tokens", type=int, default=16000)
    parser.add_argument("--one-shot", action="store_true", help="Stop after first tool call")
    args = parser.parse_args()

    # Load tools
    tools_path = Path(args.tools)
    if not tools_path.exists():
        print(f"❌ Tools file not found: {tools_path}")
        return 1
    tools_mod = load_module_from_file(str(tools_path), "tools_mod")
    tools = tools_mod.TOOLS
    get_handlers = tools_mod.get_handlers

    db_path = Path(args.db).resolve()
    project_root = Path(args.project_root).resolve()
    handlers = get_handlers(db_path, project_root)

    # Load prompt
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

    client = get_ollama_client()
    if not client.ensure_running():
        print("❌ Ollama not available.")
        return 1

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
        print(prompt)
        print("==============")

        response = client.generate(prompt, model=args.model, max_tokens=args.max_tokens, temperature=0.2)
        text = response.text.strip()
        print(f"\n=== RAW RESPONSE ===\n{text}\n===================")

        tool_calls = find_tool_calls(text)
        if tool_calls:
            # Add assistant message to history
            messages.append({"role": "assistant", "content": text})
            # Execute only the first tool call
            tool_name, args_list = tool_calls[0]
            args_dict = build_args_dict(tool_name, args_list, tools)
            # Check for nested tool calls in arguments
            nested = False
            for val in args_dict.values():
                if isinstance(val, str) and re.search(r'\w+\s*\(', val):
                    nested = True
                    break
            if nested:
                result = f"Error: Argument contains a nested tool call. Use literal values only. Arguments received: {args_dict}"
            else:
                print(f"Tool call: {tool_name}({args_dict})")
                handler = handlers.get(tool_name)
                if not handler:
                    result = f"Unknown tool: {tool_name}"
                else:
                    result = handler(args_dict)
            print(f"Result: {result[:200]}...")
            messages.append({"role": "user", "content": f"TOOL_RESULT: {result}"})
            # If one-shot, stop after first tool call
            if args.one_shot:
                print("\n--- One-shot mode: stopping after first tool call ---")
                print("Final conversation:")
                for msg in messages[-2:]:  # show last assistant and tool result
                    print(f"{msg['role'].upper()}: {msg['content'][:100]}...")
                return 0
            continue

        # No tool calls, check for final answer
        if "```" in text:
            match = re.search(r"```(?:\w+)?\n(.*?)\n```", text, re.DOTALL)
            if match:
                final = match.group(1).strip()
            else:
                final = text.strip()
            if args.output:
                Path(args.output).write_text(final, encoding='utf-8')
                print(f"✅ Result written to {args.output}")
            else:
                print("\n" + "="*40)
                print(final)
                print("="*40)
            return 0

        messages.append({"role": "assistant", "content": text})

    print("❌ Max turns reached without final output.")
    return 1

if __name__ == "__main__":
    sys.exit(main())