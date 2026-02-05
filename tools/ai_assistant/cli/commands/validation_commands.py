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
    """Show and validate guardrails"""
    # Guardrail files are in DOCS/ directory
    guardrail_files = {
        'phase': 'DOCS/ENGINE_LOOP.md',
        'system': 'DOCS/SYSTEM_OWNERSHIP.md',
        'integration': 'DOCS/INTEGRATION_CHECKLIST.md',
        'documentation': 'DOCS/DOCUMENTATION_STANDARDS.md',
        'workflow': 'DOCS/DOCUMENTATION_WORKFLOW.md',
    }
    
    if args.list:
        print("Available guardrail categories:")
        for key, filename in guardrail_files.items():
            path = Path(filename)
            if path.exists():
                size = path.stat().st_size
                print(f"  {key}: {filename} ({size} bytes)")
            else:
                print(f"  {key}: {filename} (NOT FOUND)")
        return 0
    
    # Show default (development) if none specified
    from ..indexer import CodebaseIndexer
    from ..context_builder import BridgeAgent
    
    # Use BridgeAgent to parse and summarize guardrails
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    agent = BridgeAgent(indexer)
    
    # Get phase compliance summary
    phase_context = indexer.get_phase_violation_context()
    
    print("\nGUARDRAILS SUMMARY")
    print("=" * 80)
    
    if phase_context:
        violations = phase_context.get('total_violations', 0)
        print(f"Phase violations in project: {violations}")
        if violations > 0:
            print("\nRecent phase violations from audit:")
            for i, violation in enumerate(phase_context.get('violations', [])[:3], 1):
                print(f"\n{i}. {violation[:200]}...")
    
    # List key guardrail files
    print("\nKey guardrail files found:")
    for key, filename in guardrail_files.items():
        path = Path(filename)
        if path.exists():
            print(f"  ✓ {key}: {filename}")
        else:
            print(f"  ✗ {key}: {filename} (missing)")
    
    return 0

def phase_check_command(args):
    """Check phase compliance for specific files or patterns"""
    from ..indexer import CodebaseIndexer
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    
    # Search for phase violations
    results = indexer.search("phase violation", limit=args.limit)
    
    if not results:
        print("No phase violations found in indexed files.")
        return 0
    
    print(f"\nFound {len(results)} files with phase violation references:")
    print("=" * 80)
    
    violation_files = []
    for result in results:
        file_path = result['path']
        if file_path.endswith('.py'):
            violation_files.append(file_path)
            print(f"  - {file_path} (score: {result['score']:.3f})")
    
    # Check specific patterns
    if args.patterns:
        print(f"\nChecking patterns: {args.patterns}")
        patterns = args.patterns.split(',')
        
        for pattern in patterns:
            pattern_results = indexer.search(pattern, limit=5)
            if pattern_results:
                print(f"\nPattern '{pattern}':")
                for result in pattern_results:
                    print(f"  - {result['path']}")
    
    return 0

# Register validation commands
register_command('validate', validate_command, "Validate a DeepSeek response")
register_command('guardrails', guardrails_command, "Show and validate guardrails")
register_command('phase-check', phase_check_command, "Check phase compliance for specific files or patterns")