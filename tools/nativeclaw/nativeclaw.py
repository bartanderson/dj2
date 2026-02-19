#!/usr/bin/env python3
"""
nativeclaw.py - Native Windows goal runner with capability-based tool resolution
"""

import sys
import yaml
import subprocess
import argparse
import json
import shutil
import tempfile
import os
import re
from pathlib import Path
from datetime import datetime

# Get paths relative to this file
NATIVECLAW_DIR = Path(__file__).parent
TOOLS_DIR = NATIVECLAW_DIR.parent
PROJECT_ROOT = TOOLS_DIR.parent

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

class Tool:
    """Represents a tool with declared capabilities."""
    def __init__(self, name, path):
        self.name = name
        self.path = Path(path)
        self.capabilities = self._load_capabilities()
    
    def _load_capabilities(self):
        cap_file = self.path / "tool.yaml"
        if cap_file.exists():
            try:
                data = yaml.safe_load(cap_file.read_text(encoding='utf-8'))
                # Ensure required keys exist
                if 'provides' not in data:
                    data['provides'] = []
                if 'requires' not in data:
                    data['requires'] = []
                return data
            except Exception as e:
                print(f"Error loading {cap_file}: {e}")
                return {'provides': [], 'requires': [], 'name': self.name}
        return {'provides': [], 'requires': [], 'name': self.name}

class ToolRegistry:
    """Finds and manages all tools."""
    def __init__(self, root):
        self.root = Path(root)
        self.tools = []
        self._scan_tools()
    
    def _scan_tools(self):
        # Look for tool.yaml in any subdirectory
        for cap_file in self.root.glob("**/tool.yaml"):
            tool_dir = cap_file.parent
            # Get the relative path from project root for better naming
            rel_path = tool_dir.relative_to(self.root)
            self.tools.append(Tool(str(rel_path), tool_dir))
        
        # Also scan common tool locations
        for tool_dir in [self.root / "tools", self.root / "scripts", self.root]:
            if tool_dir.exists():
                for item in tool_dir.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        # Check if it has a tool.yaml
                        if (item / "tool.yaml").exists():
                            rel_path = item.relative_to(self.root)
                            if not any(t.path == item for t in self.tools):
                                self.tools.append(Tool(str(rel_path), item))
    
    def find_tools_for(self, capability):
        """Return tools that provide this capability."""
        matches = []
        for tool in self.tools:
            for provided in tool.capabilities.get('provides', []):
                if isinstance(provided, dict):
                    if provided.get('action') == capability:
                        matches.append(tool)
                elif isinstance(provided, str):
                    if provided == capability:
                        matches.append(tool)
        return matches
    
    def find_tools_by_name(self, name):
        """Find tools by name."""
        return [t for t in self.tools if t.name == name or t.name.endswith('/' + name)]
    
    def can_fulfill(self, required_capabilities):
        """Check if we can fulfill all required capabilities."""
        missing = []
        for cap in required_capabilities:
            if not self.find_tools_for(cap):
                missing.append(cap)
        return missing
    
    def list_all_capabilities(self):
        """Return all capabilities provided by all tools."""
        caps = set()
        for tool in self.tools:
            for provided in tool.capabilities.get('provides', []):
                if isinstance(provided, dict):
                    caps.add(provided.get('action'))
                elif isinstance(provided, str):
                    caps.add(provided)
        return sorted(caps)

