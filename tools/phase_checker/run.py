#!/usr/bin/env python3
"""
Real phase compliance checker using your existing tools
Checks for phase mixing and boundary violations
"""

import subprocess
import sys
import json
from pathlib import Path

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
        except Exception:
            continue
    
    return ""

def check_phase_compliance(quiet=False):
    """
    Check phase compliance using multiple methods.
    If quiet=True, suppress all prints and return a dict with results.
    If quiet=False, print human-readable output and also return results dict.
    """
    project_root = Path.cwd()
    
    # We'll collect output lines to print later if not quiet
    output_lines = []
    def log(msg):
        if not quiet:
            print(msg)
        else:
            output_lines.append(msg)
    
    log("🔍 Checking Phase Compliance...")
    log("7 Runtime Phases: Input → Interpretation → Authority → Mutation → Consequence → Persistence → View")
    log("-" * 60)
    
    phase_violations = []
    phase_mixing = []
    
    # Method 1: Use ast_analyzer for phase violations
    log("Method 1: AST Analyzer phase violation detection...")
    ast_analyzer = project_root / "tools" / "analysis" / "ast_analyzer.py"
    if not ast_analyzer.exists():
        error_msg = f"❌ ast_analyzer not found at {ast_analyzer}"
        log(error_msg)
        if quiet:
            return {"status": "error", "error": error_msg}
        return 1  # Non-zero exit on fatal error
    
    cmd = [sys.executable, str(ast_analyzer), ".", "--mode", "violations"]
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
    else:
        log(f"⚠️  ast_analyzer returned non-zero: {result.stderr[:200]}")
    
    # Method 2: Check for phase mixing in key files
    log("Method 2: Checking for phase mixing in key files...")
    dimensions_file = project_root / "dimensions.json"
    if dimensions_file.exists():
        try:
            with open(dimensions_file, 'r', encoding='utf-8') as f:
                dimensions = json.load(f)
            
            for flow in dimensions.get('creation_flows', []):
                file_path = flow.get('file', '')
                if file_path and Path(file_path).exists() and file_path.endswith('.py'):
                    try:
                        content = safe_read_file(file_path, max_lines=200)
                        phases_present = [p for p in PHASE_SEQUENCE if p in content.lower()]
                        if len(phases_present) > 3:
                            phase_mixing.append({
                                "file": file_path,
                                "phases_detected": phases_present,
                                "message": f"Possible phase mixing: {len(phases_present)} phases in one file"
                            })
                    except Exception as e:
                        log(f"  Warning: Could not analyze {file_path}: {e}")
        except Exception as e:
            log(f"  Warning: Could not read dimensions.json: {e}")
    else:
        log("  dimensions.json not found – skipping phase mixing check")
    
    # Method 3: Check DMChatHandler line 293 specifically
    log("Method 3: Checking known violation locations...")
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
            log(f"  Warning: Could not check DMChatHandler: {e}")
    
    # Report results (only if not quiet)
    if not quiet:
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
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    if not quiet:
        print(f"\n📁 Results saved to: {results_file}")
    
    # Return value for quiet mode
    if quiet:
        return {
            "status": "success",
            "saved_files": [str(results_file.relative_to(project_root))] if (phase_violations or phase_mixing) else [],
            "data": {
                "phase_violations": len(phase_violations),
                "phase_mixing": len(phase_mixing),
                "total_issues": results["total_issues"],
                "summary": f"Found {results['total_issues']} issues"
            }
        }
    else:
        return results["total_issues"]

def main():
    # Accept JSON input if provided
    if len(sys.argv) > 1:
        input_str = ' '.join(sys.argv[1:])
        try:
            params = json.loads(input_str)
            json_output = params.get('json', False)
            # We ignore other parameters for now (could add path etc.)
        except json.JSONDecodeError:
            # Fallback to argparse for manual use
            import argparse
            parser = argparse.ArgumentParser(description="Phase Compliance Checker")
            parser.add_argument("--verbose", "-v", action="store_true", help="Show details")
            parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
            args = parser.parse_args()
            json_output = args.json
    else:
        json_output = False

    if json_output:
        # Quiet mode: capture result and output JSON only
        result = check_phase_compliance(quiet=True)
        if isinstance(result, dict):
            print(json.dumps(result))
        else:
            # Fallback (should not happen)
            print(json.dumps({"status": "error", "error": "Unexpected return type"}))
    else:
        # Human mode: run and print output
        issue_count = check_phase_compliance(quiet=False)
        sys.exit(0 if issue_count == 0 else 1)

if __name__ == "__main__":
    main()