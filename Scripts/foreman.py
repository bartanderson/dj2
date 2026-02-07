# foreman.py - One file, testable pieces

from pathlib import Path
import json
import subprocess
import pickle
import re
from dataclasses import dataclass
from typing import Dict, Any


# === PIECE A: Config Loader ===
class ConfigLoader:
    def __init__(self, ai_context_path: Path):
        self.path = ai_context_path
        self.tools = {}
        self.status = {}

    def list_tools(self) -> list:
        """Return flat list of all tool names."""
        tools = []
        for category, items in self.tools.items():
            if isinstance(items, dict):
                tools.extend(items.keys())
        return tools
    
    def load(self):
        tools_file = self.path / "tool_index.json"
        if tools_file.exists():
            self.tools = json.loads(tools_file.read_text())
        
        status_file = self.path / "status_manifest.json"
        if status_file.exists():
            self.status = json.loads(status_file.read_text())
    
    def get_tool(self, name: str):
        for cat, items in self.tools.items():
            if name in items:
                return items[name]
        raise KeyError(name)


# === PIECE B: Constraint Checker ===
class ConstraintChecker:
    def check(self, intent: str):
        bad = ["update state", "mutate", "direct"]
        for b in bad:
            if b in intent.lower():
                return {"ok": False, "fix": f"PROPOSAL: {intent}"}
        return {"ok": True}


# === PIECE C: Tool Runner ===
class ToolRunner:
    def __init__(self, root: Path, config: ConfigLoader):
        self.root = root
        self.config = config

    def list_tools(self):
        """Delegate to config."""
        return self.config.list_tools()
    
    def run(self, name: str, **kwargs):
        tool = self.config.get_tool(name)
        cmd = tool["windows_cmd"]
        for k, v in kwargs.items():
            cmd = cmd.replace(f"{{{k}}}", v)
        
        return subprocess.run(cmd, shell=True, cwd=self.root, 
                            capture_output=True, text=True)


# === PIECE D: DeepSeek Connector ===
class DeepSeek:
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.last_error = None
    
    def ask(self, prompt: str):
        """Send prompt to DeepSeek via your bridge_controller."""
        # Method 1: Try importing bridge_controller directly
        try:
            import sys
            from tools.bridge.bridge_controller import BridgeController
            
            b = BridgeController()
            result = b.ask_deepseek(prompt)
            if result:
                return result
            else:
                self.last_error = "Bridge returned empty response"
                return f"[DeepSeek error: {self.last_error}]"
                
        except ImportError as e:
            self.last_error = f"Cannot import bridge_controller: {e}"
            return f"[DeepSeek error: {self.last_error}]"
        except Exception as e:
            self.last_error = f"Bridge failed: {e}"
            return f"[DeepSeek error: {self.last_error}]"


# === PIECE E: Session Memory ===
class Session:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
    
    def save(self, data):
        with open(self.path / "last.pkl", 'wb') as f:
            pickle.dump(data, f)
    
    def load(self):
        try:
            with open(self.path / "last.pkl", 'rb') as f:
                return pickle.load(f)
        except:
            return None


# === FOREMAN: Pieces Wired Together ===
class Foreman:
    def __init__(self):
        self.root = Path("C:/Users/bartl/dev/dj2")
        self.ai = self.root / "ai_context"
        
        # Pieces
        self.config = ConfigLoader(self.ai)
        self.checker = ConstraintChecker()
        self.session = Session(self.ai / "session")
        
        # Pieces that need init
        self.tools = None
        self.deepseek = None
    
    def start(self):
        """Turn on pieces."""
        self.config.load()
        self.tools = ToolRunner(self.root, self.config)
        self.deepseek = DeepSeek(self.config)
        return "Ready"
    
#     def orchestrate(self, goal: str, auto: bool = False):
#         """
#         Orchestrate work on a goal: DeepSeek directs, Foreman executes.
        
#         Args:
#             goal: What to work on (stored as instance state for access by sub-methods)
#             auto: If True, don't ask for approval each step
#         """
#         # Store goal as instance state so _gather_context and other methods can access it
#         # without passing it through every call chain
#         self.current_goal = goal
        
#         print(f"\n=== ORCHESTRATING: {goal} ===")
        
#         # Gather context using the stored goal
#         context = self._gather_context()
        
#         # Step 2: Ask DeepSeek for plan
#         plan_prompt = f"""
# Goal: {goal}

# Current project status:
# {context}