class CapabilityResolver:
    """Finds chains of tools to fulfill requests."""
    
    def __init__(self, registry, project_root):
        self.registry = registry
        self.root = Path(project_root)
        self.session = None
    
    def set_session(self, session):
        """Attach a session for tracking created files."""
        self.session = session
    
    def resolve(self, goal_steps):
        """Given goal steps, find tools for each."""
        plan = []
        missing = []
        
        for i, step in enumerate(goal_steps):
            action = step.get('action')
            if not action:
                missing.append(f"step_{i}_no_action")
                continue
                
            tools = self.registry.find_tools_for(action)
            
            if not tools:
                missing.append(action)
                plan.append({
                    'step': step,
                    'tools': [],
                    'selected': None,
                    'capability': None,
                    'status': 'missing'
                })
                continue

            # Pick the first tool (could be smarter later)
            tool = tools[0]
            # Find which capability provides this action
            capability = None
            for cap in tool.capabilities.get('provides', []):
                if isinstance(cap, dict) and cap.get('action') == action:
                    capability = cap
                    break
            
            plan.append({
                'step': step,
                'tools': tools,
                'selected': tool,
                'capability': capability,
                'status': 'found'
            })
        
        if missing:
            return {
                'success': False,
                'missing': missing,
                'plan': plan
            }
        
        return {
            'success': True,
            'plan': plan
        }
    
    def execute_plan(self, plan, session=None):
        """Execute the resolved plan by running actual tools."""
        if session:
            self.session = session

        results = {}
        context = {}
        failed_steps = []

        print("\n📋 Executing capability plan:")
        print("="*60)

        for i, item in enumerate(plan['plan']):
            if item['status'] == 'missing':
                print(f"  ❌ Step {i+1}: {item['step'].get('action', 'unknown')} - NO TOOL")
                failed_steps.append(item['step'].get('action', 'unknown'))
                continue

            tool = item['selected']
            step = item['step']
            action = step.get('action')
            cap = item['capability']          # the specific capability dict from 'provides'

            print(f"\n  Step {i+1}: {action}")
            print(f"    Using: {tool.name}")

            # --- Safely prepare inputs ---
            inputs = {}
            with_value = step.get('with')
            if with_value is None:
                with_value = {}
            elif not isinstance(with_value, dict):
                print(f"    ⚠️  'with' value is not a dict (type: {type(with_value)}), treating as empty")
                with_value = {}

            for key, value in with_value.items():
                if isinstance(value, str) and value.startswith('previous.'):
                    ref = value.split('.')[1]
                    if ref in context:
                        inputs[key] = context[ref]
                    else:
                        print(f"    ⚠️  Missing reference: {ref}")
                        inputs[key] = None
                else:
                    inputs[key] = value

            print(f"    Inputs: {inputs}")

            # --- Validate capability ---
            if cap is None:
                print(f"    ❌ No capability definition for action '{action}' in tool {tool.name}")
                result_data = {'error': 'missing capability definition', 'status': 'failed'}
                failed_steps.append(action)
                # Store result and skip to next step
                step_name = step.get('as', action)
                context[step_name] = result_data
                results[action] = result_data
                output_preview = str(result_data)[:100] + "..." if len(str(result_data)) > 100 else str(result_data)
                print(f"    Output: {output_preview}")
                continue

            # --- Determine execution method ---
            execution = tool.capabilities.get('execution', 'cli')   # default to cli

            # --- CLI execution branch ---
            if execution == 'cli':
                print("    [CLI execution]")
                script_path_rel = tool.capabilities.get('path', tool.name + '.py')
                script_path = self.root / script_path_rel
                if not script_path.exists():
                    print(f"    ❌ Script not found: {script_path}")
                    result_data = {'error': 'script not found', 'status': 'failed'}
                    failed_steps.append(action)
                else:
                    print("    Script found")
                    cmd = [sys.executable, str(script_path)]

                    # Add static flags from the capability
                    cmd.extend(cap.get('flags', []))

                    # Add parameters based on capability's 'parameters' declaration
                    declared_params = cap.get('parameters', {})
                    for param_name, param_value in inputs.items():
                        print(f"    debug: param '{param_name}' = {param_value}")
                        if param_name in declared_params:
                            flag = f"--{param_name.replace('_', '-')}"
                            if isinstance(param_value, bool) and param_value:
                                cmd.append(flag)
                            elif not isinstance(param_value, bool):
                                cmd.extend([flag, str(param_value)])
                        else:
                            print(f"    ⚠️  Undeclared parameter '{param_name}' passed to {action}")

                    print(f"    Running: {' '.join(cmd)}")
                    try:
                        result = subprocess.run(
                            cmd,
                            cwd=self.root,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        if result.returncode != 0:
                            print(f"    ❌ CLI tool failed (code {result.returncode})")
                            if result.stderr:
                                print(f"    Error: {result.stderr[:200]}")
                            failed_steps.append(action)
                            result_data = {
                                'error': result.stderr,
                                'status': 'failed',
                                'returncode': result.returncode
                            }
                        else:
                            # Try to parse JSON output
                            try:
                                if result.stdout.strip():
                                    result_data = json.loads(result.stdout)
                                    result_data['status'] = 'success'
                                else:
                                    result_data = {'status': 'success', 'message': 'No output'}
                            except json.JSONDecodeError:
                                result_data = {
                                    'output': result.stdout.strip(),
                                    'status': 'success',
                                    'note': 'non-JSON output'
                                }
                            print(f"    ✅ CLI tool succeeded")
                    except subprocess.TimeoutExpired:
                        print(f"    ❌ CLI tool timed out")
                        failed_steps.append(action)
                        result_data = {'error': 'timeout', 'status': 'failed'}
                    except Exception as e:
                        print(f"    ❌ Error running CLI tool: {e}")
                        failed_steps.append(action)
                        result_data = {'error': str(e), 'status': 'failed'}

            # --- Future execution types can be added here ---
            else:
                print(f"    ⚠️  No execution method '{execution}' implemented, simulating")
                # Simulation fallback (keep your existing cases)
                if action == 'scan.files':
                    result_data = {
                        'files': ['arch_recon.py', 'scanner.py', 'intent_matcher.py'],
                        'count': 3
                    }
                elif action == 'extract.imports':
                    result_data = {
                        'imports': ['intent_matcher', 'reporters', 'db_operations'],
                        'count': 3
                    }
                elif action == 'analyze.coverage':
                    result_data = {
                        'total_files': 10,
                        'covered_files': 7,
                        'uncovered_files': ['file1.py', 'file2.py', 'file3.py'],
                        'coverage_percent': 70.0
                    }
                elif action == 'report.findings':
                    result_data = {
                        'report': 'Coverage: 70% (7/10 files)',
                        'format': 'summary'
                    }
                else:
                    result_data = {'status': 'simulated', 'action': action}

            # --- Track created files if any ---
            if self.session and result_data.get('created_files'):
                for f in result_data['created_files']:
                    self.session.track_created(f)

            # --- Store in context ---
            step_name = step.get('as', action)
            context[step_name] = result_data
            results[action] = result_data

            output_preview = str(result_data)[:100] + "..." if len(str(result_data)) > 100 else str(result_data)
            print(f"    Output: {output_preview}")

        print("\n" + "="*60)

        if failed_steps:
            print(f"⚠️  Plan completed with failures: {list(set(failed_steps))}")
        else:
            print("✅ Plan execution complete")

        return results

class Session:
    """Generic safety wrapper for ANY operation - belt AND suspenders."""
    
    def __init__(self, name, project_root):
        self.name = name
        self.root = Path(project_root)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.root / ".nativeclaw" / "sessions" / f"{name}_{self.timestamp}"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Get current branch before anything
        self.original_branch = self._get_current_branch()
        
        # Sanitize branch name
        safe_name = self._sanitize_branch_name(name)
        self.branch = f"auto/session_{safe_name}_{self.timestamp}"
        
        # Will hold file backups and tracking
        self.backup = {}
        self.created_files = []
    
    def _sanitize_branch_name(self, name):
        """Convert a string to a valid git branch name."""
        # Replace spaces and problematic chars with underscore
        sanitized = re.sub(r'[^\w\-./]+', '_', name)
        # Can't start with '.'
        if sanitized.startswith('.'):
            sanitized = '_' + sanitized[1:]
        # Can't end with '/'
        if sanitized.endswith('/'):
            sanitized = sanitized[:-1] + '_'
        # Can't contain '..'
        sanitized = sanitized.replace('..', '_')
        # Limit length
        if len(sanitized) > 200:
            sanitized = sanitized[:200]
        return sanitized
    
    def _get_current_branch(self):
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.root, capture_output=True, text=True
        )
        return result.stdout.strip()
    
    def start(self):
        """Create branch and backup all tracked files."""
        print(f"\n📸 Session starting: {self.name}")
        
        # BELT 1: git branch isolation
        subprocess.run(["git", "checkout", "-b", self.branch], cwd=self.root, check=True)
        print(f"  ✅ Branch created: {self.branch}")
        
        # SUSPENDERS 1: backup ALL tracked files
        files = subprocess.run(
            ["git", "ls-files"], 
            cwd=self.root, capture_output=True, text=True
        ).stdout.splitlines()
        
        backed_up = 0
        skipped = 0
        for file in files:
            path = self.root / file
            
            # Skip common binary files
            if any(file.endswith(ext) for ext in ['.pyc', '.jpg', '.png', '.gif', '.ico', '.exe', '.dll', '.so', '.dylib']):
                skipped += 1
                continue
            
            if path.exists():
                try:
                    self.backup[file] = path.read_text(encoding='utf-8')
                    backed_up += 1
                except UnicodeDecodeError:
                    skipped += 1
                    continue
        
        # Save backup
        backup_file = self.session_dir / "backup.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(self.backup, f, indent=2)
        
        print(f"  ✅ Backed up {backed_up} text files, skipped {skipped} binary files")
        
        # SUSPENDERS 2: track created files
        created_file = self.session_dir / "created_files.json"
        with open(created_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        # Save session info
        info = {
            'name': self.name,
            'branch': self.branch,
            'original_branch': self.original_branch,
            'timestamp': self.timestamp,
            'backup': str(backup_file),
            'created_files': str(created_file)
        }
        with open(self.session_dir / "session.json", 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2)
        
        # SUSPENDERS 3: check for uncommitted changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.root, capture_output=True, text=True
        ).stdout.strip()
        
        if status:
            print(f"  ⚠️  Note: You have uncommitted changes - they've been backed up")
        
        return self.branch
    
    def track_created(self, filepath):
        """Call this when your tool creates a new file."""
        relative = str(Path(filepath).relative_to(self.root))
        self.created_files.append(relative)
        
        with open(self.session_dir / "created_files.json", 'w', encoding='utf-8') as f:
            json.dump(self.created_files, f, indent=2)
        
        print(f"  📝 Tracking new file: {relative}")
    
    def restore(self):
        """Restore to exact pre-session state."""
        print(f"\n♻️  Restoring session: {self.name}")
        
        # Restore file contents
        restored = 0
        for file, content in self.backup.items():
            path = self.root / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            restored += 1
        
        print(f"  ✅ Restored {restored} files from backup")
        
        # Delete any created files
        created_file = self.session_dir / "created_files.json"
        if created_file.exists():
            with open(created_file, 'r', encoding='utf-8') as f:
                created = json.load(f)
            
            deleted = 0
            for file in created:
                path = self.root / file
                if path.exists():
                    path.unlink()
                    deleted += 1
            print(f"  ✅ Deleted {deleted} created files")
        
        # Return to original branch
        subprocess.run(["git", "checkout", self.original_branch, "--force"], 
                      cwd=self.root, check=True)
        print(f"  ✅ Returned to branch: {self.original_branch}")
        
        # Clean up session branch
        result = subprocess.run(
            ["git", "branch", "-D", self.branch],
            cwd=self.root, capture_output=True
        )
        if result.returncode == 0:
            print(f"  ✅ Deleted branch: {self.branch}")
        
        with open(self.session_dir / "restored.txt", 'w', encoding='utf-8') as f:
            f.write(f"Restored at: {datetime.now().isoformat()}")
        
        print("✅ Session fully restored")
    
    def restore_partial(self, keep_files=None):
        """Restore everything except specified files."""
        keep = keep_files or []
        print(f"\n♻️  Partially restoring session: {self.name}")
        
        # Restore files except kept ones
        restored = 0
        skipped = 0
        for file, content in self.backup.items():
            if file in keep:
                print(f"  🔒 Keeping: {file}")
                skipped += 1
            else:
                path = self.root / file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
                restored += 1
        
        print(f"  ✅ Restored {restored} files, kept {skipped} modified")
        
        # Delete created files except kept ones
        created_file = self.session_dir / "created_files.json"
        if created_file.exists():
            with open(created_file, 'r', encoding='utf-8') as f:
                created = json.load(f)
            
            deleted = 0
            kept_created = 0
            for file in created:
                if file in keep:
                    print(f"  🔒 Keeping created: {file}")
                    kept_created += 1
                else:
                    path = self.root / file
                    if path.exists():
                        path.unlink()
                        deleted += 1
            print(f"  ✅ Deleted {deleted} created files, kept {kept_created}")
        
        subprocess.run(["git", "checkout", self.original_branch, "--force"], 
                      cwd=self.root, check=True)
        
        print("✅ Partial restore complete")
    
    def approve(self):
        """Keep changes, clean up session."""
        print(f"\n✅ Approving session: {self.name}")
        
        # Create pre-merge backup
        pre_merge_dir = self.session_dir / "pre_merge"
        pre_merge_dir.mkdir(exist_ok=True)
        
        for file in self.created_files:
            path = self.root / file
            if path.exists():
                backup_path = pre_merge_dir / file.replace('/', '_')
                backup_path.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
        
        # Merge changes
        subprocess.run(["git", "checkout", self.original_branch], cwd=self.root, check=True)
        subprocess.run(["git", "merge", self.branch], cwd=self.root, check=True)
        subprocess.run(["git", "branch", "-D", self.branch], cwd=self.root, check=True)
        
        with open(self.session_dir / "approved.txt", 'w', encoding='utf-8') as f:
            f.write(f"Approved at: {datetime.now().isoformat()}")
        
        print(f"✅ Changes merged to {self.original_branch}")
        print(f"📁 Pre-merge backup saved to: {pre_merge_dir}")
    
    def abort(self):
        """Clean up on error without restoring."""
        print(f"\n⚠️  Aborting session: {self.name}")
        
        subprocess.run(["git", "checkout", self.original_branch, "--force"], 
                      cwd=self.root, check=True)
        subprocess.run(["git", "branch", "-D", self.branch], 
                      cwd=self.root, check=True)
        
        with open(self.session_dir / "aborted.txt", 'w', encoding='utf-8') as f:
            f.write(f"Aborted at: {datetime.now().isoformat()}")
        
        print("✅ Session aborted")

