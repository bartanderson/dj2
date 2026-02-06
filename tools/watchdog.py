#!/usr/bin/env python3
"""
WATCHDOG - Project Health Monitor WITH HYBRID AI INTEGRATION
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\bartl\dev\dj2")
os.chdir(PROJECT_ROOT)

MEMORY_FILE = PROJECT_ROOT / "ai_context" / "watchdog_memory.json"
GOALS_FILE = PROJECT_ROOT / "ai_context" / "watchdog_goals.md"

# ============================================================================
# NEW: HYBRID PHASE AUDITOR INTEGRATION
# ============================================================================

# In watchdog.py, replace the entire HybridPhaseAuditor class with:

class HybridPhaseAuditor:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        
    def get_current_violations(self):
        """Get actual violations using AST analyzer."""
        try:
            cmd = [sys.executable, "tools/analysis/ast_analyzer.py", ".", "--mode", "violations"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                violations = []
                for line in result.stdout.split('\n'):
                    if any(term in line for term in ['DIRECT_AI_CALL', 'PHASE_VIOLATION', 'violation']):
                        parts = line.split(':')
                        if len(parts) >= 2:
                            violations.append({
                                'file': parts[0].strip(),
                                'line': parts[1].strip() if len(parts) > 1 else '?',
                                'text': ':'.join(parts[2:]).strip()[:150] if len(parts) > 2 else line[:150]
                            })
                
                return {
                    'total': len(violations),
                    'violations': violations[:15],
                    'raw_sample': result.stdout[:1000]
                }
            return {'error': result.stderr[:200]}
        except Exception as e:
            return {'error': str(e)}
    
    def classify_with_local_ai(self, violations_data):
        """Use the unified Ollama client for classification."""
        try:
            from tools.ollama_client import get_ollama_client
            
            client = get_ollama_client()
            
            if not client.is_available():
                return "⚠️ Ollama not available. Run: ollama serve"
            
            if not violations_data.get('violations'):
                return "No violations to analyze"
            
            # Build focused prompt
            violations_text = "\n".join([
                f"{i+1}. {v.get('file', 'unknown')}:{v.get('line', '?')} - {v.get('text', '')[:80]}"
                for i, v in enumerate(violations_data['violations'][:6])
            ])
            
            prompt = f"""Code violations found: {violations_data.get('total', 0)}

{violations_text}

Classify by urgency:
★★★★ - Critical (fix now)
★★★ - High (fix today)  
★★ - Medium (this week)
★ - Low (when convenient)

