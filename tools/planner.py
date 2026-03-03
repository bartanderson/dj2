#!/usr/bin/env python3
"""
Planner module — decomposes user requests into sub-goals for agent execution.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from tools.agent_tools import deepseek_consult

logger = logging.getLogger('agent')

class Planner:
    """Decomposes user requests into executable sub-goals."""

    def __init__(self, session_dir: Path, tools: List[Dict], verbose: bool = True):
        self.session_dir = session_dir
        self.tools = tools
        self.verbose = verbose
        self.plan_file = session_dir / 'plan.json'

    def create_plan(self, user_input: str) -> List[str]:
        """Generate numbered sub-goals from user request."""
        tool_names = [t['function']['name'] for t in self.tools]

        planner_prompt = f"""You are a planning assistant. The user asked: "{user_input}"

Available tools: {', '.join(tool_names)}

Break the request into a sequence of concrete, numbered sub‑goals. Each sub‑goal must be a single, focused step that can be achieved by calling one or more tools. Aim for 4‑8 sub‑goals.

Output only the sub‑goals, one per line. Do not include any introductory or explanatory text. For example:
Run analyze_tools to get an ecosystem overview.
Read the saved analyze_tools result file to obtain the full list of hotspot files.
For each of the top 5 hotspot files, run file_metadata and read_file.

Now output the plan for the user's request.
"""

        logger.info("Generating plan...")
        plan_response = deepseek_consult(prompt=planner_prompt, timeout=60)
        logger.debug(f"Raw plan response:\n{plan_response}")

        # Split into non‑empty lines and treat each as a step
        lines = [line.strip() for line in plan_response.split('\n') if line.strip()]
        if lines:
            # Optional: strip any leading numbers (e.g., "1. " or "1 ") if present
            # but we keep the raw lines as steps
            plan = lines
        else:
            plan = [plan_response.strip()]

        self._save_plan(plan)
        logger.info(f"Created plan with {len(plan)} steps.")
        for i, step in enumerate(plan):
            logger.info(f"  {i+1}. {step}")

        return plan
    
    def _save_plan(self, plan: List[str]):
        with open(self.plan_file, 'w') as f:
            json.dump({
                "plan": plan,
                "current": 0,
                "completed": []
            }, f, indent=2)

    def load_plan(self) -> Optional[Dict[str, Any]]:
        if not self.plan_file.exists():
            return None
        with open(self.plan_file, 'r') as f:
            return json.load(f)

    def update_plan(self, plan_data: Dict[str, Any]):
        with open(self.plan_file, 'w') as f:
            json.dump(plan_data, f, indent=2)

    def is_complete(self, plan_data: Dict[str, Any]) -> bool:
        return plan_data["current"] >= len(plan_data["plan"])

    def get_current_goal(self, plan_data: Dict[str, Any]) -> Optional[str]:
        idx = plan_data["current"]
        plan = plan_data["plan"]
        if idx < len(plan):
            return plan[idx]
        return None