def main():
    parser = argparse.ArgumentParser(description="NativeClaw - Native Windows goal runner")
    parser.add_argument("command", choices=["semantic", "resume", "doctor", "list-capabilities"])
    parser.add_argument("goal_or_review", nargs="?", help="Path to goal YAML file or review folder")
    
    args = parser.parse_args()
    
    if args.command == "doctor":
        log(f"Project root: {PROJECT_ROOT}")
        log(f"Git available: {subprocess.run(['git', '--version'], capture_output=True).returncode == 0}")
        
        winmerge_path = r"C:\Program Files\WinMerge\WinMergeU.exe"
        log(f"WinMerge available: {os.path.exists(winmerge_path)}")
        
        registry = ToolRegistry(PROJECT_ROOT)
        log(f"Tools found: {len(registry.tools)}")
        for tool in registry.tools:
            caps = len(tool.capabilities.get('provides', []))
            log(f"  - {tool.name}: {caps} capabilities")
        
        # Check for pending reviews
        archive_dir = PROJECT_ROOT / ".nativeclaw" / "archive"
        if archive_dir.exists():
            pending = []
            for review_dir in archive_dir.iterdir():
                if review_dir.is_dir():
                    state_file = review_dir / "state.json"
                    approved = review_dir / "approved.txt"
                    rejected = review_dir / "rejected.txt"
                    
                    if state_file.exists() and not approved.exists() and not rejected.exists():
                        pending.append(review_dir.name)
            
            if pending:
                print("\n📋 PENDING REVIEWS:")
                for p in pending:
                    print(f"  Scripts\\nativeclaw.bat resume .nativeclaw\\archive\\{p}\\")
        return
    
    if args.command == "list-capabilities":
        registry = ToolRegistry(PROJECT_ROOT)
        caps = registry.list_all_capabilities()
        print("\n📋 All capabilities provided by tools:")
        for cap in caps:
            tools = registry.find_tools_for(cap)
            tool_names = [t.name for t in tools]
            print(f"  {cap}: {', '.join(tool_names)}")
        return
    
    if args.command == "semantic":
        if not args.goal_or_review:
            print("ERROR: Need goal file. Example: nativeclaw.py semantic goals/semantic_test.yaml")
            sys.exit(1)
        
        goal_path = Path(args.goal_or_review)
        if not goal_path.exists():
            goal_path = PROJECT_ROOT / args.goal_or_review
        
        if not goal_path.exists():
            print(f"ERROR: Goal file not found: {goal_path}")
            sys.exit(1)
        
        goal = yaml.safe_load(goal_path.read_text(encoding='utf-8'))
        print(f"\n🎯 Semantic Goal: {goal.get('name', 'unnamed')}")
        
        registry = ToolRegistry(PROJECT_ROOT)
        resolver = CapabilityResolver(registry, PROJECT_ROOT)
        
        result = resolver.resolve(goal.get('steps', []))
        
        if not result['success']:
            print(f"\n❌ Cannot fulfill goal. Missing capabilities:")
            for cap in result['missing']:
                print(f"   - {cap}")
            print("\nAvailable capabilities:")
            for cap in registry.list_all_capabilities():
                print(f"   - {cap}")
            return
        
        print(f"\n✅ Goal can be fulfilled!")
        execute = input("\nExecute plan? [y/N]: ").strip().lower()
        
        if execute == 'y':
            # Start a sessio
            session = Session(f"semantic_{goal.get('name', 'run')}", PROJECT_ROOT
            branch = session.start(
            resolver.set_session(session
            
            try:
                # Execute the plan
                outputs = resolver.execute_plan(result, session)
                
                # Save review
                archive_dir = PROJECT_ROOT / ".nativeclaw" / "archive" / datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_dir.mkdir(parents=True, exist_ok=True)
                
                state = {
                    'branch_name': branch,
                    'original_branch': session.original_branch,
                    'goal_name': goal.get('name'),
                    'timestamp': datetime.now().isoformat()
                }

                with open(archive_dir / "state.json", 'w', encoding='utf-8') as f:
                    json.dump(state, f, indent=2)
                
                with open(archive_dir / "changes.diff", 'w', encoding='utf-8') as f:
                    subprocess.run(
                        ["git", "diff", f"{session.original_branch}..{branch}"],
                        cwd=PROJECT_ROOT, stdout=f, text=True
                    )
                
                with open(archive_dir / "files.txt", 'w', encoding='utf-8') as f:
                    subprocess.run(
                        ["git", "ls-tree", "-r", branch, "--name-only"],
                        cwd=PROJECT_ROOT, stdout=f, text=True
                    )
                
                resume_instructions = f"""REVIEW SAVED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Goal: {goal.get('name', 'unknown')}
Branch: {branch}

To resume this review:
  Scripts\\nativeclaw.bat resume {archive_dir}
"""
                with open(archive_dir / "RESUME.txt", 'w', encoding='utf-8') as f:
                    f.write(resume_instructions)
                
                print("\n" + "="*70)
                print(f"✅ Review saved to: {archive_dir}")
                print(f"📄 Resume instructions: {archive_dir / 'RESUME.txt'}")
                
                input("\nPress Enter when ready to approve/reject...")
                resp = input("Approve? [Y]es [N]o: ").strip().upper()
                if resp == 'Y':
                    session.approve()
                else:
                    session.restore()
                    
            except Exception as e:
                print(f"\n❌ Error during execution: {e}")
                session.restore()
                print("✅ Session restored to original state")
        return
    
    if args.command == "resume":
        if not args.goal_or_review:
            print("ERROR: Need review folder. Example: nativeclaw.py resume .nativeclaw/archive/20260217_153000/")
            sys.exit(1)
        
        review_path = Path(args.goal_or_review)
        if not review_path.exists():
            review_path = PROJECT_ROOT / args.goal_or_review
        
        if not review_path.exists():
            print(f"ERROR: Review folder not found: {review_path}")
            sys.exit(1)
        
        # Load state
        state_file = review_path / "state.json"
        if not state_file.exists():
            print("ERROR: No state.json in review folder")
            sys.exit(1)
        
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        branch_name = state.get('branch_name')
        original_branch = state.get('original_branch', 'master')
        goal_name = state.get('goal_name')
        
        print(f"\n📋 Resuming review: {goal_name}")
        print(f"  Branch: {branch_name}")
        
        # Show diff
        diff_file = review_path / "changes.diff"
        if diff_file.exists():
            print("\n" + "="*50)
            print("CHANGES TO REVIEW:")
            print("="*50)
            with open(diff_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content[:1000])
                if len(content) > 1000:
                    print("\n... (truncated)")
        
        # Ask for decision
        while True:
            print("\n" + "-"*40)
            print("Review commands:")
            print("  Y - Approve and merge")
            print("  N - Reject and delete branch")
            print("  Q - Quit (leave branch for later)")
            print("-"*40)
            
            response = input("Choice: ").strip().upper()
            
            if response == 'Y':
                subprocess.run(["git", "checkout", original_branch], cwd=PROJECT_ROOT, check=True)
                subprocess.run(["git", "merge", branch_name], cwd=PROJECT_ROOT, check=True)
                subprocess.run(["git", "branch", "-D", branch_name], cwd=PROJECT_ROOT, check=True)
                with open(review_path / "approved.txt", 'w') as f:
                    f.write(f"Approved at: {datetime.now().isoformat()}")
                print("✅ Changes approved and merged")
                break
                
            elif response == 'N':
                subprocess.run(["git", "branch", "-D", branch_name], cwd=PROJECT_ROOT, check=True)
                with open(review_path / "rejected.txt", 'w') as f:
                    f.write(f"Rejected at: {datetime.now().isoformat()}")
                print("❌ Changes rejected, branch deleted")
                break
                
            elif response == 'Q':
                print("Exiting, branch left untouched")
                break

if __name__ == "__main__":
    main()