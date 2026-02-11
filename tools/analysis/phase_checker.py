# tools/analysis/phase_checker.py
"""
Real phase compliance checker using your existing tools
Checks for phase mixing and boundary violations
"""

import subprocess
import sys
from pathlib import Path
import json

PHASE_SEQUENCE = ['input', 'interpretation', 'authority', 'mutation', 'consequence', 'persistence', 'view']

def safe_read_file(file_path, max_lines=None):
    """Safely read a file with multiple encoding fallbacks"""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            if max_lines:
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line)
                    return ''.join(lines)
            else:
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            continue
    
    # If all encodings fail, return empty
    return ""

def check_phase_compliance():
    """Check phase compliance using multiple methods"""
    project_root = Path.cwd()
    
    print("🔍 Checking Phase Compliance...")
    print("7 Runtime Phases: Input → Interpretation → Authority → Mutation → Consequence → Persistence → View")
    print("-" * 60)
    
    phase_violations = []
    phase_mixing = []
    
    # Method 1: Use your ast_analyzer for phase violations
    print("Method 1: AST Analyzer phase violation detection...")
    cmd = [sys.executable, "tools/analysis/ast_analyzer.py", ".", "--mode", "violations"]
    
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    
    if result.returncode == 0:
        for line in result.stdout.split('\n'):
            if 'PHASE_VIOLATION' in line or 'DIRECT_AI_CALL' in line:
                parts = line.strip().split(':', 3)
                if len(parts) >= 4:
                    phase_violations.append({
                        "file": parts[0].strip(),
                        "line": parts[1].strip(),
                        "type": "Phase boundary violation" if 'PHASE_VIOLATION' in line else "AI direct call",
                        "message": parts[3].strip()[:200]
                    })
    
    # Method 2: Check for phase mixing in key files
    print("Method 2: Checking for phase mixing in key files...")
    
    # Get files from your dimensions system
    dimensions_file = project_root / "dimensions.json"
    if dimensions_file.exists():
        try:
            with open(dimensions_file, 'r', encoding='utf-8') as f:
                dimensions = json.load(f)
            
            # Check creation_flows for phase mixing
            for flow in dimensions.get('creation_flows', []):
                file_path = flow.get('file', '')
                if file_path and Path(file_path).exists() and file_path.endswith('.py'):
                    try:
                        content = safe_read_file(file_path, max_lines=200)
                        
                        phases_present = []
                        for phase in PHASE_SEQUENCE:
                            if phase in content.lower():
                                phases_present.append(phase)
                        
                        if len(phases_present) > 3:  # Heuristic: >3 phases in one file
                            phase_mixing.append({
                                "file": file_path,
                                "phases_detected": phases_present,
                                "message": f"Possible phase mixing: {len(phases_present)} phases in one file"
                            })
                    except Exception as e:
                        print(f"  Warning: Could not analyze {file_path}: {e}")
        except Exception as e:
            print(f"  Warning: Could not read dimensions.json: {e}")
    
    # Method 3: Check DMChatHandler line 293 specifically (from your audit)
    print("Method 3: Checking known violation locations...")
    dm_chat_file = project_root / "world" / "dm_chat_ai.py"
    if dm_chat_file.exists():
        try:
            content = safe_read_file(dm_chat_file, max_lines=300)
            lines = content.split('\n')
            
            if len(lines) >= 293:
                line_293 = lines[292].strip()
                if 'extract_conversation_context' in line_293 and ('session' in line_293.lower() or 'state' in line_293.lower()):
                    phase_violations.append({
                        "file": str(dm_chat_file),
                        "line": "293",
                        "type": "Known violation (from audit)",
                        "message": f"DMChatHandler line 293: {line_293[:100]}..."
                    })
        except Exception as e:
            print(f"  Warning: Could not check DMChatHandler: {e}")
    
    # Report results
    print(f"\n📊 Phase Compliance Report:")
    print(f"  Phase boundary violations: {len(phase_violations)}")
    print(f"  Phase mixing warnings: {len(phase_mixing)}")
    
    if phase_violations:
        print("\n⚠️  Phase boundary violations:")
        for i, v in enumerate(phase_violations[:5], 1):
            print(f"  {i}. {v['file']}:{v['line']}")
            print(f"     {v['type']}")
            print(f"     {v['message']}")
    
    if phase_mixing:
        print("\n⚠️  Phase mixing warnings (multiple phases in single file):")
        for i, m in enumerate(phase_mixing[:3], 1):
            print(f"  {i}. {m['file']}")
            print(f"     Phases detected: {', '.join(m['phases_detected'])}")
            print(f"     {m['message']}")
    
    if not phase_violations and not phase_mixing:
        print("\n✅ All phase checks passed!")
    
    # Save results for context system
    results = {
        "phase_violations": phase_violations,
        "phase_mixing": phase_mixing,
        "total_issues": len(phase_violations) + len(phase_mixing)
    }
    
    results_file = project_root / "ai_context" / "phase_check_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Results saved to: {results_file}")
    
    return len(phase_violations) + len(phase_mixing)

def main():
    """Command-line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Phase Compliance Checker")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
    
    args = parser.parse_args()
    
    issue_count = check_phase_compliance()
    
    if args.json:
        print(json.dumps({"issue_count": issue_count}))
    
    sys.exit(0 if issue_count == 0 else 1)

if __name__ == "__main__":
    main()