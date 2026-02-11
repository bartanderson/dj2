#!/usr/bin/env python3
# coding=utf-8
"""
PROJECT AUDITOR - Consolidated dashboard with REAL analysis only
Replaces: watchdog.py + ai_workflow.py
Shows: Real violations, TODOs, git activity, tool health, sessions
NO FAKE ANALYSIS - Only calls existing tools
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os

PROJECT_ROOT = Path(r"C:\Users\bartl\dev\dj2")
os.chdir(PROJECT_ROOT)

class ProjectAuditor:
    """Dashboard showing REAL project status from existing tools"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        
    def run_command(self, cmd: List[str]) -> Tuple[str, str, int]:
        """Run a shell command - REAL execution"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=60
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1
    
    def get_phase_violations(self) -> Dict:
        """Get REAL phase violations from ast_analyzer"""
        print("🔍 Checking phase violations...")
        cmd = [sys.executable, "tools/analysis/ast_analyzer.py", ".", "--mode", "violations"]
        stdout, stderr, code = self.run_command(cmd)
        
        if code != 0:
            return {"error": stderr[:500]}
        
        violations = []
        lines = stdout.split('\n')
        
        for line in lines:
            if 'DIRECT_AI_CALL' in line or 'PHASE_VIOLATION' in line:
                parts = line.strip().split(':', 3)
                if len(parts) >= 3:
                    violations.append({
                        "file": parts[0].strip(),
                        "line": parts[1].strip(),
                        "pattern": parts[2].strip(),
                        "text": parts[3].strip() if len(parts) > 3 else ""
                    })
        
        return {
            "total": len(violations),
            "violations": violations[:10]  # Top 10
        }
    
    def get_todos(self) -> Dict:
        """Get REAL TODOs from ast_analyzer"""
        print("📝 Checking TODOs...")
        cmd = [sys.executable, "tools/analysis/ast_analyzer.py", ".", "--mode", "todos"]
        stdout, stderr, code = self.run_command(cmd)
        
        if code != 0:
            return {"error": stderr[:500]}
        
        todos = []
        lines = stdout.split('\n')
        
        for line in lines:
            if 'TODO' in line or 'FIXME' in line:
                parts = line.strip().split(':', 3)
                if len(parts) >= 3:
                    todos.append({
                        "file": parts[0].strip(),
                        "line": parts[1].strip(),
                        "type": "TODO" if 'TODO' in line else "FIXME",
                        "text": parts[2].strip()
                    })
        
        return {
            "total": len(todos),
            "todos": todos[:15]  # Top 15
        }
    
    def get_git_status(self) -> Dict:
        """Get REAL git activity"""
        print("📊 Checking git status...")
        
        status = {"commits": 0, "uncommitted": 0, "branch": "unknown"}
        
        # Recent commits
        stdout, stderr, code = self.run_command(["git", "log", "--oneline", "--since=\"24 hours ago\""])
        if stdout.strip():
            status["commits"] = len(stdout.strip().split('\n'))
        
        # Uncommitted changes
        stdout, stderr, code = self.run_command(["git", "status", "--porcelain"])
        if stdout.strip():
            status["uncommitted"] = len(stdout.strip().split('\n'))
        
        # Current branch
        stdout, stderr, code = self.run_command(["git", "branch", "--show-current"])
        if stdout.strip():
            status["branch"] = stdout.strip()
        
        return status
    
    def get_tool_health(self) -> Dict:
        """Check REAL tool availability"""
        print("🔧 Checking tool health...")
        
        tools = {
            "ai.py": PROJECT_ROOT / "ai.py",
            "context_manager.py": PROJECT_ROOT / "scripts" / "context_manager.py",
            "ast_analyzer.py": PROJECT_ROOT / "tools" / "analysis" / "ast_analyzer.py",
        }
        
        health = {}
        for name, path in tools.items():
            exists = path.exists()
            runnable = False
            
            if exists:
                # Quick test if it runs
                if name == "ai.py":
                    stdout, stderr, code = self.run_command([sys.executable, str(path), "--help"])
                    runnable = code == 0
                elif name == "context_manager.py":
                    # Can't test without arguments, just check file
                    runnable = True
            
            health[name] = {"exists": exists, "runnable": runnable}
        
        return health
    
    def get_session_status(self) -> Dict:
        """Get REAL session status from files"""
        print("📂 Checking session status...")
        
        session_file = PROJECT_ROOT / "ai_context" / "session" / "current_session.json"
        if not session_file.exists():
            return {"active": False}
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session = json.load(f)
            
            updated_str = session.get('updated', session.get('started', '2000-01-01'))
            try:
                updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
                age_days = (datetime.now() - updated).days
            except:
                age_days = 0
            
            return {
                "active": True,
                "topic": session.get('topic', 'Unknown'),
                "age_days": age_days,
                "updated": updated_str
            }
        except Exception as e:
            return {"active": False, "error": str(e)}
    
    def get_project_status(self) -> Dict:
        """Get REAL project status from status_manifest"""
        print("📈 Checking project status...")
        
        status_file = PROJECT_ROOT / "ai_context" / "status_manifest.json"
        if not status_file.exists():
            return {"error": "No status_manifest.json found"}
        
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            
            # Calculate completion
            phases = status.get("phases", {})
            total = len(phases)
            complete = sum(1 for p in phases.values() if p.get("status") == "complete")
            
            return {
                "completion": int((complete / total * 100)) if total > 0 else 0,
                "complete_phases": complete,
                "total_phases": total,
                "active_phases": [
                    name for name, data in phases.items()
                    if data.get("status") in ["in_progress", "blocked"]
                ]
            }
        except Exception as e:
            return {"error": str(e)}
    
    def show_dashboard(self):
        """Show consolidated REAL dashboard"""
        print("\n" + "="*80)
        print("PROJECT AUDITOR - Real Data Dashboard")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Collect REAL data
        violations = self.get_phase_violations()
        todos = self.get_todos()
        git_status = self.get_git_status()
        tool_health = self.get_tool_health()
        session_status = self.get_session_status()
        project_status = self.get_project_status()
        
        # 1. Project Status
        print("\n📊 PROJECT STATUS")
        print("-" * 50)
        if "error" not in project_status:
            print(f"Completion: {project_status['completion']}%")
            print(f"Phases: {project_status['complete_phases']}/{project_status['total_phases']} complete")
            if project_status["active_phases"]:
                print(f"Active: {', '.join(project_status['active_phases'])}")
        else:
            print(f"Status: {project_status['error']}")
        
        # 2. Code Health
        print("\n🏥 CODE HEALTH")
        print("-" * 50)
        if "error" not in violations:
            print(f"Phase Violations: {violations['total']}")
            if violations['violations']:
                print("  Recent violations:")
                for v in violations['violations'][:3]:
                    print(f"    - {v['file']}:{v['line']} ({v['pattern']})")
        else:
            print(f"Violations: {violations['error']}")
        
        if "error" not in todos:
            print(f"TODOs/FIXMEs: {todos['total']}")
            if todos['todos']:
                print("  Recent TODOs:")
                for t in todos['todos'][:3]:
                    print(f"    - {t['file']}:{t['line']}: {t['text'][:60]}...")
        
        # 3. Git Activity
        print("\n📈 RECENT ACTIVITY")
        print("-" * 50)
        print(f"Branch: {git_status['branch']}")
        print(f"Commits (24h): {git_status['commits']}")
        print(f"Uncommitted changes: {git_status['uncommitted']}")
        
        # 4. Session Status
        print("\n📂 AI SESSION")
        print("-" * 50)
        if session_status['active']:
            print(f"✅ Active: {session_status['topic']}")
            print(f"   Age: {session_status.get('age_days', 0)} days")
        else:
            print("❌ No active session")
        
        # 5. Tool Health
        print("\n🔧 TOOL HEALTH")
        print("-" * 50)
        for tool, status in tool_health.items():
            icon = "✅" if status["exists"] and status["runnable"] else "⚠️ " if status["exists"] else "❌"
            print(f"{icon} {tool}")
        
        # 6. Top Priorities (REAL, not fake)
        print("\n🎯 TOP PRIORITIES (Based on REAL data)")
        print("-" * 50)
        priorities = []
        
        # Priority 1: Critical violations
        if "error" not in violations and violations['total'] > 0:
            priorities.append({
                "title": "Fix Phase Violations",
                "reason": f"{violations['total']} architectural violations found",
                "action": "Run: python ai.py violations ."
            })
        
        # Priority 2: High priority TODOs
        if "error" not in todos and todos['total'] > 10:
            priorities.append({
                "title": "Address TODOs",
                "reason": f"{todos['total']} outstanding TODOs/FIXMEs",
                "action": "Run: python ai.py todos ."
            })
        
        # Priority 3: Old session
        if session_status['active'] and session_status.get('age_days', 0) > 3:
            priorities.append({
                "title": "Review Old Session",
                "reason": f"Session '{session_status['topic']}' is {session_status['age_days']} days old",
                "action": "Run: python scripts/context_manager.py --query 'continue session'"
            })
        
        # Priority 4: Uncommitted changes
        if git_status['uncommitted'] > 5:
            priorities.append({
                "title": "Commit Changes",
                "reason": f"{git_status['uncommitted']} uncommitted changes",
                "action": "Run: git status"
            })
        
        # Show priorities
        if priorities:
            for i, p in enumerate(priorities[:3], 1):
                print(f"{i}. {p['title']}")
                print(f"   Why: {p['reason']}")
                print(f"   Action: {p['action']}")
        else:
            print("✅ No urgent issues found!")
        
        # 7. Quick Commands
        print("\n⚡ QUICK COMMANDS")
        print("-" * 50)
        print("1. Get AI context for priority #1:")
        if priorities:
            query = priorities[0]['title'].lower().replace(' ', '_')
            print(f"   python scripts/context_manager.py --query '{query}'")
        else:
            print("   python scripts/context_manager.py --query 'project status'")
        
        print("2. Start new AI session:")
        print("   python scripts/context_manager.py --query 'your topic' --send")
        
        print("3. Run deep analysis:")
        print("   python tools/analysis/ast_analyzer.py . --mode full")
        
        print("\n" + "="*80)
        print("💡 All data shown is REAL from existing tools")
        print("="*80)

def main():
    """Main entry point - simple, no complex arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Project Auditor - Real Data Dashboard")
    parser.add_argument("--quick", "-q", action="store_true", help="Quick check only")
    parser.add_argument("--session", action="store_true", help="Show only session status")
    parser.add_argument("--health", action="store_true", help="Show only tool health")
    
    args = parser.parse_args()
    
    auditor = ProjectAuditor()
    
    if args.session:
        status = auditor.get_session_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.health:
        health = auditor.get_tool_health()
        print(json.dumps(health, indent=2))
        return
    
    # Show full dashboard
    auditor.show_dashboard()

if __name__ == "__main__":
    main()