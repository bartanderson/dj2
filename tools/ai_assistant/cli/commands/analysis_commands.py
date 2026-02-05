"""
Analysis-related commands for AI Assistant CLI
"""
import sys
import json
import subprocess
from pathlib import Path

# Import registry
from . import register_command

def analyze_command(args):
    """Run comprehensive analysis on a topic"""
    try:
        from ..indexer import CodebaseIndexer
        from ..context_builder import BridgeAgent
    except ImportError:
        # Fallback for direct execution
        from tools.ai_assistant.indexer import CodebaseIndexer
        from tools.ai_assistant.context_builder import BridgeAgent
    
    indexer = CodebaseIndexer(index_dir=args.index_dir)
    agent = BridgeAgent(indexer)
    
    # Build context
    query = args.query
    if not query:
        query = input("Enter analysis topic: ")
    
    print(f"\nAnalyzing: {query}")
    print("=" * 80)
    
    context = agent.build_context_for_query(query)
    
    # Get phase violations from the indexer (for summary)
    phase_context = indexer.get_phase_violation_context()
    
    # Get related files
    whoosh_results = context['whoosh_results']
    
    # Print analysis
    print("\nANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Topic: {query}")
    
    # System boundaries affected
    systems = set()
    for result in whoosh_results:
        for tag in result.get('system_tags', []):
            systems.add(tag.replace('system:', ''))
    
    if systems:
        print(f"\nAffected systems: {', '.join(sorted(systems))}")
    
    # Get ACTUAL phase violations with code using ASTAnalyzer
    print("\nScanning for phase violations in code...")
    import sys
    from pathlib import Path
    
    # Import ASTAnalyzer
    analysis_dir = Path(__file__).parent.parent.parent.parent / 'analysis'
    sys.path.insert(0, str(analysis_dir))
    from ast_analyzer import ASTAnalyzer
    
    analyzer = ASTAnalyzer()
    project_data = analyzer.scan_project(".")
    
    # Extract violations WITH CODE CONTEXT
    violations_with_code = []
    for file_data in project_data:
        if 'phase_violations' not in file_data:
            continue
            
        for violation in file_data['phase_violations']:
            # Get code context
            context = analyzer._get_code_context(
                file_data['source'], 
                violation['line']
            )
            
            violations_with_code.append({
                'file': file_data['path'],
                'line': violation['line'],
                'type': violation.get('type', 'PHASE_VIOLATION'),
                'pattern': violation.get('pattern', 'unknown'),
                'full_line': violation.get('text', ''),
                'context': context,
            })
    
    print(f"\nPhase violations in project: {len(violations_with_code)}")
    
    # Show a few violations in the summary
    if violations_with_code:
        print("\nTop violations found:")
        for i, violation in enumerate(violations_with_code[:3], 1):
            print(f"  {i}. {violation['file']}:{violation['line']} - {violation.get('pattern', '')}")
    
    # Key files - FILTER OUT DOCUMENTATION
    if whoosh_results:
        # Filter out documentation files
        def is_code_file(path: str) -> bool:
            path_lower = path.lower()
            code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.h', '.cs']
            doc_patterns = ['\\docs\\', '/docs/', '\\doc\\', '/doc/', '\\documentation\\', '/documentation/']
            
            # Must be a code file
            if not any(path_lower.endswith(ext) for ext in code_extensions):
                return False
            
            # Must NOT be in documentation directory
            if any(pattern in path_lower for pattern in doc_patterns):
                return False
            
            return True
        
        # Filter whoosh results
        code_files = [r for r in whoosh_results if is_code_file(r['path'])]
        
        print(f"\nCode files ({len(code_files)} found):")
        for result in code_files[:8]:
            score_str = f"({result['score']:.2f})" if args.detail else ""
            print(f"  - {result['path']} {score_str}")
        
        # Optionally show documentation files separately
        if args.detail and len(code_files) < len(whoosh_results):
            doc_files = [r for r in whoosh_results if not is_code_file(r['path'])]
            print(f"\nRelated documentation ({len(doc_files)} found):")
            for result in doc_files[:3]:
                print(f"  - {result['path']}")
    
    # Use llama3.2 for deeper analysis
    if args.deep:
        print("\n" + "=" * 80)
        print("DEEP ANALYSIS (using llama3.2)")
        print("=" * 80)
        
        if violations_with_code:
            # Build a prompt that includes ACTUAL CODE VIOLATIONS
            analysis_prompt = f"""
            Analysis Topic: {query}
            
            Found {len(whoosh_results)} relevant files.
            
            PHASE VIOLATIONS ANALYSIS:
            Found {len(violations_with_code)} actual phase violations in code:
            
            """
            
            # Add each violation with code context
            for i, violation in enumerate(violations_with_code[:10], 1):
                analysis_prompt += f"\n{'='*60}"
                analysis_prompt += f"\nVIOLATION {i}: {violation['file']}:{violation['line']}"
                analysis_prompt += f"\nType: {violation['type']}"
                analysis_prompt += f"\nPattern: {violation['pattern']}"
                analysis_prompt += f"\n\nCode context:\n{violation['context']}"
                analysis_prompt += f"\nFull line: {violation['full_line']}"
            
            analysis_prompt += f"""
            {'='*60}
            TASK: Analyze these SPECIFIC phase violations and provide:
            
            1. For EACH violation:
               - Is this actually a PHASE/ARCHITECTURAL violation? (Yes/No with reason)
               - What specific architectural rule does it violate?
               - What's the exact fix needed?
               - Priority level (High/Medium/Low)
            
            2. Overall recommendations:
               - Most critical violations to fix first
               - Estimated effort for fixes
               - Architectural improvements needed
            
            IMPORTANT: Focus only on PHASE/ARCHITECTURAL violations (boundary crossings, layer violations, direct external calls).
            IGNORE general code quality issues (unused imports, magic numbers, long methods, etc.).
            """
        else:
            print("[OK] No architectural violations found.")
            print("\nFor comprehensive project analysis:")
            print("  python ai.py analyze-project       # Full structure + phase compliance")
            print("  python ai.py refactor-plan         # Generate refactoring plan")
            print("  python ai.py living-workflow       # Complete workflow analysis")
            print("\nFor detailed phase violation analysis:")
            print("  python tools/analysis/ast_analyzer.py . --mode violations --show-code")
        
        analysis = agent._call_ollama(analysis_prompt)
        print(analysis)
    
    return 0

