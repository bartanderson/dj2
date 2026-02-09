#!/usr/bin/env python3
"""
foreman.py - Orchestration tool for AI-assisted development

Simplified version with:
- Ollama-first AI with DeepSeek fallback
- Single 'run' method for all commands
- Clean, minimal code
"""

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pickle


# ============================================================================
# CONFIG LOADER
# ============================================================================

class ConfigLoader:
    """Loads tool_index.json and status_manifest.json"""
    
    def __init__(self, ai_context_path: Path):
        self.path = ai_context_path
        self.tools = {}
        self.status = {}
    
    def load(self):
        """Load configuration files"""
        # Load tools
        tools_file = self.path / "tool_index.json"
        if tools_file.exists():
            with open(tools_file, 'r') as f:
                self.tools = json.load(f)
        
        # Load status
        status_file = self.path / "status_manifest.json"
        if status_file.exists():
            with open(status_file, 'r') as f:
                self.status = json.load(f)
    
    def list_tools(self) -> List[str]:
        """Return flat list of all tool names"""
        tool_list = []
        for category, items in self.tools.items():
            if isinstance(items, dict):
                tool_list.extend(items.keys())
        return tool_list
    
    def get_tool(self, name: str) -> Dict:
        """Get tool specification by name"""
        for category, items in self.tools.items():
            if isinstance(items, dict) and name in items:
                return items[name]
        raise KeyError(f"Tool '{name}' not found")


# ============================================================================
# CONSTRAINT CHECKER
# ============================================================================

class ConstraintChecker:
    """Simple constraint checker based on ai_contract.md"""
    
    def check(self, intent: str) -> Dict:
        """Check if intent violates constraints"""
        forbidden = ["update state", "mutate", "direct", "bypass", "skip validation"]
        
        for pattern in forbidden:
            if pattern in intent.lower():
                return {
                    "ok": False,
                    "fix": f"PROPOSAL: {intent} [AWAITING VALIDATION]"
                }
        
        return {"ok": True}


# ============================================================================
# TOOL RUNNER
# ============================================================================