Which 3 should we fix FIRST? Be specific with file:line.
Respond in 4 lines max."""
            
            response = client.quick_chat(prompt, max_lines=4)
            return response if response else "Local AI returned empty response"
            
        except ImportError:
            return "Cannot import ollama_client"
        except Exception as e:
            return f"Local AI error: {str(e)[:100]}"

# ============================================================================
# EXISTING WATCHDOG FUNCTIONS (UPDATED)
# ============================================================================

def load_memory():
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"runs": [], "patterns": {}, "last_hybrid_audit": None}
    return {"runs": [], "patterns": {}, "last_hybrid_audit": None}

def save_memory(memory):
    MEMORY_FILE.parent.mkdir(exist_ok=True, parents=True)
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def run_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def check_phase_violations():
    """Check phase violations - UPDATED to use HybridPhaseAuditor"""
    auditor = HybridPhaseAuditor()
    violations_data = auditor.get_current_violations()
    
    if 'error' in violations_data:
        # Fallback to old method
        stdout, stderr, code = run_command("python ai.py violations .")
        lines = stdout.split('\n')
        violations = sum(1 for line in lines if 'violation' in line.lower() or '❌' in line)
        return violations, stdout[:300]
    
    # Use new auditor data
    total = violations_data.get('total', 0)
    sample = ""
    if violations_data.get('violations'):
        sample = "\n".join([f"{v.get('file')}:{v.get('line')}" 
                          for v in violations_data['violations'][:3]])
    
    return total, sample

def check_recent_activity():
    changes = {"commits": 0, "uncommitted": 0, "branch": "unknown"}
    
    stdout, stderr, code = run_command("git log --oneline --since=\"24 hours ago\"")
    if stdout.strip():
        changes["commits"] = len(stdout.strip().split('\n'))
    
    stdout, stderr, code = run_command("git status --porcelain")
    if stdout.strip():
        changes["uncommitted"] = len(stdout.strip().split('\n'))
    
    stdout, stderr, code = run_command("git branch --show-current")
    if stdout.strip():
        changes["branch"] = stdout.strip()
    
    return changes

def check_session_status():
    session_file = PROJECT_ROOT / "ai_context" / "session" / "current_session.json"
    if not session_file.exists():
        return {"active": False, "age_days": None, "topic": None}
    
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            session = json.load(f)
        
        updated_str = session.get('updated', session.get('started', '2000-01-01'))
        try:
            updated = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
        except:
            updated = datetime.strptime(updated_str.split('T')[0], '%Y-%m-%d')
        
        age_days = (datetime.now() - updated).days
        
        return {
            "active": True,
            "age_days": age_days,
            "topic": session.get('topic', 'Unknown'),
            "updated": updated_str
        }
    except Exception as e:
        return {"active": False, "error": str(e)}

def check_tool_health():
    tools = {
        "ai.py": PROJECT_ROOT / "ai.py",
        "context_manager.py": PROJECT_ROOT / "scripts" / "context_manager.py",
        "ai_workflow.py": PROJECT_ROOT / "scripts" / "ai_workflow.py",
        "ast_analyzer.py": PROJECT_ROOT / "tools" / "analysis" / "ast_analyzer.py",
    }
    
    health = {}
    for name, path in tools.items():
        exists = path.exists()
        health[name] = {"exists": exists, "runnable": False}
        
        if exists and name == "ai.py":
            stdout, stderr, code = run_command(f"python {path} --help")
            health[name]["runnable"] = code == 0
    
    return health

# ============================================================================
# NEW: HYBRID WORKFLOW DECISION MAKING
# ============================================================================

def should_use_hybrid_audit(memory, violations_count):
    """Decide if we should run hybrid audit"""
    # If never run before
    if not memory.get("last_hybrid_audit"):
        return True
    
    # If high violations
    if violations_count > 5:
        return True
    
    # If last run was more than 3 days ago
    try:
        last_run = datetime.fromisoformat(memory["last_hybrid_audit"])
        days_since = (datetime.now() - last_run).days
        if days_since > 3:
            return True
    except:
        return True
    
    return False

def run_hybrid_audit():
    """Run the hybrid audit and update memory"""
    print("\n" + "="*70)
    print("🚀 RUNNING HYBRID AI AUDIT")
    print("Local AI (fast) + DeepSeek (powerful)")
    print("="*70)
    
    auditor = HybridPhaseAuditor()
    
    # Step 1: Get violations
    print("\n[1/3] 🔍 Scanning for actual violations...")
    violations = auditor.get_current_violations()
    
    if 'error' in violations:
        print(f"Error: {violations['error']}")
        return None
    
    print(f"Found {violations.get('total', 0)} violations")
    
    # Step 2: Local AI analysis
    print("\n[2/3] 🤖 Local AI classification (fast)...")
    local_analysis = auditor.classify_with_local_ai(violations)
    
    print("\nLOCAL AI SAYS:")
    print("-" * 40)
    print(local_analysis)
    
    # Step 3: Prepare context
    print("\n[3/3] 📋 Preparing context...")
    
    context = f"""PROJECT STATUS: Hybrid Audit Results

VIOLATIONS: {violations.get('total', 0)} found

LOCAL AI ANALYSIS (fast):
{local_analysis}

TOP VIOLATIONS TO FIX:
"""
    
    for i, v in enumerate(violations.get('violations', [])[:5], 1):
        context += f"\n{i}. {v.get('file', 'unknown')}:{v.get('line', '?')}"
        context += f"\n   {v.get('text', '')[:100]}"
    
    context += f"""

RECOMMENDED WORKFLOW:
1. Fix critical violations (★★★★) first
2. Run validation: python ai.py violations .
3. Commit fixes
4. Send remaining issues to DeepSeek for final polish