# Available tools: {', '.join(self.tools.list_tools()[:10])}

# Create a step-by-step plan using ONLY these formats:
# 1. tool <tool_name> arg=value arg2=value2
# 2. ask "question for deepseek"

# Example:
# 1. tool four_layer topic={goal}
# 2. tool violations path=.
# 3. ask "What should I fix first?"

# Respond with numbered steps only. No extra text. No descriptions. Just commands.
# """
#         plan_text = self.deepseek.ask(plan_prompt)
#         print(f"\nDeepSeek plan:\n{plan_text}")
        
#         # Step 3: Parse and execute steps
#         steps = self._parse_plan(plan_text)

#         step_results = []  # To store the results of each step
        
#         for i, step in enumerate(steps, 1):
#             print(f"\n--- Step {i}/{len(steps)}: {step} ---")
            
#             # Check constraints
#             check = self.checker.check(str(step))
#             if not check["ok"]:
#                 print(f"BLOCKED: {check['fix']}")
#                 if not auto:
#                     fix = input("Proceed with fix? [y/n]: ")
#                     if fix != 'y':
#                         break
#                 step = check['fix']
            
#             # Execute
#             if not auto:
#                 proceed = input("Execute? [y/n/skip]: ")
#                 if proceed == 'skip':
#                     continue
#                 if proceed != 'y':
#                     break
            
#             result = self._execute_step(step)
#             print(f"Result: {result[:200]}...")
            
#             # Save progress
#             self.session.save({
#                 "goal": goal,
#                 "step": i,
#                 "action": str(step),
#                 "result": result[:500]
#             })
        
