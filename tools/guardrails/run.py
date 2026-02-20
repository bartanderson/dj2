#!/usr/bin/env python3
"""
Real guardrails implementation using your existing AST analyzer
Validates code against AI Contract rules
"""

import subprocess
import sys
import json
import sqlite3
from pathlib import Path
import contextlib
import io

def safe_read_file(file_path, max_lines=100):
    """Safely read a file with multiple encoding fallbacks"""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read(max_lines * 200)
                return content
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    
    try:
        with open(file_path, 'rb') as f:
            binary = f.read(max_lines * 200)
            return binary.decode('utf-8', errors='replace')
    except Exception as e:
        return f"[ERROR reading file: {e}]"

def check_ai_contract(project_root=None, quiet=False):
    """
    Check AI contract violations.
    If quiet=True, suppress all prints and return a dict with results.
    If quiet=False, print human-readable output and also return results.
    """
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root)
    
    # We'll collect output in a list to print later if not quiet
    output_lines = []
    
    def log(msg):
        if not quiet:
            print(msg)
        else:
            output_lines.append(msg)
    
    log("🔍 Checking AI Contract Guardrails...")
    log("Rule 1: AI NEVER owns state")
    log("Rule 2: AI NEVER mutates state directly")
    log("Rule 3: AI ONLY requests actions via interfaces")
    log("-" * 50)
    
    # Use ast_analyzer in violations mode
    ast_analyzer = project_root / "tools" / "analysis" / "ast_analyzer.py"
    if not ast_analyzer.exists():
        error_msg = f"❌ ast_analyzer not found at {ast_analyzer}"
        log(error_msg)
        if quiet:
            return {"error": error_msg, "status": "error"}
        return -1, None
    
    cmd = [sys.executable, str(ast_analyzer), ".", "--mode", "violations"]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )
        
        violations = []
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            
            for line in lines:
                if 'DIRECT_AI_CALL' in line:
                    parts = line.strip().split(':', 3)
                    if len(parts) >= 4:
                        violations.append({
                            "type": "AI_CONTRACT_VIOLATION",
                            "rule": "AI NEVER mutates state directly",
                            "file": parts[0].strip(),
                            "line": parts[1].strip(),
                            "message": f"Direct AI call detected: {parts[3].strip()}"
                        })
                elif 'PHASE_VIOLATION' in line:
                    parts = line.strip().split(':', 3)
                    if len(parts) >= 4:
                        violations.append({
                            "type": "PHASE_BOUNDARY_VIOLATION",
                            "rule": "Never skip, never reverse, never combine adjacent phases",
                            "file": parts[0].strip(),
                            "line": parts[1].strip(),
                            "message": f"Phase violation: {parts[3].strip()}"
                        })
            
            # Check for direct SessionSystem calls in AI files using scout.db
            log("Checking for direct state mutations in AI files (via path prefixes)...")
            db_path = project_root / "ai_context" / "scout.db"
            ai_files = []
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    layers = ['world', 'dungeon_neo', 'engine', 'ai']
                    conditions = []
                    for layer in layers:
                        conditions.append(f"REPLACE(path, '\\', '/') LIKE '{layer}/%'")
                    sql = "SELECT path FROM files WHERE " + " OR ".join(conditions)
                    cursor.execute(sql)
                    ai_files = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    log(f"  Found {len(ai_files)} AI-layer files in DB")
                except Exception as e:
                    log(f"  Warning: Could not query scout.db: {e}")
            else:
                log("  Warning: scout.db not found – run arch_recon --scout first")

            for file_path in ai_files:
                full_path = project_root / file_path
                if not full_path.exists():
                    continue
                try:
                    content = safe_read_file(str(full_path))
                    if 'SessionSystem' in content and ('save' in content.lower() or 'update' in content.lower()):
                        violations.append({
                            "type": "STATE_OWNERSHIP_VIOLATION",
                            "rule": "AI NEVER owns state",
                            "file": file_path,
                            "line": "multiple",
                            "message": "AI file directly accesses SessionSystem"
                        })
                except Exception as e:
                    log(f"  Warning: Could not check {file_path}: {e}")
                    continue

            # Save to JSON file
            violations_file = project_root / "ai_context" / "guardrail_violations.json"
            violations_file.parent.mkdir(parents=True, exist_ok=True)
            with open(violations_file, 'w', encoding='utf-8') as f:
                json.dump(violations, f, indent=2, ensure_ascii=False)
            
            # Report results
            if violations:
                log(f"⚠️  Found {len(violations)} AI contract violations:")
                for i, v in enumerate(violations[:10], 1):
                    log(f"\n{i}. {v['type']}")
                    log(f"   File: {v['file']}:{v['line']}")
                    log(f"   Rule: {v['rule']}")
                    log(f"   Issue: {v['message']}")
                log(f"\n📁 Violations saved to: {violations_file}")
            else:
                log("✅ No AI contract violations found!")
            
            # Return value
            if quiet:
                return {
                    "status": "success",
                    "saved_files": [str(violations_file.relative_to(project_root))] if violations else [],
                    "data": {
                        "violation_count": len(violations),
                        "summary": f"Found {len(violations)} violations" if violations else "No violations"
                    }
                }
            else:
                return len(violations), str(violations_file) if violations else None
        else:
            error_msg = f"❌ Error running ast_analyzer: {result.stderr}"
            log(error_msg)
            if quiet:
                return {"status": "error", "error": error_msg}
            return -1, None
            
    except Exception as e:
        error_msg = f"❌ Exception in guardrails: {e}"
        log(error_msg)
        import traceback
        traceback.print_exc()
        if quiet:
            return {"status": "error", "error": error_msg}
        return -1, None

def main():
    # Accept JSON input from concatenated arguments (if any)
    if len(sys.argv) > 1:
        input_str = ' '.join(sys.argv[1:])
        try:
            params = json.loads(input_str)
            json_output = params.get('json', False)
            save_output = params.get('save', False)
            project_root = params.get('project_root', None)
            quiet = True  # In JSON mode, suppress human output
        except json.JSONDecodeError:
            # Fallback to argparse for manual use
            import argparse
            parser = argparse.ArgumentParser(description="AI Contract Guardrails Check")
            parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
            parser.add_argument("--save", "-s", action="store_true", help="Save to file")
            parser.add_argument("--project-root", help="Project root directory")
            args = parser.parse_args()
            json_output = args.json
            save_output = args.save
            project_root = args.project_root
            quiet = json_output
    else:
        json_output = False
        save_output = False
        project_root = None
        quiet = False

    if json_output:
        # Quiet mode, capture result and output JSON only
        result = check_ai_contract(project_root, quiet=True)
        # Ensure result is a dict
        if isinstance(result, dict):
            print(json.dumps(result))
        else:
            # In case of fallback (old return style), wrap it
            print(json.dumps({"status": "success", "data": {"violation_count": result[0]}}))
    else:
        # Human mode: run normally, print output
        violation_count, saved_to = check_ai_contract(project_root, quiet=False)
        if saved_to:
            print(f"\n✅ Results saved to: {saved_to}")
        sys.exit(0 if violation_count == 0 else 1)

if __name__ == "__main__":
    main()