READY FOR DEEPSEEK? Copy this context or run: python scripts/ai_workflow.py send
"""
    
    # Save context
    output_file = PROJECT_ROOT / "hybrid_audit_results.txt"
    output_file.write_text(context, encoding='utf-8')
    
    print(f"\n✅ Hybrid audit complete!")
    print(f"   Results: {output_file}")
    
    # Update memory
    memory = load_memory()
    memory["last_hybrid_audit"] = datetime.now().isoformat()
    save_memory(memory)
    
    return {
        'violations': violations,
        'local_analysis': local_analysis,
        'context_file': str(output_file)
    }

# ============================================================================
# UPDATED MAIN WATCHDOG FUNCTION
# ============================================================================

def run_watchdog():
    print("\n" + "="*70)
    print("WATCHDOG - Project Health Monitor")
    print(f"Run at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    
    # Load memory
    memory = load_memory()
    
    # Run checks
    print("\n📊 PROJECT VITAL SIGNS")
    print("-" * 40)
    
    violations_count, violation_sample = check_phase_violations()
    activity = check_recent_activity()
    session = check_session_status()
    tools = check_tool_health()
    
    print(f"Phase Violations: {violations_count}")
    if violations_count > 0:
        print(f"  Sample: {violation_sample}")
    
    print(f"\nRecent Activity:")
    print(f"  Commits (24h): {activity.get('commits', 0)}")
    print(f"  Uncommitted: {activity.get('uncommitted', 0)}")
    print(f"  Branch: {activity.get('branch', 'unknown')}")
    
    print(f"\nSession Status:")
    if session["active"]:
        print(f"  ✅ Active: {session.get('topic', 'Unknown')}")
        print(f"  Age: {session.get('age_days', 0)} days")
    else:
        print(f"  ❌ No active session")
    
    # HYBRID DECISION
    print(f"\n🤖 AI WORKFLOW RECOMMENDATION")
    print("-" * 40)
    
    if violations_count == 0:
        print("  ✅ No violations - Use DeepSeek for strategic planning")
        print("  Command: python scripts/ai_workflow.py start --topic 'Architecture planning'")
    
    elif violations_count <= 3:
        print("  ⚠️  Few violations - Use local AI for quick fixes")
        print("  Command: python ai.py analyze 'Fix phase violations'")
    
    elif violations_count <= 10:
        print("  🔥 Moderate violations - Run hybrid audit")
        print("  Command: python tools/watchdog.py --hybrid-audit")
    
    else:
        print("  🚨 High violations - PRIORITY: Hybrid audit required")
        print("  Command: python tools/watchdog.py --hybrid-audit")
    
    # Check if we should run hybrid audit automatically
    if should_use_hybrid_audit(memory, violations_count):
        print(f"\n💡 SUGGESTION: Run hybrid audit (last run: {memory.get('last_hybrid_audit', 'never')})")
        print("  Run: python tools/watchdog.py --hybrid-audit")
    
    # Tool health
    print(f"\n🔧 TOOL HEALTH")
    print("-" * 40)
    for tool, info in tools.items():
        status = "✅" if info["exists"] else "❌"
        print(f"  {status} {tool}")
    
    # Quick commands
    print(f"\n⚡ QUICK COMMANDS")
    print("-" * 40)
    print("  1. Hybrid audit: python tools/watchdog.py --hybrid-audit")
    print("  2. Fix violations: python ai.py violations .")
    print("  3. Start session: python scripts/ai_workflow.py start --topic \"...\"")
    print("  4. DeepSeek only: python scripts/context_manager.py --query \"...\" --send")
    
    print("\n" + "="*70)
    print("💡 Use hybrid workflow: Local AI (fast) → Fix 80% → DeepSeek (polish 20%)")
    print("="*70)

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--edit-goals":
            os.system(f'notepad "{GOALS_FILE}"')
            sys.exit(0)
        elif sys.argv[1] == "--history":
            memory = load_memory()
            print("Run History (last 10):")
            for run in memory.get("runs", [])[-10:]:
                print(f"  {run.get('timestamp', 'unknown')}: "
                      f"{run.get('violations', 0)} violations")
            sys.exit(0)
        elif sys.argv[1] == "--hybrid-audit":
            # Run the hybrid audit
            result = run_hybrid_audit()
            if result:
                print(f"\n📋 Next: Review {result['context_file']}")
                print("   Then send to DeepSeek or fix locally")
            sys.exit(0)
        elif sys.argv[1] == "--help":
            print("Watchdog - Project Health Monitor")
            print("Usage:")
            print("  python tools/watchdog.py           # Run health check")
            print("  python tools/watchdog.py --hybrid-audit  # Run hybrid AI audit")
            print("  python tools/watchdog.py --edit-goals    # Edit goals file")
            print("  python tools/watchdog.py --history       # Show run history")
            print("  python tools/watchdog.py --help          # Show this help")
            sys.exit(0)
    
    # Run normal watchdog
    run_watchdog()