#         print(f"\n=== DONE: {goal} ===")
#         return f"Completed {len(steps)} steps"

    def orchestrate(self, goal: str, auto: bool = False):
        """
        Orchestrate work on a goal: DeepSeek directs, Foreman executes.
        
        Args:
            goal: What to work on (stored as instance state for access by sub-methods)
            auto: If True, don't ask for approval each step
        """
        # Store goal as instance state so _gather_context and other methods can access it
        # without passing it through every call chain
        self.current_goal = goal
        
        print(f"\n=== ORCHESTRATING: {goal} ===")
        
        # Gather context using the stored goal
        context = self._gather_context()
        
        # Step 2: Ask DeepSeek for plan
        plan_prompt = f"""
Goal: {goal}

Current project status:
{context}

Available tools: {', '.join(self.tools.list_tools()[:10])}

Create a step-by-step plan using ONLY these formats:
1. tool <tool_name> arg=value arg2=value2
2. ask "question for deepseek"

Example:
1. tool four_layer topic={goal}
2. tool violations path=.
3. ask "What should I fix first?"

Respond with numbered steps only. No extra text. No descriptions. Just commands.
"""
        plan_text = self.deepseek.ask(plan_prompt)
        print(f"\nDeepSeek plan:\n{plan_text}")
        
        # Step 3: Parse and execute steps
        steps = self._parse_plan(plan_text)
        
        # Collect all results for context
        all_results = []
        
        for i, step in enumerate(steps, 1):
            print(f"\n--- Step {i}/{len(steps)}: {step} ---")
            
            # Check constraints
            check = self.checker.check(str(step))
            if not check["ok"]:
                print(f"BLOCKED: {check['fix']}")
                if not auto:
                    fix = input("Proceed with fix? [y/n]: ")
                    if fix != 'y':
                        break
                step = check['fix']
            
            # Execute
            if not auto:
                proceed = input("Execute? [y/n/skip]: ")
                if proceed == 'skip':
                    continue
                if proceed != 'y':
                    break
            
            # Handle ask steps specially - include previous results
            if step.lower().startswith('ask '):
                question = step[4:].strip('"\'')
                # Build context from all previous results
                if all_results:
                    context_summary = "\n\n".join([f"Step {j+1}: {result[:200]}..." for j, result in enumerate(all_results)])
                    full_question = f"Previous steps results:\n{context_summary}\n\nQuestion: {question}"
                    result = self.deepseek.ask(full_question)
                else:
                    result = self.deepseek.ask(question)
            else:
                result = self._execute_step(step)
            
            all_results.append(result)
            print(f"Result: {result[:200]}...")
            
            # Save progress
            self.session.save({
                "goal": goal,
                "step": i,
                "action": str(step),
                "result": result[:500]
            })
        
        print(f"\n=== DONE: {goal} ===")
        return f"Completed {len(steps)} steps"
    
    def _gather_context(self) -> str:
        """
        Build context for DeepSeek using self.current_goal.
        
        Why instance state: Multiple methods may need the current goal (gather, resume, 
        status checks). Storing once avoids passing goal through 3+ layers of calls.
        """
        # Retrieve goal from instance state (set by orchestrate)
        goal = getattr(self, 'current_goal', 'Unknown')
        
        parts = [f"Goal: {goal}"]
        
        # Use four_layer for deep analysis
        try:
            from tools.ai_assistant.four_layer import FourLayerAnalyzer
            analyzer = FourLayerAnalyzer()  # Auto-indexer works now
            analysis = analyzer.analyze_for_context(goal)
            
            synth = analysis.get('layer4_synthesis', {})
            parts.append(f"Status: {synth.get('summary', 'Unknown')}")
            parts.append(f"Recommendations: {synth.get('recommendations', [])}")
        except Exception as e:
            parts.append(f"Analysis error: {e}")
        
        # Quick violations check
        try:
            v = self.tools.run("violations", path=".")
            v_lines = v.stdout.strip().split('\n') if v.success else []
            parts.append(f"Violations: {len(v_lines)} found")
        except:
            pass
        
        return '\n'.join(parts)
    
    def _parse_plan(self, plan_text: str) -> list:
        """Parse DeepSeek's plan into steps. Handles numbered or unnumbered."""
        steps = []
        for line in plan_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Try numbered format: "1. tool ..."
            match = re.match(r'^\d+\.\s*(.+)$', line)
            if match:
                steps.append(match.group(1))
            elif line.startswith('tool ') or line.startswith('ask '):
                # Unnumbered but valid command
                steps.append(line)
            # else: skip unknown lines
        
        return steps if steps else [plan_text]  # Fallback
    
    # def _execute_step(self, step: str) -> str:
    #     """Execute with exact match first, fuzzy fallback."""
    #     step = step.strip()
    #     step_lower = step.lower()
    #     parts = step.split(maxsplit=1)
    #     tool_name = parts[0] if parts else ""
    #     args_str = parts[1] if len(parts) > 1 else ""

    #     # DEBUG: Show what tools are available
    #     available_tools = self.tools.list_tools()
    #     print(f"  [DEBUG: tool_name='{tool_name}', available={len(available_tools)}, has_four_layer={'four_layer' in available_tools}]")
        
    #     # EXACT MATCH FIRST
    #     if tool_name in self.tools.list_tools():
    #         kwargs = {}
    #         for arg in args_str.split():
    #             if '=' in arg:
    #                 k, v = arg.split('=', 1)
    #                 kwargs[k] = v.strip('"\'')
    #         try:
    #             result = self.tools.run(tool_name, **kwargs)
    #             return result.stdout if result.returncode == 0 else result.stderr
    #         except Exception as e:
    #             return f"Tool '{tool_name}' error: {e}"
        
    #     # FUZZY MATCH: Fallback only if exact not found
    #     if "extraction" in step_lower or "analysis" in step_lower:
    #         # Extract topic from various patterns
    #         topic_match = re.search(r'target=(\w+)|topic=(\w+)|"([^"]+)"', step)
    #         topic = topic_match.group(1) or topic_match.group(2) or topic_match.group(3) if topic_match else "unknown"
            
    #         print(f"  [Interpreted as: tool four_layer topic={topic}]")
    #         try:
    #             result = self.tools.run("four_layer", topic=topic)
    #             return result.stdout if result.returncode == 0 else result.stderr
    #         except Exception as e:
    #             return f"Four layer error: {e}"
        
    #     # Fuzzy match: search query
    #     if "search" in step.lower() and "query=" in step.lower():
    #         query_match = re.search(r'query="([^"]+)"|query=(\S+)', step)
    #         query = query_match.group(1) or query_match.group(2) if query_match else step
            
    #         print(f"  [Interpreted as: tool search query={query}]")
    #         try:
    #             result = self.tools.run("search", query=query, limit="5")
    #             return result.stdout if result.returncode == 0 else result.stderr
    #         except Exception as e:
    #             return f"Search error: {e}"
        
    #     # Fuzzy match: code_search specifically
    #     if "code_search" in step.lower():
    #         query_match = re.search(r'query="([^"]+)"|query=(\S+)', step)
    #         query = query_match.group(1) or query_match.group(2) if query_match else "GameEngine"
            
    #         print(f"  [Interpreted as: tool code_search query={query}]")
    #         try:
    #             result = self.tools.run("code_search", query=query, limit="5")
    #             return result.stdout if result.returncode == 0 else result.stderr
    #         except Exception as e:
    #             return f"Code search error: {e}"
        
    #     # Check if it's an ask
    #     if step.lower().startswith('ask '):
    #         question = step[4:].strip('"\'')
    #         return self.deepseek.ask(question)
        
    #     # Unknown
    #     return f"Don't know how to: {step[:50]}..."

    def _execute_step(self, step: str) -> str:
        """Execute a single step from plan."""
        step = step.strip()
        step_lower = step.lower()
        
        # Check if it's an ask command
        if step_lower.startswith('ask '):
            question = step[4:].strip('"\'')
            return self.deepseek.ask(question)
        
        # Check if it's a tool command
        if step_lower.startswith('tool '):
            # Remove "tool " prefix
            command = step[5:].strip()
            # Split into tool name and arguments
            parts = command.split(maxsplit=1)
            tool_name = parts[0] if parts else ""
            args_str = parts[1] if len(parts) > 1 else ""
        else:
            # Not a recognized command format
            return f"Unknown command format: {step[:50]}..."
        
        # DEBUG: Show what tools are available
        available_tools = self.tools.list_tools()
        print(f"  [DEBUG: tool_name='{tool_name}', available={len(available_tools)}, has_four_layer={'four_layer' in available_tools}]")
        
        # EXACT MATCH FIRST
        if tool_name in available_tools:
            kwargs = {}
            # Parse arguments (key=value pairs)
            if args_str:
                for arg in args_str.split():
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        kwargs[k] = v.strip('"\'')
            try:
                result = self.tools.run(tool_name, **kwargs)
                return result.stdout if result.returncode == 0 else result.stderr
            except Exception as e:
                return f"Tool '{tool_name}' error: {e}"
        
        # FUZZY FALLBACK: Only if exact not found
        if "extraction" in step_lower or "analysis" in step_lower:
            # Extract topic from various patterns
            topic_match = re.search(r'target=(\w+)|topic=(\w+)|"([^"]+)"', step)
            topic = topic_match.group(1) or topic_match.group(2) or topic_match.group(3) if topic_match else "unknown"
            
            print(f"  [Interpreted as: tool four_layer topic={topic}]")
            try:
                result = self.tools.run("four_layer", topic=topic)
                return result.stdout if result.returncode == 0 else result.stderr
            except Exception as e:
                return f"Four layer error: {e}"
        
        if "search" in step_lower and "query=" in step_lower:
            query_match = re.search(r'query="([^"]+)"|query=(\S+)', step)
            query = query_match.group(1) or query_match.group(2) if query_match else step
            
            print(f"  [Interpreted as: tool search query={query}]")
            try:
                result = self.tools.run("search", query=query, limit="5")
                return result.stdout if result.returncode == 0 else result.stderr
            except Exception as e:
                return f"Search error: {e}"
        
        if "code_search" in step_lower:
            query_match = re.search(r'query="([^"]+)"|query=(\S+)', step)
            query = query_match.group(1) or query_match.group(2) if query_match else "GameEngine"
            
            print(f"  [Interpreted as: tool code_search query={query}]")
            try:
                result = self.tools.run("code_search", query=query, limit="5")
                return result.stdout if result.returncode == 0 else result.stderr
            except Exception as e:
                return f"Code search error: {e}"
        
        # Unknown
        return f"Tool '{tool_name}' not found and no fuzzy match."

if __name__ == "__main__":
    import sys
    
    f = Foreman()
    f.start()
    
    if len(sys.argv) > 1:
        # Command mode: python foreman.py "work on EventSystem"
        goal = " ".join(sys.argv[1:])
        f.orchestrate(goal, auto=False)
    else:
        # Interactive mode
        print("Foreman orchestrator ready.")
        print("Commands: 'work <goal>' or 'tool <name>' or 'ask <question>'")
        
        while True:
            try:
                cmd = input("\n> ").strip()
                if cmd in ["quit", "q"]:
                    break
                
                if cmd.startswith("work "):
                    f.orchestrate(cmd[5:], auto=False)
                elif cmd.startswith("tool "):
                    print(f.do(cmd))  # Use old direct method
                elif cmd.startswith("ask "):
                    print(f.deepseek.ask(cmd[4:]))
                else:
                    print("Unknown. Use: work <goal>, tool <name>, ask <question>")
                    
            except KeyboardInterrupt:
                break