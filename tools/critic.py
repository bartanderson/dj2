#!/usr/bin/env python3
"""
Critic module — evaluates agent progress and suggests corrections or replanning.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from tools.agent_tools import deepseek_consult


class Critic:
    """Evaluates progress against sub-goals and guides next actions."""
    
    def __init__(self, user_input: str, verbose: bool = True):
        self.user_input = user_input
        self.verbose = verbose
    
    def _log(self, message: str):
        if self.verbose:
            print(f"[Critic] {message}")
    
    def evaluate(
        self,
        plan: List[str],
        current_idx: int,
        completed: List[int],
        assistant_message: str,
        tool_results: List[str]
    ) -> Tuple[str, Optional[str], Optional[List[str]]]:
        """
        Evaluate current progress and return (status, guidance, revised_plan).
        
        Status: 'complete', 'incomplete', 'blocked', or 'replan'
        Guidance: next step description or system message
        Revised_plan: new list of sub-goals if replanning triggered
        """
        current_goal = plan[current_idx] if current_idx < len(plan) else None
        
        critic_prompt = f"""You are a critic reviewing an AI assistant's progress. The original user query: "{self.user_input}"

The current plan:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(plan))}

The assistant is currently working on sub‑goal {current_idx+1}: "{current_goal}"

The assistant's last message:
{assistant_message}

Tool results received:
{chr(10).join(tool_results) if tool_results else "No tool results yet."}

Your task:
- Determine if the current sub‑goal is complete.
- If not, what specific information is still missing?
- Suggest the next tool call(s) that would help complete this sub‑goal.
- If the sub‑goal is complete, indicate that we should move to the next one.
- If the entire plan is misguided, suggest a revised plan.

Output in this format:
STATUS: [complete / incomplete / blocked / replan]
NEXT_STEP: (if incomplete) a brief description of what's needed
TOOL_SUGGESTIONS: (if incomplete) one or more <tool> tags on separate lines
MOVE_TO_NEXT: [yes/no] (only if STATUS is complete)
REVISED_PLAN: (if replan) a new numbered list of sub‑goals
"""
        
        self._log("Evaluating...")
        response = deepseek_consult(prompt=critic_prompt, timeout=60)
        self._log(f"Response:\n{response}\n")
        
        # Parse response
        status = self._extract_status(response)
        
        if status == "complete" and "MOVE_TO_NEXT: yes" in response:
            return "complete", self._advance_message(plan, current_idx), None
        
        elif status == "replan" and "REVISED_PLAN:" in response:
            revised = self._extract_revised_plan(response)
            if revised:
                return "replan", "The plan has been revised. Start with the first new sub‑goal.", revised
        
        elif status == "incomplete":
            return "incomplete", f"Critic suggests: {response}", None
        
        else:
            # Blocked or unparseable — return raw for agent to handle
            return "blocked", f"Critic feedback: {response}", None
    
    def _extract_status(self, response: str) -> str:
        """Parse STATUS field from critic response."""
        for line in response.split('\n'):
            if line.startswith('STATUS:'):
                return line.replace('STATUS:', '').strip().lower()
        return "incomplete"  # Default
    
    def _extract_revised_plan(self, response: str) -> Optional[List[str]]:
        """Extract new numbered list after REVISED_PLAN marker."""
        if "REVISED_PLAN:" not in response:
            return None
        
        revised_part = response.split("REVISED_PLAN:")[1].strip()
        lines = [line.strip() for line in revised_part.split('\n') if line.strip()]
        
        new_plan = []
        for line in lines:
            if line and line[0].isdigit() and '. ' in line:
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    new_plan.append(parts[1])
        
        return new_plan if new_plan else None
    
    def _advance_message(self, plan: List[str], current_idx: int) -> str:
        """Generate guidance message for advancing to next goal or finishing."""
        next_idx = current_idx + 1
        if next_idx < len(plan):
            return f"Good. Now proceed to sub‑goal {next_idx+1}: {plan[next_idx]}"
        else:
            return "All sub‑goals are complete. Please provide a final answer to the user."
    
    def extract_tool_results(self, messages: List[Dict[str, str]]) -> List[str]:
        """Extract tool result messages from recent history."""
        results = []
        for msg in reversed(messages):
            if msg.get("role") == "tool":
                results.append(msg["content"])
            else:
                break
        results.reverse()
        return results