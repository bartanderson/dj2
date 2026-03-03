#!/usr/bin/env python3
"""
Orchestrated Agent — agent with planner/critic layer for complex tasks.
[Usage]: python tools/agent.py "analyze the codebase"
"""

import os
import re
import sys
import json
import datetime
import argparse
import logging
from pathlib import Path
from typing import Any

from langchain_ollama import ChatOllama

from tools import agent_tools
from tools.default_tools import TOOLS
from tools.planner import Planner
from tools.critic import Critic

os.environ['NODE_NO_WARNINGS'] = '1'
logging.getLogger('deepseek_lib').setLevel(logging.WARNING)
#logging.getLogger('langchain').setLevel(logging.WARNING)
#logging.getLogger('httpcore').setLevel(logging.WARNING)

# Build TOOL_MAP from TOOLS and agent_tools
TOOL_MAP = {}
for tool_def in TOOLS:
    name = tool_def['function']['name']
    if hasattr(agent_tools, name):
        TOOL_MAP[name] = getattr(agent_tools, name)

# For binding, we need just the function definitions (without the outer 'type')
TOOL_FUNCTIONS = [t['function'] for t in TOOLS]

# Add project root to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Constant base directory for all sessions
SESSIONS_DIR = Path('ai_context') / 'sessions'
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

