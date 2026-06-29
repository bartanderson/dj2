#!/usr/bin/env python3
# coding=utf-8
"""
CONTEXT MANAGER - Load docs and files, send to AI
Attempts full context, only chunks if interface fails
"""

import os
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

PROJECT_ROOT = Path(r"C:\Users\bartl\dev\dj2")
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))
import dungeon_neo.llm_client as llm_client

class ContextManager:
    def __init__(self, verbose: bool = False):
        self.project_root = PROJECT_ROOT
        self.verbose = verbose
        self.ai_context = PROJECT_ROOT / "ai_context"
        self.session_dir = self.ai_context / "session"
        self.session_dir.mkdir(exist_ok=True)
        
        if self.verbose:
            print(f"[VERBOSE] ContextManager initialized")
            print(f"[VERBOSE] Project root: {PROJECT_ROOT}")
            print(f"[VERBOSE] Session dir: {self.session_dir}")
        
    def _vlog(self, msg: str):
        """Log verbose message if verbose mode enabled"""
        if self.verbose:
            print(f"[VERBOSE] {msg}")
        
    def clean_ascii(self, text: str) -> str:
        if not text:
            return text
        
        original_len = len(text)
        fix_count = 0
        
        fixes = {
            '├ó┼ôΓÇª': '...', '├ó┼ôΓÇÜ': ',', '├óΓÇ¥': '"', '├óΓÇ₧': '"',
            '├óΓÇÖ': "'", 'ΓåÆ': '->', 'ΓåÉ': '<-', 'ΓÇ£': '"', 'ΓÇ¥': '"',
            'ΓÇÿ': "'", 'ΓÇÖ': "'", 'ΓÇö': '-', 'ΓÇô': '-', 'ΓÇª': '...',
            '→': '->', '←': '<-', '✓': '[OK]', '✅': '[OK]', '⚠': '[WARN]',
            '🔍': '[SEARCH]', '🏗': '[BUILD]', '💾': '[SAVE]', '📝': '[NOTE]',
            '📋': '[DOC]', '🔧': '[TOOL]', '🎯': '[FOCUS]', '💻': '[CODE]',
            '✅': '[OK]', '❌': '[FAIL]', '•': '*', '—': '-', '…': '...',
        }
        
        for bad, good in fixes.items():
            if bad in text:
                count = text.count(bad)
                text = text.replace(bad, good)
                fix_count += count
        
        non_ascii = sum(1 for c in text if ord(c) >= 128)
        result = ''.join(c if ord(c) < 128 else '?' for c in text)
        
        if self.verbose and (fix_count > 0 or non_ascii > 0):
            self._vlog(f"ASCII cleanup: {fix_count} mojibake fixes, {non_ascii} non-ASCII chars -> '?'")
            self._vlog(f"ASCII cleanup: {original_len} -> {len(result)} chars")
            
        return result
        
    def load_system_docs(self) -> dict:
        docs = {}
        
        if self.verbose:
            self._vlog("Loading system documents...")
        
        contract_file = self.ai_context / "ai_contract.md"
        if contract_file.exists():
            content = contract_file.read_text(encoding='utf-8')
            docs["ai_contract"] = self.clean_ascii(content)
            self._vlog(f"Loaded ai_contract.md: {len(content)} chars")
        else:
            docs["ai_contract"] = "[ERROR: ai_contract.md not found]"
            self._vlog("WARNING: ai_contract.md not found")
        
        playbook_file = self.ai_context / "development_playbook.md"
        if playbook_file.exists():
            content = playbook_file.read_text(encoding='utf-8')
            docs["playbook"] = self.clean_ascii(content) + "\n...[truncated]"
            self._vlog(f"Loaded development_playbook.md: {len(content)} chars")
        else:
            docs["playbook"] = "[Playbook not found]"
            self._vlog("WARNING: development_playbook.md not found")
        
        tool_file = self.ai_context / "tool_index.json"
        if tool_file.exists():
            with open(tool_file, 'r') as f:
                tools = json.load(f)
            tool_list = []
            tested_count = 0
            for cat, items in tools.items():
                for name, info in items.items():
                    status = "OK" if info.get("tested") else "UNTESTED"
                    if info.get("tested"):
                        tested_count += 1
                    tool_list.append(f"{cat}/{name} [{status}]")
            docs["tools"] = "\n".join(tool_list)
            self._vlog(f"Loaded tool_index.json: {len(tool_list)} tools ({tested_count} tested)")
        else:
            docs["tools"] = "[No tools registry]"
            self._vlog("WARNING: tool_index.json not found")
        
        status_file = self.ai_context / "status_manifest.json"
        if status_file.exists():
            with open(status_file, 'r') as f:
                status = json.load(f)
            current = []
            phase_count = 0
            for phase, info in status.get("phases", {}).items():
                if info.get("status") in ["in_progress", "blocked"]:
                    current.append(f"{phase}: {info['status']} -> {info.get('next_action', 'TBD')}")
                    phase_count += 1
            docs["status"] = "\n".join(current) if current else "[No active work]"
            self._vlog(f"Loaded status_manifest.json: {phase_count} active phases")
        else:
            docs["status"] = "[No status file]"
            self._vlog("WARNING: status_manifest.json not found")
            
        return docs

    def extract_code(self, query: str, max_lines: int = 100) -> dict:
        """
        Extract code using JSON search wrapper
        """
        self._vlog(f"extract_code called with query: '{query}'")
        
        try:
            # Import the JSON search
            import sys
            sys.path.insert(0, str(self.project_root / "tools"))
            from json_search import search_to_json
            
            # Get search results as JSON
            results = search_to_json(query, limit=10)
            
            if not results:
                self._vlog(f"No search results for '{query}'")
                return {
                    "files": [],
                    "strategy": "no_results",
                    "content": f"No search results for: '{query}'",
                    "total_files_found": 0
                }
            
            # Filter for Python files that exist
            python_files = [r for r in results if r['is_python'] and r['exists']]
            
            if not python_files:
                self._vlog(f"No Python files found. All results: {[r['file'] for r in results]}")
                return {
                    "files": [],
                    "strategy": "no_python_files",
                    "content": f"Found {len(results)} files but none are Python",
                    "total_files_found": len(results)
                }
            
            self._vlog(f"Found {len(python_files)} Python files")
            
            # Extract code from top Python files
            extracted_content = ""
            extracted_files = []
            
            for result in python_files[:5]:  # Top 5 Python files
                file_path = result['file']
                score = result['score']
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    
                    lines = content.split('\n')
                    total_lines = len(lines)
                    
                    # Decide how much to include
                    if total_lines <= max_lines:
                        # Include full file
                        snippet = content
                        header = f"[FILE: {file_path}] (full file, {total_lines} lines, score: {score:.2f})"
                    else:
                        # Include first max_lines lines
                        snippet = '\n'.join(lines[:max_lines])
                        header = f"[FILE: {file_path}] (first {max_lines} of {total_lines} lines, score: {score:.2f})"
                    
                    extracted_content += f"\n{'-'*60}\n{header}\n{'-'*60}\n{snippet}\n"
                    extracted_files.append(file_path)
                    
                except Exception as e:
                    self._vlog(f"Error reading {file_path}: {e}")
                    continue
            
            return {
                "files": extracted_files,
                "strategy": "search_success",
                "content": extracted_content,
                "total_files_found": len(python_files)
            }
            
        except Exception as e:
            self._vlog(f"Error in extract_code: {e}")
            import traceback
            traceback.print_exc()
            return {
                "files": [],
                "strategy": "error",
                "content": f"Error: {e}"
            }
    
    def get_violations(self) -> str:
        """Check for phase violations"""
        self._vlog("Checking for phase violations...")
        try:
            cmd = [sys.executable, "ai.py", "violations", "."]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                violations = self.clean_ascii(result.stdout[:1000]) if result.stdout else "No violations detected"
                self._vlog(f"Violations check complete: {len(violations)} chars")
                return violations
            return "[Could not run violations check]"
        except Exception as e:
            self._vlog(f"Violations check failed: {e}")
            return f"[Error: {e}]"
    
    def load_code_file(self, filepath: Path, max_lines: int = 200) -> str:
        """Load file with line limit"""
        if not filepath.exists():
            self._vlog(f"File not found: {filepath}")
            return f"[File not found: {filepath}]"
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            content = ''.join(lines[:max_lines])
            
            if len(lines) > max_lines:
                content += f"\n...[truncated at {max_lines} lines]"
                self._vlog(f"Loaded {filepath.name}: {total_lines} lines -> truncated to {max_lines}")
            else:
                self._vlog(f"Loaded {filepath.name}: {total_lines} lines (no truncation)")
                
            return content
            
        except Exception as e:
            self._vlog(f"Error reading {filepath}: {e}")
            return f"[Error reading {filepath}: {e}]"
    
    def build_context(self, query: str, include_files: bool = True) -> str:
        print(f"[BUILD] Building context for: {query}")
        
        if self.verbose:
            self._vlog(f"Query: '{query}'")
            self._vlog(f"Include files: {include_files}")
        
        docs = self.load_system_docs()
        
        # Get violations
        violations = self.get_violations()
        
        # Get smart code extraction if requested
        code_info = {"files": 0, "context": "Files not requested"}
        if include_files:
            code_info = self.extract_code(query)

        # Use the correct key 'content' instead of 'context'
        code_content = code_info.get('content', '')
        
        parts = [
            "=" * 80,
            "DUNGEON JOURNEY 2 - CONTEXT PACKAGE",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Query: {query}",
            "=" * 80,
            "",
            "[CORE CONSTRAINTS]",
            docs["ai_contract"],
            "",
            "[DEVELOPMENT PLAYBOOK]",
            docs["playbook"],
            "",
            "[TOOLS]",
            docs["tools"],
            "",
            "[STATUS]",
            docs["status"],
            "",
            "[WARN] PHASE VIOLATIONS",
            violations,
            "",
            f"[CODE] RELEVANT CODE ({code_info['files']} files found)",
            f"Extraction: {code_info.get('strategy', 'N/A')}",
            code_content,
        ]
        
        full_context = "\n".join(parts)
        token_estimate = len(full_context) // 4
        
        if self.verbose:
            self._vlog(f"Context breakdown:")
            self._vlog(f"  - Core constraints: {len(docs['ai_contract'])} chars")
            self._vlog(f"  - Playbook: {len(docs['playbook'])} chars")
            self._vlog(f"  - Tools list: {len(docs['tools'])} chars")
            self._vlog(f"  - Status: {len(docs['status'])} chars")
            self._vlog(f"  - Violations: {len(violations)} chars")
            self._vlog(f"  - Code: {len(code_info.get('content', ''))} chars")
            self._vlog(f"  - Total size: {len(full_context)} chars")
            self._vlog(f"  - Token estimate: ~{token_estimate}")
        
        print(f"[INFO] Context size: {len(full_context)} chars ({token_estimate} estimated tokens)")
        return full_context

    def build_package(self, query: str, target: str = "deepseek", max_tokens: int = 10000) -> dict:
        """
        Build a structured context package (compatibility with ai_workflow.py)
        Uses smart code extraction
        """
        self._vlog(f"build_package called: target={target}, max_tokens={max_tokens}")
        
        # Load docs
        docs = self.load_system_docs()
        
        # Get violations
        violations = self.get_violations()
        
        # Smart code extraction
        code_info = self.extract_code(query)
        
        # Build formatted context based on target
        if target == "deepseek":
            formatted = f"""{'='*80}
DUNGEON JOURNEY 2 - CONTEXT PACKAGE
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Query: {query}
{'='*80}

[DOC] CORE CONSTRAINTS (ai_contract.md)
{docs.get('ai_contract', '[No ai_contract.md]')}

[PLAYBOOK] DEVELOPMENT PLAYBOOK
{docs.get('playbook', '[No playbook]')}

[TOOL] AVAILABLE TOOLS
{docs.get('tools', 'None')}

[FOCUS] CURRENT SYSTEM FOCUS
{docs.get('status', 'No system focus')}

[WARN] PHASE VIOLATIONS
{violations}

[CODE] RELEVANT CODE ({code_info.get('files', 0)} files found)
Extraction: {code_info.get('strategy', 'N/A')}
{code_info.get('content', 'No code')}

{'='*80}
INSTRUCTIONS:
1. Suggest ONLY using tools listed above
2. Respect phase boundaries in constraints
3. If you need a tool not listed, ask "Is there a tool for X?"
{'='*80}"""
        else:
            formatted = f"""Query: {query}
Constraints: AI never mutates state, phases: Input->Interp->Auth->Mutate->Conseq->Persist->View
Tools: {docs.get('tools', 'None')}
Violations: {violations}
Code: {code_info.get('content', 'None')}"""

        # ADD: Include project status for certain queries
        if any(word in query.lower() for word in ["status", "progress", "overview", "dashboard"]):
            try:
                # Get real project status
                from scripts.project_auditor import ProjectAuditor
                auditor = ProjectAuditor()
                project_status = auditor.get_project_status()
                
                if "error" not in project_status:
                    # Add to context
                    status_context = f"""
[PROJECT STATUS]
Completion: {project_status['completion']}%
Phases: {project_status['complete_phases']}/{project_status['total_phases']} complete
Active phases: {', '.join(project_status['active_phases']) if project_status['active_phases'] else 'None'}
"""
                    # Insert after core documentation
                    formatted = formatted.replace("[CODE]", status_context + "\n[CODE]")
            except ImportError:
                pass  # Silently fail if project_auditor not available
        
        
        token_estimate = len(formatted.split())
        actual_tokens_estimate = len(formatted) // 4  # Rough estimate: 1 token ≈ 4 chars
        self._vlog(f"Actual token estimate (char/4): ~{actual_tokens_estimate}")
        self._vlog(f"Word count: {token_estimate}")
        
        # Truncate if over budget
        if token_estimate > max_tokens:
            self._vlog(f"Truncating from {token_estimate} to ~{max_tokens} tokens")
            words = formatted.split()
            truncated_words = words[:max_tokens]
            formatted = " ".join(truncated_words) + "\n...[truncated]"
            token_estimate = len(formatted.split())
        
        self._vlog(f"Package built: {token_estimate} tokens, {len(code_info.get('files', []))} files")
        
        return {
            "formatted": formatted,
            "token_estimate": token_estimate,
            "components": {
                "docs": docs,
                "code": code_info,
                "violations": violations
            }
        }
    
    def send_to_deepseek(self, context: str, keep_open: bool = False) -> str:
        """Send context to DeepSeek via file upload (reliable)."""
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "tools"))
            from bridge.deepseek_bridge_react import DeepSeekBridgeReact as DeepSeekBridge

            print("[BRIDGE] Connecting...")
            self._vlog(f"Initializing DeepSeekBridgeReact")
            bridge = DeepSeekBridge()

            if not bridge.connect():
                print("[FAIL] Could not connect")
                self._vlog("Bridge connection failed")
                return None

            print(f"[BRIDGE] Uploading context ({len(context)} chars)...")
            self._vlog(f"Context size: {len(context)} chars, ~{len(context)//4} tokens")

            # ========== SINGLE FILE UPLOAD ==========
            filename = f"context_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            if bridge.send_via_file_upload(context, filename):
                print("[BRIDGE] File uploaded, waiting for response...")
                response = bridge._wait_for_response(timeout=180)
            else:
                print("[FAIL] File upload failed")
                bridge.close()
                return None
            # =========================================

            if response:
                # Write to fixed name (overwrites previous) – always show
                fixed_file = self.session_dir / "deepseek_response.txt"
                fixed_file.write_text(self.clean_ascii(response), encoding='utf-8')
                print(f"[SAVE] Fixed response: {fixed_file}")

                # Also write a timestamped copy – show only in verbose mode
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                timestamped_file = self.session_dir / f"deepseek_response_{timestamp}.txt"
                timestamped_file.write_text(self.clean_ascii(response), encoding='utf-8')
                self._vlog(f"Archived response: {timestamped_file}")

                return response, timestamped_file
            else:
                return None, None

            if keep_open:
                print("\n[BROWSER LEFT OPEN]")
                print("Close Chrome manually when done reading.")
                self._vlog("Browser left open per request")
            else:
                bridge.close()
                print("[BRIDGE] Closed")
                self._vlog("Bridge closed")

            return response

        except Exception as e:
            print(f"[ERROR] {e}")
            self._vlog(f"Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def save_context(self, context: str, filename: str = "context_for_ai.txt"):
        filepath = self.session_dir / filename
        filepath.write_text(context, encoding='utf-8')
        print(f"[SAVE] {filepath}")
        self._vlog(f"Saved context ({len(context)} chars) to {filepath}")
        return filepath

    def send(self, package: dict, target: str = "auto", keep_open: bool = False) -> tuple[bool, Path | None]:
        if target == "auto":
            estimated_tokens = len(package['formatted']) // 4
            if estimated_tokens < 115000:
                success = self.send_to_llm(package)
                return success, None
            # fallback
            result, path = self.send_to_deepseek(package['formatted'], keep_open)
            return result is not None, path
        elif target in ("llm", "local"):
            success = self.send_to_llm(package)
            return success, None
        else:  # deepseek
            result, path = self.send_to_deepseek(package['formatted'], keep_open)
            return result is not None, path
    
    def send_to_llm(self, package: dict, max_context_chars: int = 393216) -> bool:
        """
        Send context to local llama-server (OpenAI-compatible, localhost:8080).

        Uses unique naming to avoid conflict with DeepSeek files:
        - localctx_for_ai.txt (context)
        - localcur_session.json (current session)
        - local_response.txt (AI response)
        - session_localarch_YYYYMMDD_HHMMSS.json (archive)
        """
        if not llm_client.is_available():
            print("[LLM] llama-server not available at localhost:8080")
            return False

        # Truncate context to fit (98K safe limit)
        full_context = package['formatted']
        if len(full_context) > max_context_chars:
            print(f"[LLM] Truncating: {len(full_context)} -> {max_context_chars} chars")
            truncated = full_context[:max_context_chars]
            truncated += "\n\n[Note: Context truncated. Use DeepSeek for full analysis.]"
        else:
            truncated = full_context

        # Save local context (unique naming)
        local_context_file = self.session_dir / "localctx_for_ai.txt"
        local_response_file = self.session_dir / "local_response.txt"

        with open(local_context_file, 'w', encoding='utf-8') as f:
            f.write(truncated)

        print(f"[LLM] Context saved: {local_context_file}")
        print(f"[LLM] Sending {len(truncated)} chars (~{len(truncated)//4} tokens)...")

        try:
            query = package.get('query', 'Analyze this codebase')

            response_text = llm_client.chat([
                {"role": "system", "content": "You are a senior Python developer. Be specific and actionable."},
                {"role": "user", "content": truncated},
            ])

            if response_text is None:
                print("[LLM] No response received")
                return False

            # Save response
            with open(local_response_file, 'w', encoding='utf-8') as f:
                f.write(f"Query: {query}\n")
                f.write("="*70 + "\n\n")
                f.write(response_text)

            print(f"[LLM] Response saved: {local_response_file}")

            # Archive and save session
            self._archive_local_session()
            self._save_local_session(package, response_text)

            return True

        except Exception as e:
            print(f"[LLM] Error: {e}")
            return False
    
    def _archive_local_session(self):
        """Archive existing local session if present."""
        current_session = self.session_dir / "localcur_session.json"
        
        if current_session.exists():
            try:
                with open(current_session, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_name = f"session_localarch_{timestamp}.json"
                archive_path = self.session_dir / archive_name
                
                with open(archive_path, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2)
                
                print(f"[OLLAMA] Archived: {archive_name}")
            except Exception as e:
                print(f"[OLLAMA] Archive warning: {e}")
    
    def _save_local_session(self, package: dict, response_text: str):
        """Save current local session state."""
        session_file = self.session_dir / "localcur_session.json"
        
        session_data = {
            "topic": package.get('query', 'Unknown'),
            "started": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "context_size": len(package.get('formatted', '')),
            "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
            "backend": "llama-server"
        }

        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
        except Exception as e:
            print(f"[LLM] Session save warning: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", "-q", required=True, help="Topic/question")
    parser.add_argument("--target", "-t", 
                   choices=["auto", "llm", "local", "deepseek"],
                   default="auto",
                   help="AI backend: auto=smart routing, llm/local=llama-server, deepseek=web")
    parser.add_argument("--send", "-s", action="store_true",
                       help="Send to AI (uses --target, default: auto)")
    parser.add_argument("--keep-open", "-k", action="store_true", help="Leave browser open")
    parser.add_argument("--no-files", action="store_true", help="Docs only")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("-o", help="Output filename")
    
    args = parser.parse_args()
    
    mgr = ContextManager(verbose=args.verbose)
    context = mgr.build_context(args.query, include_files=not args.no_files)
    
    print(f"\n[OK] Context: {len(context)} chars")
    
    if args.send or args.target != "auto":
        # Build package for send() method
        package = mgr.build_package(args.query, target="llm" if args.target in ("llm", "local", "auto") else "deepseek")
        
        success = mgr.send(package, target=args.target, keep_open=args.keep_open)
        
        if success:
            print("\n[DONE] Complete")
        else:
            print("\n[FALLBACK] Failed, saving to file")
            mgr.save_context(context)
    else:
        filename = args.o or "context_for_ai.txt"
        mgr.save_context(context, filename)
        print(f"\n[READY] {filename}")

if __name__ == "__main__":
    main()