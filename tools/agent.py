#!/usr/bin/env python3
# simple_agent.py

import re
import sys
import datetime
from pathlib import Path

# Path setup – script is in project root
script_dir = Path(__file__).parent          # .../dj2/tools/
project_root = script_dir.parent             # .../dj2/
tools_dir = script_dir
# Setup session log with timestamp
session_dir = project_root / "ai_context" / "session"
session_dir.mkdir(parents=True, exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = session_dir / f"agent_session_{timestamp}.log"    

# Add tools directory to path
sys.path.insert(0, str(tools_dir))

from langchain_ollama import ChatOllama
import tools.default_tools as tools_mod

def log_to_file(entry):
    """Append entry to log file with timestamp."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}]\n{entry}\n\n")

def extract_tool_calls(text):
    pattern = r'<tool>(.*?)</tool>'
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    tool_calls = []
    for match in matches:
        m = re.match(r'(\w+)\((.*)\)', match.strip(), re.DOTALL)
        if m:
            tool_name = m.group(1)
            args_str = m.group(2).strip()
            tool_calls.append((tool_name, args_str))
    return tool_calls

def extract_final(text):
    match = re.search(r'<final>(.*?)</final>', text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None

def parse_args_string(args_str, tool_name, tools):
    args_dict = {}
    pattern = r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s]+))'
    matches = list(re.finditer(pattern, args_str))
    if matches:
        for match in matches:
            key = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4)
            if value.endswith(','):
                value = value[:-1].rstrip()
            args_dict[key] = value
        return args_dict
    # fallback to positional
    param_names = []
    for t in tools:
        if t["function"]["name"] == tool_name:
            param_names = list(t["function"]["parameters"]["properties"].keys())
            break
    import shlex
    try:
        positional = shlex.split(args_str)
    except:
        positional = [v.strip() for v in args_str.split(',') if v.strip()]
    for i, val in enumerate(positional):
        if i < len(param_names):
            args_dict[param_names[i]] = val.strip('"\'')
    return args_dict

def main():
    if len(sys.argv) < 2:
        print("Usage: simple_agent.py <user request>")
        return 1

    user_input = " ".join(sys.argv[1:])

    # Load tools and handlers
    tools = tools_mod.TOOLS
    handlers = tools_mod.get_handlers(db_path=None, project_root=project_root)

    # Load prompt
    prompt_path = project_root / "prompts" / "agent.txt"
    sys_prompt = prompt_path.read_text(encoding='utf-8')

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_input}
    ]

    # Initialize Ollama directly
    llm = ChatOllama(model="mistral:7b", temperature=0.2, num_predict=4000)

    max_turns = 10
    for turn in range(max_turns):
        # Build prompt
        prompt = ""
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            prompt += f"{role}: {content}\n"
        prompt += "ASSISTANT:"

        print(f"\n--- Turn {turn+1} ---")
        # Log the prompt before sending
        log_to_file(f"--- Turn {turn+1} PROMPT ---\n{prompt}")

        response = llm.invoke(prompt)
        text = response.content
        print(f"\nRAW: {text}\n")
        log_to_file(f"--- Turn {turn+1} RAW ---\n{text}")

        messages.append({"role": "assistant", "content": text})

        # 1. Tool calls first
        tool_calls = extract_tool_calls(text)
        if tool_calls:
            for tool_name, args_str in tool_calls:
                args_dict = parse_args_string(args_str, tool_name, tools)
                handler = handlers.get(tool_name)
                if not handler:
                    result = f"Unknown tool: {tool_name}"
                else:
                    try:
                        result = handler(**args_dict)
                        log_to_file(f"--- Tool {tool_name} result ---\n{result}")
                    except Exception as e:
                        result = f"Error executing {tool_name}: {e}"
                        log_to_file(f"--- Tool {tool_name} result ---\n{result}")
                print(f"Executed {tool_name}: {str(result)[:100]}...")
                messages.append({"role": "user", "content": f"TOOL_RESULT: {result}"})
            continue

        # 2. No tool calls – check for final
        final = extract_final(text)
        if final:
            print("\n=== FINAL ANSWER ===")
            print(final)
            log_to_file(f"=== FINAL ANSWER ===\n{final}")
            return 0

        # 3. Implicit final
        print("\n=== FINAL ANSWER (implicit) ===")
        print(text.strip())
        # Log implicit final as a single entry
        log_to_file(f"=== FINAL ANSWER (implicit) ===\n{text.strip()}")
        return 0

    print("Max turns reached.")
    return 1

if __name__ == "__main__":
    sys.exit(main())