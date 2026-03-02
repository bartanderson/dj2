#!/usr/bin/env python3
"""
Orchestrated Agent — agent with planner/critic layer for complex tasks.
[Usage]: python tools\agent.py "analyze the codebase"

# Options
 --no-critic
 --max-turns 15 (default is like 50 so not sure how useful it would be to try lowering or raising)
"""

import re
import sys
import json
import datetime
import argparse
from pathlib import Path
from typing import Any

# Build TOOLS list from available tool functions for planner compatibility
# These are the tools exported by agent_tools that are in TOOL_WHITELIST
from tools import agent_tools
from tools.default_tools import TOOL_WHITELIST
from langchain_ollama import ChatOllama
from tools.planner import Planner
from tools.critic import Critic
from tools.agent_tools import deepseek_consult

def save_tool_result(tool_name: str, result: Any) -> str:
    """Save full tool result to a session file and return a summary message."""
    session_dir = Path('ai_context/sessions')
    session_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = session_dir / f"tool_result_{tool_name}_{timestamp}.txt"
    
    result_str = str(result)
    result_file.write_text(result_str, encoding='utf-8')
    
    # Truncate for display
    if len(result_str) > 500:
        display = result_str[:500] + f"... (truncated, total {len(result_str)} chars)"
    else:
        display = result_str
    
    return f"Result from {tool_name}: {display}\nFull result saved to {result_file}"

# Map of tool names to functions
TOOL_MAP = {}
for name in TOOL_WHITELIST:
    if hasattr(agent_tools, name):
        TOOL_MAP[name] = getattr(agent_tools, name)

# Build TOOLS in OpenAI function-calling format for planner
TOOLS = []
for name in TOOL_WHITELIST:
    if name in TOOL_MAP:
        func = TOOL_MAP[name]
        TOOLS.append({
            'type': 'function',
            'function': {
                'name': name,
                'description': func.__doc__ or f"Execute {name}",
                'parameters': {'type': 'object', 'properties': {}}
            }
        })

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Constant base directory for all sessions
SESSIONS_DIR = Path('ai_context') / 'sessions'
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)  # Ensure exists once at startup

def get_session_log_file() -> Path:
    """Create timestamped log file path in sessions directory."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = SESSIONS_DIR / f"agent_session_{timestamp}.log"
    return log_file

# Initialize log file at module load
LOG_FILE = get_session_log_file()

def log_to_file(entry):
    """Append entry to log file with timestamp."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}]\n{entry}\n\n")

def classify_request(user_input: str) -> str:
    """Determine if request is direct, simple, or complex using LLM."""
    prompt = f"""You are a task classifier. Determine how to handle the user request.

User: {user_input}

Choose one of:
- direct: The request is a simple greeting or a question that can be answered immediately without any tools or analysis. (e.g., "say hello", "what's 2+2?", "thanks")
- simple: The request can be fulfilled by a single tool call without needing a multi‑step plan. (e.g., "read file character_builder.py", "list all Python files", "search for concept movement")
- complex: The request requires multiple steps, analysis, or planning. (e.g., "analyze the codebase", "generate a test for character creation", "compare two files")

Output only the category word.
"""
    try:
        response = deepseek_consult(prompt=prompt, timeout=10)
        category = response.strip().lower()
        if category not in ('direct', 'simple', 'complex'):
            category = 'complex'  # fallback
        return category
    except Exception as e:
        print(f"[Classification error] {e}. Defaulting to complex.")
        return 'complex'

#llm = ChatOllama(model="qwen2.5:7b", temperature=0.2, num_predict=4000)
#llm = ChatOllama(model="mistral:7b", temperature=0.2, num_predict=4000)
# llm = ChatOllama(model="llama3.1:latest", temperature=0.2, num_predict=4000)
#llm = ChatOllama(model="llama3.2:3b", temperature=0.2, num_predict=4000)
#llm = ChatOllama(model="qwen3.5:35b", temperature=0.2, num_predict=4000)
def run_simple_tool_agent(user_input: str, max_turns: int = 5) -> str:
    """Run a simple agent using native tool calling."""
    print(f"\n[SimpleAgent] Starting with input: {user_input}")
    messages = [{"role": "user", "content": user_input}]
    llm = ChatOllama(model="qwen2.5:7b", temperature=0.2, num_predict=4000)
    bound_llm = llm.bind_tools(TOOLS)
    
    for turn in range(max_turns):
        print(f"\n[SimpleAgent] Turn {turn+1}")
        print(f"[SimpleAgent] Invoking bound LLM with {len(messages)} messages...")
        
        try:
            import time
            start = time.time()
            response = bound_llm.invoke(messages)
            elapsed = time.time() - start
            print(f"[SimpleAgent] LLM invoke took {elapsed:.2f} seconds")
        except Exception as e:
            print(f"[SimpleAgent] LLM invoke raised: {e}")
            import traceback
            traceback.print_exc()
            return f"Error: LLM call failed – {e}"

        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            name = tool_call['name']
            args = tool_call.get('args', {})
            print(f"[SimpleAgent] Executing tool: {name} with args: {args}")
            
            if name not in TOOL_MAP:
                result = f"Error: Unknown tool '{name}'"
                print(result, flush=True)
                return result
            else:
                try:
                    raw_result = TOOL_MAP[name](**args)
                    # Use the helper to save and format the result
                    final_message = save_tool_result(name, raw_result)
                    print(final_message, flush=True)
                    return final_message
                except Exception as e:
                    result = f"Error executing {name}: {e}"
                    print(f"[SimpleAgent] {result}", flush=True)
                    return result
        else:
            print("[SimpleAgent] No tool calls – treating as final answer.")
            return response.content
    
    print("[SimpleAgent] Max turns reached.")
    return "Max turns reached without final answer."

