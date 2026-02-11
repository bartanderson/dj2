# coding=utf-8
"""
Validation and guardrails commands for AI Assistant CLI
"""
import json
from pathlib import Path

# Import registry
from . import register_command

def validate_command(args):
    """Validate a DeepSeek response"""
    from ..indexer import CodebaseIndexer
    from ..context_builder import BridgeAgent
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    agent = BridgeAgent(indexer)
    
    # Read response
    if args.response_file:
        with open(args.response_file, 'r', encoding='utf-8') as f:
            response = f.read()
    elif args.response_text:
        response = args.response_text
    else:
        print("Paste DeepSeek response (Ctrl+D to finish, blank line to end):")
        lines = []
        try:
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
        except EOFError:
            pass
        response = "\n".join(lines)
    
    if not response.strip():
        print("No response provided.")
        return 1
    
    # Create minimal context
    context = {
        "query": "Validation only",
        "structured_context": {
            "relevant_files": [],
            "key_insights": "Validating DeepSeek response against project rules"
        }
    }
    
    print("\nValidating DeepSeek response...")
    validation = agent.validate_deepseek_response(response, context)
    
    print("\n" + "=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    
    if validation.get('is_valid', True):
        print("✅ Response is VALID")
    else:
        print("❌ Response has ISSUES")
    
    if validation.get('issues'):
        print("\nISSUES FOUND:")
        for i, issue in enumerate(validation['issues'], 1):
            print(f"  {i}. {issue}")
    
    if validation.get('suggested_fixes'):
        print("\nSUGGESTED FIXES:")
        for i, fix in enumerate(validation.get('suggested_fixes', []), 1):
            print(f"  {i}. {fix}")
    
    phase_check = validation.get('phase_compliance_check', 'unknown')
    print(f"\nPHASE COMPLIANCE: {phase_check.upper()}")
    
    if phase_check == 'fail':
        print("  ⚠️  This change may violate phase boundaries!")
    elif phase_check == 'needs_review':
        print("  ⚠️  Manual review required for phase compliance")
    
    # Save validation report
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(validation, f, indent=2)
        print(f"\n✓ Validation report saved to: {args.output}")
    
    return 0 if validation.get('is_valid', True) else 1

def guardrails_command(args):
    """REAL implementation - runs the new guardrails tool"""
    import sys
    from pathlib import Path
    import subprocess
    
    print("🔍 Running AI Contract Guardrails...")
    
    # Find the new tool
    tool_path = Path(__file__).parent.parent.parent.parent.parent / "tools" / "analysis" / "guardrails.py"
    
    if not tool_path.exists():
        print(f"Error: guardrails tool not found at {tool_path}")
        return 1
    
    # Build command
    cmd = [sys.executable, str(tool_path)]
    
    # Add any flags from args
    if hasattr(args, 'list') and args.list:
        cmd.append("--list")
    
    # Run it
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        encoding='utf-8', 
        errors='replace'
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr[:500]}", file=sys.stderr)
    
    return result.returncode

def phase_check_command(args):
    """REAL implementation - runs the new phase-check tool"""
    import sys
    from pathlib import Path
    import subprocess
    
    print("🔍 Running Phase Compliance Check...")
    
    # Find the new tool
    tool_path = Path(__file__).parent.parent.parent.parent.parent / "tools" / "analysis" / "phase_checker.py"
    
    if not tool_path.exists():
        print(f"Error: phase-checker tool not found at {tool_path}")
        return 1
    
    # Build command
    cmd = [sys.executable, str(tool_path)]
    
    # Add any flags from args
    if hasattr(args, 'verbose') and args.verbose:
        cmd.append("--verbose")
    
    # Run it
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        encoding='utf-8', 
        errors='replace'
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr[:500]}", file=sys.stderr)
    
    return result.returncode

# Register validation commands
register_command('validate', validate_command, "Validate a DeepSeek response")
register_command('guardrails', guardrails_command, "Show and validate guardrails")
register_command('phase-check', phase_check_command, "Check phase compliance for specific files or patterns")