def violations_command(args):
    """Run phase boundary violation analysis"""
    import subprocess
    tools_dir = Path(__file__).parent.parent.parent.parent / 'analysis'
    
    # Find the analyzer
    analyzer_path = tools_dir / 'ast_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    # Build command
    cmd = [sys.executable, str(analyzer_path)]
    cmd.extend([args.path, "--mode", "violations"])
    
    return subprocess.call(cmd)

def todos_command(args):
    """Find TODOs and FIXMEs"""
    import subprocess
    tools_dir = Path(__file__).parent.parent.parent.parent / 'analysis'
    
    analyzer_path = tools_dir / 'ast_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    cmd = [sys.executable, str(analyzer_path)]
    cmd.extend([args.path, "--mode", "todos"])
    
    return subprocess.call(cmd)

def deps_command(args):
    """Show dependency analysis"""
    import subprocess
    tools_dir = Path(__file__).parent.parent.parent.parent / 'analysis'
    
    analyzer_path = tools_dir / 'ast_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    cmd = [sys.executable, str(analyzer_path)]
    cmd.extend([args.path, "--mode", "deps"])
    
    return subprocess.call(cmd)

def structure_command(args):
    """Show project structure"""
    import subprocess
    tools_dir = Path(__file__).parent.parent.parent.parent / 'analysis'
    
    analyzer_path = tools_dir / 'ast_analyzer.py'
    
    if not analyzer_path.exists():
        print(f"Error: Could not find analyzer at {analyzer_path}")
        return 1
    
    cmd = [sys.executable, str(analyzer_path)]
    cmd.extend([args.path, "--mode", "structure"])
    
    return subprocess.call(cmd)

# Register all analysis commands
register_command('analyze', analyze_command, "Analyze a topic")
register_command('violations', violations_command, "Find phase boundary violations")
register_command('todos', todos_command, "Find TODOs and FIXMEs")
register_command('deps', deps_command, "Show dependency analysis")
register_command('structure', structure_command, "Show project structure")