def run_orchestrated_agent(user_input: str, use_critic: bool = True, max_turns: int = 10):
    """Run agent with planning and critic layers using native tool calls."""

    # --- Trivial intent guard (from Step 1.1) ---
    trivial_greetings = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'say hello']
    if any(greeting in user_input.lower() for greeting in trivial_greetings):
        response = "Hello! How can I help you today?"
        print(response)
        log_to_file(f"[Trivial guard] Responded with: {response}")
        return response

    # --- Complexity classification (from Step 1.2) ---
    category = classify_request(user_input)
    print(f"[Complexity] Category: {category}")
    log_to_file(f"[Complexity] Category: {category}")

    if category == 'direct':
        direct_prompt = f"Answer directly and concisely: {user_input}"
        response = deepseek_consult(prompt=direct_prompt, timeout=20)
        print(response)
        log_to_file(f"[Direct answer] {response}")
        return response
    elif category == 'simple':
        return run_simple_tool_agent(user_input, max_turns)

    # --- Complex path (planner/critic) ---
    print(f"Session log: {LOG_FILE}")
    log_to_file(f"\n{'='*50}\nNew session: {user_input}\n{'='*50}\n")

    session_work_dir = SESSIONS_DIR / LOG_FILE.stem
    session_work_dir.mkdir(exist_ok=True)

    llm = ChatOllama(model="qwen2.5:7b", temperature=0.2, num_predict=4000)
    bound_llm = llm.bind_tools(TOOLS)

    planner = None
    critic = None
    plan_data = None

    if use_critic:
        planner = Planner(session_work_dir, TOOLS)
        plan = planner.create_plan(user_input)
        critic = Critic(user_input)
        plan_data = planner.load_plan()

    messages = [{"role": "user", "content": user_input}]

    for turn in range(max_turns):
        # Build system prompt (optional – you can keep or remove)
        tool_desc = "\n".join([
            f"- {t['function']['name']}: {t['function'].get('description', 'No description')}"
            for t in TOOLS
        ])

        plan_context = ""
        if use_critic and plan_data:
            current_goal = planner.get_current_goal(plan_data)
            if current_goal:
                plan_context = f"\nCurrent sub‑goal: {current_goal}\n"

        # We'll include the context in the messages, not as a separate system prompt,
        # because the model already has the conversation. Optionally, we can insert a system message.
        # For simplicity, we'll just use the existing messages and rely on the model's memory.

        response = bound_llm.invoke(messages)

        if hasattr(response, 'tool_calls') and response.tool_calls:
            # Execute the first tool call (simplify; could handle multiple)
            tool_call = response.tool_calls[0]
            name = tool_call['name']
            args = tool_call.get('args', {})
            print(f"[Complex] Executing tool: {name} with args: {args}")

            if name not in TOOL_MAP:
                result = f"Error: Unknown tool '{name}'"
            else:
                try:
                    result = TOOL_MAP[name](**args)
                except Exception as e:
                    result = f"Error executing {name}: {e}"

            # Append tool result as a tool message
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get('id', ''),
                "content": str(result)
            })

            # Critic evaluation (if enabled)
            if use_critic and plan_data and critic:
                tool_results = critic.extract_tool_results(messages)
                status, guidance, revised_plan = critic.evaluate(
                    plan_data["plan"],
                    plan_data["current"],
                    plan_data["completed"],
                    response.content,
                    tool_results
                )

                if status == "complete":
                    plan_data["completed"].append(plan_data["current"])
                    plan_data["current"] += 1
                    planner.update_plan(plan_data)
                    messages.append({"role": "system", "content": guidance})

                    if planner.is_complete(plan_data):
                        print("\n[Planner] All sub‑goals complete.")
                elif status == "replan" and revised_plan:
                    plan_data = {"plan": revised_plan, "current": 0, "completed": []}
                    planner.update_plan(plan_data)
                    messages.append({"role": "system", "content": guidance})
                else:
                    messages.append({"role": "user", "content": guidance})

            continue  # next turn

        else:
            # No tool calls – final answer (or we need to ask for more)
            # Could also be the model requesting clarification.
            print(f"\n[Complex] Final: {response.content[:200]}...")
            return response.content

    print(f"\nReached max turns ({max_turns})")
    return messages[-1]["content"] if messages else "No response"

def main():
    parser = argparse.ArgumentParser(description='Orchestrated Agent with planner/critic')
    parser.add_argument('prompt', nargs='?', help='User request')
    parser.add_argument('--no-critic', action='store_true', help='Disable planner/critic layer')
    parser.add_argument('--max-turns', type=int, default=10, help='Maximum turns')
    args = parser.parse_args()
    
    if args.prompt:
        user_input = args.prompt
    else:
        user_input = input("Enter your request: ")
    
    run_orchestrated_agent(
        user_input,
        use_critic=not args.no_critic,
        max_turns=args.max_turns
    )


if __name__ == "__main__":
    main()