# scripts/simple_tool_tester.py
"""
Simple, accurate tool tester - only tests what we know works
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict

def test_basic_command(cmd: str, args: List[str] = None) -> Dict:
    """Test a command with minimal, safe arguments"""
    project_root = Path(r"C:\Users\bartl\dev\dj2")
    
    # Safe test patterns based on your actual commands
    test_cases = {
        "search": ["search", "test"],
        "analyze": ["analyze", "test"],
        "violations": ["violations", "."],
        "todos": ["todos", "."],
        "deps": ["deps", "."],
        "structure": ["structure", "."],
        # For commands that might not need args
        "context": ["context"],
        "validate": ["validate"],
        "guardrails": ["guardrails"],  # Might need args
        "phase-check": ["phase-check"],
        "bridge-status": ["bridge-status"],
        "index": ["index"],
        "archive-index": ["archive-index"],
        "refactor-plan": ["refactor-plan"],
        "js-css-check": ["js-css-check"],
        "analyze-project": ["analyze-project"],
        "feature-report": ["feature-report"],
        "living-workflow": ["living-workflow"],
        "tools": ["tools"],
        "tool-help": ["tool-help", "search"],  # Example with arg
    }
    
    # Build command
    cmd_parts = ["python", "ai.py", cmd]
    if args:
        cmd_parts.extend(args)
    elif cmd in test_cases:
        cmd_parts = ["python", "ai.py"] + test_cases[cmd]
    
    try:
        print(f"Testing: {' '.join(cmd_parts)}")
        result = subprocess.run(
            cmd_parts,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
            shell=True
        )
        
        if result.returncode == 0:
            return {
                "status": "✅ Working",
                "output": result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout,
                "returncode": result.returncode
            }
        else:
            # Some commands might exit with non-zero for help-like output
            output = result.stderr or result.stdout
            if "usage:" in output.lower() or "error:" in output.lower():
                return {
                    "status": "⚠️  Partial (shows usage/error)",
                    "output": output[:200] + "..." if len(output) > 200 else output,
                    "returncode": result.returncode
                }
            return {
                "status": "❌ Error",
                "output": output[:200] + "..." if len(output) > 200 else output,
                "returncode": result.returncode
            }
            
    except Exception as e:
        return {
            "status": "❌ Exception",
            "output": str(e),
            "returncode": -1
        }

def get_actual_commands():
    """Get commands from ai.py help (better parsing)"""
    project_root = Path(r"C:\Users\bartl\dev\dj2")
    
    result = subprocess.run(
        ["python", "ai.py", "--help"],
        cwd=project_root,
        capture_output=True,
        text=True,
        shell=True
    )
    
    if result.returncode != 0:
        return []
    
    # Simple but more robust parsing
    lines = result.stdout.split('\n')
    commands = []
    in_commands = False
    
    for line in lines:
        line = line.strip()
        
        if "commands:" in line.lower():
            in_commands = True
            continue
        elif "options:" in line.lower() or line.startswith('-'):
            in_commands = False
            continue
            
        if in_commands and line and not line.startswith(' ') and ' ' in line:
            # Take first word as command
            cmd = line.split()[0].strip()
            if cmd and cmd not in ['python', 'ai.py']:
                commands.append(cmd)
    
    return commands

def main():
    print("🔍 SIMPLE TOOL TESTER - Actually Testing Commands")
    print("=" * 60)
    
    # Get actual commands
    commands = get_actual_commands()
    print(f"Found {len(commands)} commands in ai.py")
    
    # Test each one
    results = {}
    for cmd in commands:
        print(f"\nTesting: {cmd}")
        result = test_basic_command(cmd)
        results[cmd] = result
        print(f"  Status: {result['status']}")
        if "output" in result:
            print(f"  Output: {result['output']}")
    
    # Summary
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    working = sum(1 for r in results.values() if r["status"] == "✅ Working")
    partial = sum(1 for r in results.values() if "Partial" in r["status"])
    broken = sum(1 for r in results.values() if "❌" in r["status"])
    
    print(f"✅ Working: {working}")
    print(f"⚠️  Partial: {partial}")
    print(f"❌ Broken: {broken}")
    print(f"Total: {len(results)}")
    
    # Save results
    output_path = Path(r"C:\Users\bartl\dev\dj2") / "ai_context" / "simple_audit.json"
    with open(output_path, 'w') as f:
        json.dump({
            "commands": commands,
            "results": results,
            "summary": {
                "working": working,
                "partial": partial,
                "broken": broken,
                "total": len(results)
            }
        }, f, indent=2)
    
    print(f"\n📄 Saved to: {output_path}")

if __name__ == "__main__":
    main()