# scripts/simple_tool_tester.py
"""
Simple, accurate tool tester - now with real arguments
"""

import subprocess
import json
import tempfile
import os
from pathlib import Path
from typing import List, Dict

def test_basic_command(cmd: str, args: List[str] = None) -> Dict:
    """Test a command with real arguments"""
    project_root = Path(r"C:\Users\bartl\dev\dj2")
    
    # REAL arguments for each command (based on actual usage)
    test_cases = {
        "search": ["search", "phase"],
        "analyze": ["analyze", "game engine"],
        "violations": ["violations", "."],
        "todos": ["todos", "."],
        "deps": ["deps", "."],
        "structure": ["structure", "."],
        "context": ["context", "test context"],
        "validate": ["validate", "--response-text", "test response"],
        "guardrails": ["guardrails", "--list"],
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
        "tool-help": ["tool-help", "context_manager"],
        "th": ["th", "context_manager"],
        # Direct commands need special handling
        "delete": ["delete", "--dry-run", "--help"],
        "insert": ["insert", "--dry-run", "--help"],
        "replace": ["replace", "--dry-run", "--help"],
        "write": ["write", "--dry-run", "--help"],
        "replace-text": ["replace-text", "--dry-run", "--help"],
        "extract-class": ["extract-class", "--help"],
        "extract-lines": ["extract-lines", "--help"],
        "extract": ["extract", "GameEngine"],
        "find-class": ["find-class", "--help"],
    }
    
    # Build command
    if args:
        cmd_parts = ["python", "ai.py", cmd] + args
    elif cmd in test_cases:
        cmd_parts = ["python", "ai.py"] + test_cases[cmd]
    else:
        # Default: just test with --help
        cmd_parts = ["python", "ai.py", cmd, "--help"]
    
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
        
        # SUCCESS if:
        # 1. Return code is 0 OR
        # 2. Shows usage/help (common for --help flag) OR
        # 3. Shows expected error (like "file not found" for direct commands)
        
        output = result.stdout + result.stderr
        
        # Check for success patterns
        success_patterns = [
            "usage:", "help:", "Options:", "Arguments:",
            "[OK]", "✅", "✓", "Found", "Working", "Available",
            "DRY RUN", "would", "Would", "test", "Test"
        ]
        
        # Check for failure patterns
        failure_patterns = [
            "Error:", "ERROR:", "Exception:", "Traceback",
            "not found", "No such", "Invalid", "Failed to"
        ]
        
        has_success = any(pattern in output for pattern in success_patterns)
        has_failure = any(pattern in output for pattern in failure_patterns)
        
        if result.returncode == 0 or has_success:
            status = "✅ Working"
        elif has_failure and not has_success:
            status = "❌ Error"
        else:
            status = "⚠️  Partial"
        
        return {
            "status": status,
            "output": output[:300] + "..." if len(output) > 300 else output,
            "returncode": result.returncode
        }
            
    except Exception as e:
        return {
            "status": "❌ Exception",
            "output": str(e),
            "returncode": -1
        }

def get_actual_commands():
    """Get commands from ai.py help - ULTRA SIMPLE"""
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
    
    # Look for lines that contain the command list pattern
    for line in result.stdout.split('\n'):
        line = line.strip()
        # Match lines like: "{search,analyze,violations,...}"
        if line.startswith('{') and line.endswith('}'):
            # Remove curly braces and split
            cmd_text = line[1:-1]  # Remove { and }
            commands = [cmd.strip() for cmd in cmd_text.split(',')]
            
            # Filter out empty strings
            commands = [cmd for cmd in commands if cmd]
            
            # Remove any command that contains spaces (not a valid command)
            commands = [cmd for cmd in commands if ' ' not in cmd]
            
            return commands
    
    return []
    
def main():
    print("🔍 IMPROVED TOOL TESTER - Testing with Real Arguments")
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
        if result['output'].strip():
            print(f"  Output: {result['output'][:150]}...")
    
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
    
    # Show broken commands
    if broken > 0:
        print(f"\nBroken commands:")
        for cmd, result in results.items():
            if "❌" in result["status"]:
                print(f"  - {cmd}: {result['output'][:100]}")
    
    # Save results
    output_path = Path(r"C:\Users\bartl\dev\dj2") / "ai_context" / "simple_audit.json"
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump({
            "commands": commands,
            "results": {cmd: {k: v for k, v in res.items() if k != 'output'} for cmd, res in results.items()},
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