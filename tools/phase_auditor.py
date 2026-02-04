# tools/phase_auditor.py
"""
Hybrid Phase Auditor - Uses local AI for 80% work, prepares for DeepSeek
"""

import subprocess
import json
import tempfile
from pathlib import Path
import sys

class HybridPhaseAuditor:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.local_ai = "llama3.2:3b"  # Fast local model
        
    def get_current_violations(self):
        """Get actual violations using AST analyzer"""
        print("🔍 Running deep AST analysis for actual violations...")
        
        # Run the AST analyzer in violation mode
        cmd = [
            sys.executable, "tools/analysis/ast_analyzer.py",
            ".", "--mode", "violations", "--show-code"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                # Parse the output to count real violations
                violations = []
                lines = result.stdout.split('\n')
                
                for line in lines:
                    if 'DIRECT_AI_CALL' in line or 'PHASE_VIOLATION' in line:
                        # Extract file and line
                        parts = line.split(':')
                        if len(parts) >= 3:
                            file = parts[0].strip()
                            line_num = parts[1].strip()
                            violation = {
                                'file': file,
                                'line': line_num,
                                'type': 'DIRECT_AI_CALL' if 'DIRECT_AI_CALL' in line else 'PHASE_VIOLATION',
                                'text': ':'.join(parts[2:]).strip()[:200]
                            }
                            violations.append(violation)
                
                return {
                    'total': len(violations),
                    'violations': violations[:20],  # Top 20
                    'raw_output': result.stdout[:2000]
                }
            else:
                return {'error': result.stderr}
                
        except Exception as e:
            return {'error': str(e)}
    
    def classify_violations_local(self, violations_data):
        """Use local AI to quickly classify violations by priority"""
        if not violations_data.get('violations'):
            return "No violations found!"
        
        # Build prompt for local AI
        violations_text = "\n".join([
            f"{i+1}. {v['file']}:{v['line']} - {v['type']}: {v['text'][:100]}..."
            for i, v in enumerate(violations_data['violations'][:10])
        ])
        
        prompt = f"""You are a code architecture assistant. Classify these phase violations:

VIOLATIONS FOUND:
{violations_text}

TOTAL VIOLATIONS: {violations_data.get('total', 0)}

CLASSIFICATION TASK:
1. Categorize each violation (1-4 stars urgency):
   ★★★★ - Critical: Direct AI calls, state mutation risks
   ★★★  - High: Boundary crossings, improper imports
   ★★   - Medium: Minor violations, documentation issues
   ★    - Low: Code smells, non-critical issues

2. For each critical/high violation, suggest exact file/line fix
3. Which 3 violations should be fixed FIRST?

Respond in this format:
CRITICAL (★★★★):
- [File:Line] Issue description → Suggested fix

HIGH (★★★):
- [File:Line] Issue description → Suggested fix

MEDIUM (★★):
- List

LOW (★):
- List

TOP 3 TO FIX NOW:
1. [File:Line] - Reason
2. [File:Line] - Reason
3. [File:Line] - Reason

READY FOR DEEPSEEK? [Yes/No] - Brief explanation
"""
        
        # Call local AI via Ollama
        return self._call_local_ai(prompt)
    
    def _call_local_ai(self, prompt):
        """Call local Ollama model"""
        try:
            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.local_ai,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 1000}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("response", "No response")
            else:
                return f"Local AI error: {response.status_code}"
                
        except Exception as e:
            return f"Local AI unavailable: {e}"
    
    def prepare_for_deepseek(self, violations_data, local_analysis):
        """Prepare optimized context for DeepSeek"""
        
        # Build efficient context (minimal, focused)
        context = f"""PROJECT STATUS: Phase Compliance Audit

VIOLATION SUMMARY:
Total violations: {violations_data.get('total', 0)}
Sample violations (first 5):
"""
        
        # Add sample violations
        for i, v in enumerate(violations_data.get('violations', [])[:5]):
            context += f"\n{i+1}. {v['file']}:{v['line']} - {v['type']}"
            context += f"\n   {v['text'][:150]}"
        
        context += f"""

LOCAL AI ANALYSIS SUMMARY:
{local_analysis[:1000]}...

TASK FOR YOU (DeepSeek):
1. Verify the top 3 priorities identified by local AI
2. Provide SPECIFIC code fixes for each critical violation
3. Suggest architectural improvements to prevent recurrence
4. Create a step-by-step plan (max 5 steps)

CONTEXT NOTES:
- Use existing tools: ai.py, ast_analyzer.py, editing_commands.py
- Respect phase boundaries: AI never mutates state
- Check SYSTEM_OWNERSHIP.md for system boundaries
"""
        
        return context
    
    def run_hybrid_audit(self):
        """Run complete hybrid audit workflow"""
        print("=" * 70)
        print("HYBRID PHASE AUDITOR")
        print("Local AI (fast) + DeepSeek (powerful)")
        print("=" * 70)
        
        # Step 1: Get actual violations (fast, local)
        print("\n[1/3] 📊 Scanning for actual violations...")
        violations = self.get_current_violations()
        
        if 'error' in violations:
            print(f"Error: {violations['error']}")
            return
        
        print(f"Found {violations.get('total', 0)} potential violations")
        
        # Step 2: Local AI analysis (fast classification)
        print("\n[2/3] 🤖 Local AI classification (fast)...")
        local_analysis = self.classify_violations_local(violations)
        
        print("Local AI analysis complete")
        print("-" * 40)
        print(local_analysis[:500] + "..." if len(local_analysis) > 500 else local_analysis)
        
        # Step 3: Prepare for DeepSeek
        print("\n[3/3] 🚀 Preparing for DeepSeek...")
        deepseek_context = self.prepare_for_deepseek(violations, local_analysis)
        
        # Save context
        output_file = self.project_root / "hybrid_audit_context.txt"
        output_file.write_text(deepseek_context, encoding='utf-8')
        
        print(f"\n✅ Hybrid audit complete!")
        print(f"   Context saved to: {output_file}")
        print(f"   Context size: {len(deepseek_context)} chars")
        
        # Show next steps
        print("\n" + "=" * 70)
        print("NEXT STEPS:")
        print("1. Review local analysis above (fast, 80% done)")
        print("2. For final polish, send to DeepSeek:")
        print(f"   cat {output_file} | pbcopy  # Copy to clipboard")
        print("3. Or use bridge:")
        print("   python scripts/ai_workflow.py send")
        print("=" * 70)
        
        return {
            'violations': violations,
            'local_analysis': local_analysis,
            'deepseek_context': deepseek_context,
            'context_file': str(output_file)
        }

# Command line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Hybrid Phase Auditor')
    parser.add_argument('--audit', action='store_true', help='Run full hybrid audit')
    parser.add_argument('--violations-only', action='store_true', help='Just find violations')
    parser.add_argument('--prepare-context', action='store_true', help='Prepare for DeepSeek')
    
    args = parser.parse_args()
    
    auditor = HybridPhaseAuditor()
    
    if args.audit:
        auditor.run_hybrid_audit()
    elif args.violations_only:
        violations = auditor.get_current_violations()
        print(json.dumps(violations, indent=2))
    elif args.prepare_context:
        # You'd need to pass violations data here
        print("Use --audit for complete workflow")
    else:
        parser.print_help()