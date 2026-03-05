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

from tools import agent_tools   # this registers tools
from tools.tool_registry import get_all_tools, get_tool_schema_override
from tools.tool_utils import function_to_tool_schema
from tools.planner import Planner
from tools.critic import Critic


USE_OLLAMA_FOR_LIGHT_TASKS = True

os.environ['NODE_NO_WARNINGS'] = '1'
logging.getLogger('deepseek_lib').setLevel(logging.WARNING)
#logging.getLogger('langchain').setLevel(logging.WARNING)
#logging.getLogger('httpcore').setLevel(logging.WARNING)

KNOWLEDGE_TOOLS = {"arch_context", "analyze_tools", "semantic_search", "deepseek_consult"}

# Build TOOLS list and TOOL_MAP from registry
TOOLS = []
TOOL_MAP = {}
for name, func in get_all_tools():
    schema_override = get_tool_schema_override(name)
    tool_func_schema = function_to_tool_schema(func, schema_override)
    TOOLS.append({"type": "function", "function": tool_func_schema})
    TOOL_MAP[name] = func

# Keep TOOL_FUNCTIONS for convenience (if used elsewhere)
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
#LOG_FILE = None

def setup_logging(session_dir: Path, main_log_path: Path):
    """Configure a single logger with console and two file handlers."""
    logger = logging.getLogger('agent')
    # Remove any existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
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

def get_llm_for_light_tasks():
    """Return an LLM instance for lightweight tasks (classification, direct answers)."""
    if USE_OLLAMA_FOR_LIGHT_TASKS:
        from langchain_ollama import ChatOllama
        return ChatOllama(model="qwen2.5:7b", temperature=0.2, num_predict=4000)
    else:
        # Use DeepSeek via the existing consult tool (but wrapped as an LLM-like interface)
        # We can create a simple wrapper that calls deepseek_consult
        class DeepSeekWrapper:
            def invoke(self, prompt):
                from tools.agent_tools import deepseek_consult
                return type('Response', (), {'content': deepseek_consult(prompt)})()
        return DeepSeekWrapper()

def classify_request(user_input: str) -> str:
    """Determine if request is direct, simple, or complex using LLM."""
    llm = get_llm_for_light_tasks()
    prompt = f"""You are a task classifier. Determine how to handle the user request.

User: {user_input}

Choose one of:
- direct: The request is a simple greeting or a question that can be answered immediately without any tools or analysis. (e.g., "say hello", "what's 2+2?", "thanks")
- simple: The request can be fulfilled by a single tool call without needing a multi‑step plan. (e.g., "read file character_builder.py", "list all Python files", "search for concept movement")
- complex: The request requires multiple steps, analysis, or planning. (e.g., "analyze the codebase", "generate a test for character creation", "compare two files")

Output only the category word.
"""
    try:
        response = llm.invoke(prompt)
        category = response.content.strip().lower()
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

    # Load or create thread ID
    thread_id_file = session_dir / "thread_id.txt"
    if thread_id_file.exists():
        thread_id = thread_id_file.read_text().strip()
    else:
        thread_id = f"thread_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        thread_id_file.write_text(thread_id)

    # Build system prompt with knowledge base instructions
    system_message = f"""You are an AI assistant with access to tools. Your goal is to answer the user's request: "{user_input}"

You have access to a persistent knowledge base that stores results from previous tool runs. Before running any expensive tool (like `arch_context`, `analyze_tools`, `semantic_search`, or `deepseek_consult`), you should first check if relevant information already exists by using `retrieve_knowledge` with appropriate keywords or thread ID.

Each analysis session has a thread ID: {thread_id}. Tools that generate new knowledge (like `arch_context`) will automatically store their results with this thread ID, so you can refer back to them later.

When you need to read files, **use `read_files`** – it accepts a single file path (as a string) or a list of paths. Using `read_files` is more efficient than multiple `read_file` calls. Avoid `read_file` unless you have a specific reason; `read_files` is the preferred tool for reading files.

When you read a file using `read_files`, you will receive one or more `SAVED_FILE:` lines with paths to the saved content. **You must then call `deepseek_consult` with the `file` parameter set to that path** and an appropriate prompt (e.g., "Analyze this file for phase compliance"). Do not attempt to answer based on the raw file content alone – always use `deepseek_consult` for deep architectural analysis.

**Critical rules:**
- Follow the plan step by step. After completing a step, move to the next.
- If the critic provides `TOOL_SUGGESTIONS`, you must execute those tools in your next turn unless they have already been executed. Do not provide a final answer while the current sub‑goal is incomplete.
- If a tool call fails, do not give up. Use the critic's guidance to correct the approach.

Available tools: {', '.join([t['function']['name'] for t in TOOLS])}

Now begin..
"""
    messages = [{"role": "system", "content": system_message}, {"role": "user", "content": user_input}]

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

def run_orchestrated_agent(user_input: str, use_critic: bool = True, max_turns: int = 30):
    """Run agent with planning and critic layers using native tool calls."""
    global LOG_FILE  # we will still use a global, but it will point inside session dir

    # --- Create session directory and main log file ---
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    session_work_dir = SESSIONS_DIR / f"agent_session_{timestamp}"
    session_work_dir.mkdir(parents=True, exist_ok=True)
    LOG_FILE = session_work_dir / f"agent_session_{timestamp}.log"

    # Set up logging (for complex path; simple path will also have logger)
    logger = setup_logging(session_work_dir, LOG_FILE)

    # --- Complexity classification ---
    category = classify_request(user_input)
    print(f"[Complexity] Category: {category}")

    if category == 'direct':
        llm = get_llm_for_light_tasks()
        direct_prompt = f"Answer directly and concisely: {user_input}"
        response = llm.invoke(direct_prompt)
        print(response)
        return response
    elif category == 'simple':
        # Simple agent already receives session_dir
        return run_simple_tool_agent(user_input, session_work_dir, max_turns)

    # --- Complex path ---
    session_work_dir = SESSIONS_DIR / LOG_FILE.stem
    session_work_dir.mkdir(exist_ok=True)

    # Load or create thread ID for knowledge base
    thread_id_file = session_work_dir / "thread_id.txt"
    if thread_id_file.exists():
        thread_id = thread_id_file.read_text().strip()
    else:
        thread_id = f"thread_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        thread_id_file.write_text(thread_id)
    logger.info(f"Thread ID: {thread_id}")

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
            if name in KNOWLEDGE_TOOLS:
                args["thread_id"] = thread_id
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
            # Save full final answer to a file
            final_file = session_work_dir / 'final_answer.txt'
            final_file.write_text(final, encoding='utf-8')
            logger.info(f"Full final answer saved to {final_file}")
            logger.info(f"Final (truncated): {final[:200]}...")
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