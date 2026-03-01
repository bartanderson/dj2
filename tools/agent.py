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
import datetime
import argparse
from pathlib import Path

# Build TOOLS list from available tool functions for planner compatibility
# These are the tools exported by agent_tools that are in TOOL_WHITELIST
from tools import agent_tools
from tools.default_tools import TOOL_WHITELIST
from langchain_ollama import ChatOllama
from tools.planner import Planner
from tools.critic import Critic
from tools.agent_tools import deepseek_consult

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

def get_or_create_session_dir():
    session_dir = project_root / "ai_context" / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir

# Setup session log with timestamp
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
session_dir = get_or_create_session_dir()
LOG_FILE = session_dir / f"agent_session_{timestamp}.log"  

def log_to_file(entry):
    """Append entry to log file with timestamp."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}]\n{entry}\n\n")

def run_orchestrated_agent(user_input: str, use_critic: bool = True, max_turns: int = 10):
    """Run agent with planning and critic layers."""
    
    # Setup
    session_dir = get_or_create_session_dir()
    print(f"Session: {session_dir}")
    log_to_file(f"\n{'='*50}\nNew session: {user_input}\n{'='*50}\n")
    
    # Initialize LLM
    llm = ChatOllama(model="mistral:7b", temperature=0.2, num_predict=4000)
    
    # Planning phase (if critic enabled)
    planner = None
    critic = None
    plan_data = None
    
    if use_critic:
        planner = Planner(session_dir, TOOLS)
        plan = planner.create_plan(user_input)
        
        critic = Critic(user_input)
        plan_data = planner.load_plan()
    
    # Execution loop
    messages = [{"role": "user", "content": user_input}]
    
    for turn in range(max_turns):
        # Build prompt with tool definitions
        tool_desc = "\n".join([
            f"<tool>{t['function']['name']}</tool> — {t['function'].get('description', 'No description')}"
            for t in TOOLS
        ])
        
        # Add plan context if using critic
        plan_context = ""
        if use_critic and plan_data:
            current_goal = planner.get_current_goal(plan_data)
            if current_goal:
                plan_context = f"\nCurrent sub-goal: {current_goal}\n"
        
        prompt = f"""You are an AI assistant with tools. Respond with <tool>name</tool> to use a tool.

Available tools:
{tool_desc}
{plan_context}

History:
{json.dumps(messages, indent=2)}

Respond with tool calls or final answer."""
        
        # Get LLM response
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, 'content') else str(response)
        messages.append({"role": "assistant", "content": text})
        
        # Parse tool calls
        tool_calls = re.findall(r'<tool>(\w+)</tool>', text)
        
        if tool_calls:
            # Execute tools
            for tool_name in tool_calls:
                if tool_name not in TOOL_MAP:
                    result = f"Error: Unknown tool '{tool_name}'"
                else:
                    try:
                        result = TOOL_MAP[tool_name](user_input)
                    except Exception as e:
                        result = f"Error executing {tool_name}: {e}"
                
                messages.append({"role": "user", "content": f"TOOL_RESULT: {result}"})
                print(f"Executed {tool_name}: {str(result)[:100]}...")
            
            # Critic evaluation (if enabled)
            if use_critic and plan_data and critic:
                tool_results = critic.extract_tool_results(messages)
                
                status, guidance, revised_plan = critic.evaluate(
                    plan_data["plan"],
                    plan_data["current"],
                    plan_data["completed"],
                    text,
                    tool_results
                )
                
                if status == "complete":
                    # Advance to next sub-goal
                    plan_data["completed"].append(plan_data["current"])
                    plan_data["current"] += 1
                    planner.update_plan(plan_data)
                    messages.append({"role": "system", "content": guidance})
                    
                    # Check if fully complete
                    if planner.is_complete(plan_data):
                        print("\n[Planner] All sub-goals complete.")
                        # Continue to let agent provide final answer
                        
                elif status == "replan" and revised_plan:
                    # Reset with new plan
                    plan_data = {
                        "plan": revised_plan,
                        "current": 0,
                        "completed": []
                    }
                    planner.update_plan(plan_data)
                    messages.append({"role": "system", "content": guidance})
                    
                else:
                    # Incomplete or blocked — inject critic feedback
                    messages.append({"role": "user", "content": guidance})
            
            continue  # Next turn
        
        # No tool calls — check if final answer
        if not re.search(r'<tool>', text):
            print(f"\nFinal: {text[:200]}...")
            return text
    
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