#!/usr/bin/env python3
"""
Generic ReAct agent using Ollama with manual tool‑call parsing.
Works with any model; does not rely on native tool calling.
"""
import json
import re
import sys
import argparse
import shlex
from pathlib import Path
import importlib.util

# Path setup
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

def load_tools(tools_module):
    """Extract tool definitions and handlers from a module."""
    return tools_module.TOOLS, tools_module.get_handlers

def format_tools_for_prompt(tools):
    """Convert tool definitions to a readable list for the prompt."""
    lines = []
    for t in tools:
        name = t["function"]["name"]
        desc = t["function"]["description"]
        params = t["function"]["parameters"]["properties"]
        param_str = ", ".join(params.keys())
        lines.append(f"- {name}({param_str}): {desc}")
    return "\n".join(lines)

def parse_tool_call(line):
    """Parse a line like 'TOOL_CALL: tool_name(arg1, arg2, "arg with spaces")' using shlex."""
    match = re.match(r"TOOL_CALL:\s*(\w+)\((.*)\)", line, re.DOTALL)
    if not match:
        return None, None
    tool_name = match.group(1)
    args_str = match.group(2).strip()
    try:
        # Use shlex to split respecting quotes
        args_list = shlex.split(args_str)
    except:
        # Fallback to simple split if shlex fails
        args_list = [a.strip() for a in args_str.split(",") if a.strip()]
    return tool_name, args_list

def run_agent(user_input, tools, get_handlers_func, db_path, project_root, sys_prompt, model="llama3.2:3b", max_turns=15, max_tokens=118000):
    client = get_ollama_client()
    if not client.ensure_running():
        print("❌ Ollama not available.")
        return None

    # Create handlers with injected dependencies
    handlers = get_handlers_func(db_path, project_root)

    # Build the full system prompt including tool descriptions
    tools_desc = format_tools_for_prompt(tools)
    full_sys_prompt = sys_prompt + "\n\nAvailable tools:\n" + tools_desc + """
To use a tool, output exactly:
TOOL_CALL: tool_name(arg1, arg2, ...)

After receiving the tool result (which will be provided as "TOOL_RESULT: ..."), continue reasoning.
When you have enough information, output the final answer inside triple backticks. The final answer should be a complete Python test file. Do not truncate; output the entire test.
"""

    messages = [
        {"role": "system", "content": full_sys_prompt},
        {"role": "user", "content": user_input}
    ]

    for turn in range(max_turns):
        print(f"\n--- Turn {turn+1} ---")
        # Format the conversation as a single prompt
        prompt = ""
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            prompt += f"{role}: {content}\n"
        prompt += "ASSISTANT:"

        # Get response with high token limit
        result = client.generate(prompt, model=model, max_tokens=max_tokens, temperature=0.2)
        response = result.text.strip()
        print(f"Assistant: {response[:500]}..." if len(response) > 500 else f"Assistant: {response}")

        # Check for tool call
        tool_name, args_list = parse_tool_call(response)
        if tool_name:
            # Find the tool's parameter names from the tools list
            param_names = []
            for t in tools:
                if t["function"]["name"] == tool_name:
                    param_names = list(t["function"]["parameters"]["properties"].keys())
                    break
            # Build arguments dictionary by position
            args_dict = {}
            for i, name in enumerate(param_names):
                if i < len(args_list):
                    args_dict[name] = args_list[i]
                else:
                    args_dict[name] = ""
            print(f"Tool call: {tool_name}({args_dict})")
            handler = handlers.get(tool_name)
            if handler:
                tool_result = handler(args_dict)
            else:
                tool_result = f"Unknown tool: {tool_name}"
            print(f"Result: {tool_result[:200]}..." if len(tool_result) > 200 else f"Result: {tool_result}")

            # Add the tool result as a new user message
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"TOOL_RESULT: {tool_result}"})
            # If this was call_deepseek, treat the result as the final test
            if tool_name == "call_deepseek":
                return tool_result
            continue

        # No tool call, check for final answer in triple backticks
        if "```" in response:
            code_match = re.search(r"```(?:\w+)?\n(.*?)\n```", response, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()
            else:
                # Maybe the whole response is the answer
                return response.strip()

        # Otherwise, add assistant response and continue
        messages.append({"role": "assistant", "content": response})

    print("❌ Max turns reached without final output.")
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tools", required=True, help="Path to Python file defining tools and handlers")
    parser.add_argument("--prompt", required=True, help="Path to system prompt file")
    parser.add_argument("--input", required=True, help="User input (e.g., intent)")
    parser.add_argument("--output", help="Output file for final result")
    parser.add_argument("--db", default="ai_context/scout.db", help="Path to scout DB")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--model", default="llama3.2:3b", help="Ollama model name")
    parser.add_argument("--max-turns", type=int, default=15)
    parser.add_argument("--max-tokens", type=int, default=8000, help="Maximum tokens to generate per response")
    args = parser.parse_args()

    tools_path = Path(args.tools)
    if not tools_path.exists():
        print(f"❌ Tools file not found: {tools_path}")
        return 1
    tools_mod = load_module_from_file(str(tools_path), "tools_mod")
    tools, get_handlers_func = load_tools(tools_mod)

    prompt_path = Path(args.prompt)
    if not prompt_path.exists():
        print(f"❌ Prompt file not found: {prompt_path}")
        return 1
    sys_prompt = prompt_path.read_text(encoding='utf-8')

    db_path = Path(args.db).resolve()
    project_root = Path(args.project_root).resolve()

    result = run_agent(args.input, tools, get_handlers_func, db_path, project_root, sys_prompt, args.model, args.max_turns, args.max_tokens)
    if result is None:
        return 1

    if args.output:
        Path(args.output).write_text(result, encoding='utf-8')
        print(f"✅ Result written to {args.output}")
    else:
        print("\n" + "="*40)
        print(result)
        print("="*40)
    return 0

if __name__ == "__main__":
    sys.exit(main())