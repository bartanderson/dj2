# tools/analysis/guardrails.py
"""
Real guardrails implementation using your existing AST analyzer
Validates code against AI Contract rules
"""

import subprocess
import sys
from pathlib import Path
import json
import sqlite3

def safe_read_file(file_path, max_lines=100):
    """Safely read a file with multiple encoding fallbacks"""
    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read(max_lines * 200)  # Read approximate number of characters
                return content
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    
    # If all encodings fail, try binary with replacement
    try:
        with open(file_path, 'rb') as f:
            binary = f.read(max_lines * 200)
            return binary.decode('utf-8', errors='replace')
    except Exception as e:
        return f"[ERROR reading file: {e}]"

def check_ai_contract():
    """Check AI contract violations using existing ast_analyzer"""
    project_root = Path.cwd()
    
    print("🔍 Checking AI Contract Guardrails...")
    print("Rule 1: AI NEVER owns state")
    print("Rule 2: AI NEVER mutates state directly")
    print("Rule 3: AI ONLY requests actions via interfaces")
    print("-" * 50)
    
    # Use your existing ast_analyzer in violations mode
    cmd = [sys.executable, "tools/analysis/ast_analyzer.py", ".", 
           "--mode", "violations"]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )
        
        violations = []  # initialize here
        
        if result.returncode == 0:
            # Parse output for AI contract violations
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
            
            # ===== MOVED BLOCK STARTS HERE =====
            # Check for direct SessionSystem calls in AI files using scout.db (path‑based layers)
            print("Checking for direct state mutations in AI files (via path prefixes)...")
            db_path = project_root / "ai_context" / "scout.db"
            ai_files = []
            if db_path.exists():
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    # Layers considered AI: world, dungeon_neo, engine, ai
                    layers = ['world', 'dungeon_neo', 'engine', 'ai']
                    conditions = []
                    for layer in layers:
                        # Use REPLACE to handle Windows backslashes
                        conditions.append(f"REPLACE(path, '\\', '/') LIKE '{layer}/%'")
                    sql = "SELECT path FROM files WHERE " + " OR ".join(conditions)
                    cursor.execute(sql)
                    ai_files = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    print(f"  Found {len(ai_files)} AI-layer files in DB")
                except Exception as e:
                    print(f"  Warning: Could not query scout.db: {e}")
            else:
                print("  Warning: scout.db not found – run arch_recon --scout first")

            # Perform the checks
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
                    print(f"  Warning: Could not check {file_path}: {e}")
                    continue
            # ===== MOVED BLOCK ENDS HERE =====

            # Report results
            if violations:
                print(f"⚠️  Found {len(violations)} AI contract violations:")
                for i, v in enumerate(violations[:10], 1):  # Show top 10
                    print(f"\n{i}. {v['type']}")
                    print(f"   File: {v['file']}:{v['line']}")
                    print(f"   Rule: {v['rule']}")
                    print(f"   Issue: {v['message']}")
                
                # Save to JSON for context system
                violations_file = project_root / "ai_context" / "guardrail_violations.json"
                with open(violations_file, 'w', encoding='utf-8') as f:
                    json.dump(violations, f, indent=2, ensure_ascii=False)
                print(f"\n📁 Violations saved to: {violations_file}")
            else:
                print("✅ No AI contract violations found!")
            
            return len(violations)
            
        else:
            print(f"❌ Error running guardrails: {result.stderr}")
            return -1
            
    except Exception as e:
        print(f"❌ Exception in guardrails: {e}")
        import traceback
        traceback.print_exc()
        return -1

def main():
    """Command-line entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Contract Guardrails Check")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON")
    parser.add_argument("--save", "-s", action="store_true", help="Save to file")
    
    args = parser.parse_args()
    
    violation_count = check_ai_contract()
    
    if args.json:
        print(json.dumps({"violation_count": violation_count}))
    
    sys.exit(0 if violation_count == 0 else 1)

if __name__ == "__main__":
    main()