def get_session_log_file() -> Path:
    """Create timestamped log file path in sessions directory."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = SESSIONS_DIR / f"agent_session_{timestamp}.log"
    return log_file

# Global log file – will be set in run_orchestrated_agent
LOG_FILE = None

def setup_logging(session_dir: Path, main_log_path: Path):
    """Configure a single logger with console and two file handlers."""
    logger = logging.getLogger('agent')
    logger.setLevel(logging.DEBUG)

    # Console handler (INFO and above) – concise format
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console_format = logging.Formatter('%(message)s')  # just the message
    console.setFormatter(console_format)
    logger.addHandler(console)

    # Main session log (INFO and above) – with timestamps
    main_handler = logging.FileHandler(main_log_path, encoding='utf-8')
    main_handler.setLevel(logging.INFO)
    main_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    main_handler.setFormatter(main_format)
    logger.addHandler(main_handler)

    # Debug log (DEBUG and above) inside session directory
    debug_log = session_dir / 'debug.log'
    debug_handler = logging.FileHandler(debug_log, encoding='utf-8')
    debug_handler.setLevel(logging.DEBUG)
    debug_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    debug_handler.setFormatter(debug_format)
    logger.addHandler(debug_handler)

    # Suppress noisy deepseek_lib logs
    logging.getLogger('deepseek_lib').setLevel(logging.WARNING)

    return logger

def classify_request(user_input: str) -> str:
    """Determine if request is direct, simple, or complex using LLM."""
    from tools.agent_tools import deepseek_consult
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
            category = 'complex'
        return category
    except Exception as e:
        print(f"[Classification error] {e}. Defaulting to complex.")
        return 'complex'

def save_tool_result(tool_name: str, result: Any, session_dir: Path) -> str:
    """
    Save full tool result to a per‑tool file in the session directory,
    append to tools.log, and return a summary message.
    """
    session_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = session_dir / f"tool_result_{tool_name}_{timestamp}.txt"
    result_str = str(result)
    # If result is a dict/list, serialize to JSON with nice formatting
    if isinstance(result, (dict, list)):
        result_str = json.dumps(result, indent=2, default=str)
    else:
        result_str = str(result)    
    result_file.write_text(result_str, encoding='utf-8')

    # Append to session‑wide tools log
    tools_log = session_dir / 'tools.log'
    with open(tools_log, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Tool: {tool_name}\n")
        f.write(f"Time: {timestamp}\n")
        f.write(f"File: {result_file.name}\n")
        f.write(f"{'='*60}\n")
        f.write(result_str)
        f.write("\n")

    # Truncated display version
    if len(result_str) > 500:
        display = result_str[:500] + f"... (truncated, total {len(result_str)} chars)"
    else:
        display = result_str

    return f"SAVED_FILE: {result_file}\nResult from {tool_name}: {display}"

def run_simple_tool_agent(user_input: str, session_dir: Path, max_turns: int = 5) -> str:
    """Run a simple agent using native tool calling."""
    logger = logging.getLogger('agent')
    logger.info(f"SimpleAgent starting with input: {user_input}")
    messages = [{"role": "user", "content": user_input}]
    llm = ChatOllama(model="qwen2.5:7b", temperature=0.2, num_predict=4000)
    bound_llm = llm.bind_tools(TOOL_FUNCTIONS)

    for turn in range(max_turns):
        logger.info(f"SimpleAgent turn {turn+1}")
        try:
            response = bound_llm.invoke(messages)
        except Exception as e:
            logger.error(f"LLM invoke failed: {e}")
            return f"Error: LLM call failed – {e}"

        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            name = tool_call['name']
            args = tool_call.get('args', {})
            logger.info(f"Executing tool: {name}")
            logger.debug(f"Full args: {args}")

            if name not in TOOL_MAP:
                result = f"Error: Unknown tool '{name}'"
                logger.error(result)
                return result

            try:
                raw_result = TOOL_MAP[name](**args)
                final_message = save_tool_result(name, raw_result, session_dir)
                logger.info(final_message.split('\n')[0])  # first line summary
                return final_message
            except Exception as e:
                result = f"Error executing {name}: {e}"
                logger.error(result)
                return result
        else:
            logger.info("No tool calls – final answer")
            return response.content

    logger.warning("Max turns reached")
    return "Max turns reached without final answer."

def run_orchestrated_agent(user_input: str, use_critic: bool = True, max_turns: int = 10):
    """Run agent with planning and critic layers using native tool calls."""
    global LOG_FILE
    LOG_FILE = get_session_log_file()

    # --- Trivial intent guard ---
    trivial_greetings = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'say hello']
    if any(greeting in user_input.lower() for greeting in trivial_greetings):
        response = "Hello! How can I help you today?"
        print(response)
        return response

    # --- Complexity classification ---
    category = classify_request(user_input)
    print(f"[Complexity] Category: {category}")

    if category == 'direct':
        from tools.agent_tools import deepseek_consult
        direct_prompt = f"Answer directly and concisely: {user_input}"
        response = deepseek_consult(prompt=direct_prompt, timeout=20)
        print(response)
        return response
    elif category == 'simple':
        # Need session_dir – create it now
        session_work_dir = SESSIONS_DIR / LOG_FILE.stem
        session_work_dir.mkdir(exist_ok=True)
        return run_simple_tool_agent(user_input, session_work_dir, max_turns)

    # --- Complex path ---
    session_work_dir = SESSIONS_DIR / LOG_FILE.stem
    session_work_dir.mkdir(exist_ok=True)

    # Set up logging
    logger = setup_logging(session_work_dir, LOG_FILE)
    logger.info(f"Session started: {user_input}")

    llm = ChatOllama(model="qwen2.5:7b", temperature=0.2, num_predict=4000)
    bound_llm = llm.bind_tools(TOOL_FUNCTIONS)

    planner = None
    critic = None
    plan_data = None

    if use_critic:
        planner = Planner(session_work_dir, TOOLS)  # planner uses full TOOLS for list
        plan = planner.create_plan(user_input)
        critic = Critic(user_input)
        plan_data = planner.load_plan()

    messages = [{"role": "user", "content": user_input}]

    for turn in range(max_turns):
        logger.info(f"Turn {turn+1}")

        if use_critic and plan_data:
            current_goal = planner.get_current_goal(plan_data)
            if current_goal:
                messages.append({"role": "system", "content": f"Current sub‑goal: {current_goal}"})

        response = bound_llm.invoke(messages)

        if hasattr(response, 'tool_calls') and response.tool_calls:
            tool_call = response.tool_calls[0]
            name = tool_call['name']
            args = tool_call.get('args', {})
            logger.info(f"Executing tool: {name}")
            logger.debug(f"Full args: {args}")

            if name not in TOOL_MAP:
                result_str = f"Error: Unknown tool '{name}'"
                logger.error(result_str)
            else:
                try:
                    raw_result = TOOL_MAP[name](**args)
                    result_str = save_tool_result(name, raw_result, session_work_dir)
                    logger.info(result_str.split('\n')[0])
                except Exception as e:
                    result_str = f"Error executing {name}: {e}"
                    logger.error(result_str)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get('id', ''),
                "content": result_str
            })

            # Critic evaluation
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
                    logger.info(f"Sub‑goal complete. Moving to next.")
                    if planner.is_complete(plan_data):
                        logger.info("All sub‑goals complete.")
                elif status == "replan" and revised_plan:
                    plan_data = {"plan": revised_plan, "current": 0, "completed": []}
                    planner.update_plan(plan_data)
                    messages.append({"role": "system", "content": guidance})
                    logger.info("Plan revised.")
                else:
                    messages.append({"role": "user", "content": guidance})
                    logger.debug(f"Critic feedback: {guidance}")

            continue

        else:
            logger.info("No tool calls – final answer")
            final = response.content
            logger.info(f"Final: {final[:200]}...")
            return final

    logger.warning(f"Max turns ({max_turns}) reached")
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