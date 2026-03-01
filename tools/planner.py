#!/usr/bin/env python3
"""
Planner module — decomposes user requests into sub-goals for agent execution.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from tools.agent_tools import deepseek_consult


class Planner:
    """Decomposes user requests into executable sub-goals."""
    
    def __init__(self, session_dir: Path, tools: List[Dict], verbose: bool = True):
        self.session_dir = session_dir
        self.tools = tools
        self.verbose = verbose
        self.plan_file = session_dir / 'plan.json'
    
    def _log(self, message: str):
        if self.verbose:
            print(f"[Planner] {message}")
    
    def create_plan(self, user_input: str) -> List[str]:
        """Generate numbered sub-goals from user request."""
        tool_names = [t['function']['name'] for t in self.tools]
        
        planner_prompt = f"""You are a planning assistant. The user asked: "{user_input}"

Available tools: {', '.join(tool_names)}

Break this task down into a sequence of concrete sub‑goals. Each sub‑goal should be something that can be achieved by calling one or more tools. Output a numbered list, each line starting with the sub‑goal number and a brief description.

Example:
1. Find all files related to the DM agent.
2. Find all files related to character creation.
3. Identify the main functions in the DM agent.
4. Identify character creation functions.
5. Trace whether any DM function calls a character creation function.
6. If not, propose missing code.

Now output the plan for the user's request.
        """
        
        self._log("Generating plan...")
        plan_response = deepseek_consult(prompt=planner_prompt, timeout=60)
        
        # Parse numbered list
        plan_lines = [line.strip() for line in plan_response.split('\n') if line.strip()]
        plan = []
        for line in plan_lines:
            if line and line[0].isdigit() and '. ' in line:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    plan.append(parts[1])
        
        if not plan:
            # Fallback: treat entire response as single step
            plan = [plan_response.strip()]
        
        # Persist plan
        self._save_plan(plan)
        self._log(f"Created plan with {len(plan)} steps.")
        
        # Display to user
        print("Plan:")
        for i, step in enumerate(plan):
            print(f"  {i+1}. {step}")
        
        return plan
    
    def _save_plan(self, plan: List[str]):
        """Save plan to session JSON."""
        with open(self.plan_file, 'w') as f:
            json.dump({
                "plan": plan,
                "current": 0,
                "completed": []
            }, f, indent=2)
    
    def load_plan(self) -> Optional[Dict[str, Any]]:
        """Load current plan state if exists."""
        if not self.plan_file.exists():
            return None
        with open(self.plan_file, 'r') as f:
            return json.load(f)
    
    def update_plan(self, plan_data: Dict[str, Any]):
        """Persist updated plan state."""
        with open(self.plan_file, 'w') as f:
            json.dump(plan_data, f, indent=2)
    
    def is_complete(self, plan_data: Dict[str, Any]) -> bool:
        """Check if all sub-goals completed."""
        return plan_data["current"] >= len(plan_data["plan"])
    
    def get_current_goal(self, plan_data: Dict[str, Any]) -> Optional[str]:
        """Get active sub-goal or None if complete."""
        idx = plan_data["current"]
        plan = plan_data["plan"]
        if idx < len(plan):
            return plan[idx]
        return None