class ToolRunner:
    """Executes tools from tool_index.json"""
    
    def __init__(self, root: Path, config: ConfigLoader):
        self.root = root
        self.config = config
    
    def run(self, name: str, **kwargs) -> subprocess.CompletedProcess:
        """Execute a tool with arguments"""
        tool = self.config.get_tool(name)
        cmd_template = tool.get("windows_cmd", "")
        
        if not cmd_template:
            raise ValueError(f"Tool '{name}' has no windows_cmd")
        
        # Substitute arguments
        cmd = cmd_template
        for key, val in kwargs.items():
            placeholder = f"{{{key}}}"
            if placeholder in cmd:
                # Clean the value and replace
                clean_val = str(val).strip('"\'')
                cmd = cmd.replace(placeholder, clean_val)
        
        # Execute
        return subprocess.run(
            cmd,
            shell=True,
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
    
    def list_tools(self) -> List[str]:
        """Delegate to config"""
        return self.config.list_tools()


# ============================================================================
# AI CLIENT
# ============================================================================

class AIClient:
    """
    Unified AI client with three modes:
    - "auto": Ollama first, DeepSeek fallback (default)
    - "ollama": Ollama only
    - "deepseek": DeepSeek only
    """
    
    def __init__(self, config: ConfigLoader, preference: str = "auto"):
        self.config = config
        self.preference = preference.lower()
        self.ollama_client = None
        self.deepseek_client = None
        
        print(f"[AI Client] Mode: {self.preference}")
        self._init_clients()
    
    def _init_clients(self):
        """Initialize AI backends based on preference"""
        
        # Initialize Ollama if needed
        if self.preference in ["auto", "ollama"]:
            try:
                from tools.ollama_client import get_ollama_client
                self.ollama_client = get_ollama_client()
                if self.ollama_client and self.ollama_client.is_available():
                    print("  ✓ Ollama: Available")
                else:
                    print("  ⚠ Ollama: Not running (ollama serve)")
            except Exception as e:
                print(f"  ⚠ Ollama: Failed - {e}")
        
        # Initialize DeepSeek if needed
        if self.preference in ["auto", "deepseek"]:
            try:
                from tools.bridge.bridge_controller import BridgeController
                self.deepseek_client = BridgeController()
                print("  ✓ DeepSeek: Bridge available")
            except Exception as e:
                print(f"  ⚠ DeepSeek: Failed - {e}")
    
    def ask(self, prompt: str) -> str:
        """Send prompt to AI based on preference"""
        
        # Ollama-only mode
        if self.preference == "ollama":
            if self.ollama_client and self.ollama_client.is_available():
                try:
                    return self.ollama_client.quick_chat(prompt, max_lines=100)
                except Exception as e:
                    return f"[Ollama error: {e}]"
            return "[Ollama not available]"
        
        # DeepSeek-only mode
        elif self.preference == "deepseek":
            if self.deepseek_client:
                try:
                    return self.deepseek_client.ask_deepseek(prompt) or "[DeepSeek: Empty response]"
                except Exception as e:
                    return f"[DeepSeek error: {e}]"
            return "[DeepSeek not available]"
        
        # Auto mode: Ollama first, then DeepSeek
        else:
            # Try Ollama first
            if self.ollama_client and self.ollama_client.is_available():
                try:
                    return self.ollama_client.quick_chat(prompt, max_lines=100)
                except Exception as e:
                    print(f"  Ollama failed: {e}, trying DeepSeek...")
            
            # Fallback to DeepSeek
            if self.deepseek_client:
                try:
                    return self.deepseek_client.ask_deepseek(prompt) or "[DeepSeek: Empty response]"
                except Exception as e:
                    return f"[Both AIs failed: {e}]"
            
            return "[No AI available]"
    
    def get_status(self) -> Dict:
        """Get current status of AI clients"""
        return {
            "preference": self.preference,
            "ollama_available": self.ollama_client and self.ollama_client.is_available(),
            "deepseek_available": self.deepseek_client is not None
        }


# ============================================================================
# SESSION MANAGER
# ============================================================================

@dataclass
class SessionStep:
    timestamp: str
    action: str
    result: str


@dataclass
class Session:
    id: str
    started: str
    intent: str
    steps: List[SessionStep] = field(default_factory=list)


class SessionManager:
    """Manages session persistence"""
    
    def __init__(self, session_path: Path):
        self.path = session_path
        self.path.mkdir(parents=True, exist_ok=True)
        self.current = None
    
    def start(self, intent: str) -> Session:
        """Start new session"""
        self.current = Session(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            started=datetime.now().isoformat(),
            intent=intent
        )
        self._save()
        return self.current
    
    def add_step(self, action: str, result: str):
        """Add step to current session"""
        if self.current:
            self.current.steps.append(SessionStep(
                timestamp=datetime.now().isoformat(),
                action=action,
                result=result[:500]  # Truncate long results
            ))
            self._save()
    
    def _save(self):
        """Save session to file"""
        if self.current:
            file_path = self.path / f"session_{self.current.id}.pkl"
            with open(file_path, 'wb') as f:
                pickle.dump(self.current, f)


# ============================================================================
# FOREMAN (MAIN CLASS)
# ============================================================================

class Foreman:
    """Main orchestration class"""
    
    def __init__(self, ai_preference: str = "auto"):
        self.root = Path("C:/Users/bartl/dev/dj2")
        self.ai_context = self.root / "ai_context"
        
        # Initialize components
        self.config = ConfigLoader(self.ai_context)
        self.checker = ConstraintChecker()
        self.session_manager = SessionManager(self.ai_context / "session")
        self.verbose = False
        self.ai_preference = ai_preference
        
        # These will be set in start()
        self.ai_client = None
        self.tools = None
    
    def start(self):
        """Initialize the system"""
        print("Starting Foreman...")
        self.config.load()
        self.ai_client = AIClient(self.config, preference=self.ai_preference)
        self.tools = ToolRunner(self.root, self.config)
        print("Ready!")
    
    def run(self, command: str):
        """
        Single entry point for all commands:
        - work <goal>: Full orchestration
        - tool <name> [args]: Run a single tool
        - ask <question>: Ask AI directly
        - status: Show AI status
        - help: Show help
        """
        command = command.strip()
        
        # Work command: Full orchestration
        if command.startswith("work "):
            goal = command[5:]
            return self.orchestrate(goal, verbose=self.verbose)
        
        # Tool command: Run a single tool
        elif command.startswith("tool "):
            return self._run_tool(command[5:])
        
        # Ask command: Direct AI query
        elif command.startswith("ask "):
            question = command[4:]
            response = self.ai_client.ask(question)
            
            # Save to session
            if self.session_manager.current:
                self.session_manager.add_step(f"ask: {question}", response)
            
            return response
        
        # Status command
        elif command == "status":
            status = self.ai_client.get_status()
            return json.dumps(status, indent=2)
        
        # Help command
        elif command in ["help", "?"]:
            return """
Commands:
  work <goal>           - Orchestrate work on a goal
  tool <name> [args]    - Run a single tool
  ask <question>        - Ask AI directly
  status                - Show AI status
  help                  - Show this help

Flags (when starting):
  --ollama              - Use Ollama only
  --deepseek            - Use DeepSeek only
  --auto                - Ollama first, DeepSeek fallback (default)
  --verbose             - Save detailed outputs
"""
        
        # Unknown command
        else:
            return f"Unknown command: {command}\nType 'help' for available commands."
    
    def _run_tool(self, tool_spec: str) -> str:
        """Run a tool with arguments"""
        parts = tool_spec.split()
        if not parts:
            return "Usage: tool <name> [arg=value]"
        
        tool_name = parts[0]
        kwargs = {}
        
        # Parse arguments
        for part in parts[1:]:
            if '=' in part:
                key, val = part.split('=', 1)
                kwargs[key] = val.strip('"\'')
        
        try:
            # Check constraints
            check = self.checker.check(f"run {tool_name}")
            if not check["ok"]:
                return f"Blocked: {check['fix']}"
            
            # Run tool
            result = self.tools.run(tool_name, **kwargs)
            output = result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
            
            # Save to session
            if self.session_manager.current:
                self.session_manager.add_step(f"tool: {tool_name}", output)
            
            return output
            
        except Exception as e:
            return f"Tool error: {e}"
    
    def orchestrate(self, goal: str, verbose: bool = False):
        """
        Orchestrate work on a goal
        """
        self.verbose = verbose
        
        # Start session
        self.session_manager.start(f"work: {goal}")
        
        print(f"\n=== ORCHESTRATING: {goal} ===")
        if verbose:
            print("  (Verbose mode: saving detailed outputs)")
        
        # Gather context
        context = self._gather_context()
        
        # Ask AI for plan
        plan_prompt = f"""
Goal: {goal}

Current project status:
{context}

Available tools: {', '.join(self.tools.list_tools()[:10])}

Create a step-by-step plan using ONLY these formats:
1. tool <tool_name> arg=value
2. ask "question"

Example:
1. tool four_layer topic={goal}
2. tool violations path=.
3. ask "What should I fix first?"

Respond with numbered steps only. No extra text.
"""
        print("\n📋 Getting plan from AI...")
        plan_text = self.ai_client.ask(plan_prompt)
        print(f"\nPlan:\n{plan_text}")
        
        # Parse and execute steps
        steps = self._parse_plan(plan_text)
        
        all_results = []
        for i, step in enumerate(steps, 1):
            print(f"\n--- Step {i}/{len(steps)}: {step} ---")
            
            # Ask for confirmation
            proceed = input("Execute? [y/n/skip]: ").strip().lower()
            if proceed == 'skip':
                continue
            if proceed != 'y':
                print("Stopping.")
                break
            
            # Execute step
            if step.startswith('ask '):
                question = step[4:].strip('"\'')
                # Include previous results as context
                if all_results:
                    context_summary = "\n".join([f"Step {j}: {r[:200]}..." 
                                               for j, r in enumerate(all_results, 1)])
                    full_question = f"Previous results:\n{context_summary}\n\nQuestion: {question}"
                    result = self.ai_client.ask(full_question)
                else:
                    result = self.ai_client.ask(question)
            else:
                result = self._execute_step(step)
            
            all_results.append(result)
            print(f"Result: {result[:200]}...")
            
            # Save step
            self.session_manager.add_step(step, result)
            
            # Save to file if verbose
            if verbose:
                step_file = self.ai_context / f"step_{i}_{datetime.now().strftime('%H%M%S')}.txt"
                with open(step_file, 'w', encoding='utf-8') as f:
                    f.write(f"Step: {step}\n\n")
                    f.write(result)
                print(f"  [Verbose] Saved to: {step_file}")
        
        print(f"\n✅ Done: {goal}")
        return f"Completed {len(steps)} steps"
    
    def _gather_context(self) -> str:
        """Gather current project context"""
        context = []
        
        # Get focus from status manifest
        focus = self.config.status.get('current_focus', 'Unknown')
        context.append(f"Current focus: {focus}")
        
        # Run violations check
        try:
            result = self.tools.run("violations", path=".")
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                context.append(f"Phase violations: {len(lines)} found")
        except:
            context.append("Phase violations: Could not check")
        
        return "\n".join(context)
    
    def _parse_plan(self, plan_text: str) -> List[str]:
        """Parse AI's plan into steps"""
        steps = []
        for line in plan_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Look for numbered steps: "1. tool ..." or "1. ask ..."
            match = re.match(r'^\d+\.\s*(.+)$', line)
            if match:
                steps.append(match.group(1))
            # Also accept unnumbered but valid commands
            elif line.startswith('tool ') or line.startswith('ask '):
                steps.append(line)
        
        return steps if steps else [plan_text]
    
    def _execute_step(self, step: str) -> str:
        """Execute a single step from plan"""
        # Handle tool commands
        if step.startswith('tool '):
            return self._run_tool(step[5:])
        
        # Handle ask commands (should have been caught earlier)
        if step.startswith('ask '):
            question = step[4:].strip('"\'')
            return self.ai_client.ask(question)
        
        # Unknown format
        return f"Don't know how to: {step}"


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Default settings
    ai_preference = "auto"
    verbose = False
    
    # Parse command line arguments
    args = sys.argv[1:]
    
    # Handle flags
    if "--ollama" in args:
        ai_preference = "ollama"
        args.remove("--ollama")
    elif "--deepseek" in args:
        ai_preference = "deepseek"
        args.remove("--deepseek")
    elif "--auto" in args:
        ai_preference = "auto"
        args.remove("--auto")
    
    if "--verbose" in args:
        verbose = True
        args.remove("--verbose")
    
    # Create and start Foreman
    foreman = Foreman(ai_preference=ai_preference)
    foreman.verbose = verbose
    foreman.start()
    
    # If there are arguments, run them
    if args:
        command = " ".join(args)
        result = foreman.run(command)
        if result:
            print(result)
    else:
        # Interactive mode
        print(f"\n🔧 Foreman Ready")
        print(f"   AI Mode: {ai_preference}")
        print(f"   Verbose: {verbose}")
        print("\nType 'help' for commands, 'quit' to exit")
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if user_input in ["quit", "exit", "q"]:
                    print("Goodbye!")
                    break
                
                result = foreman.run(user_input)
                if result:
                    print(result)
                    
            except KeyboardInterrupt:
                print("\nInterrupted. Type 'quit' to exit.")
            except Exception as e:
                print(f"Error: {e}")