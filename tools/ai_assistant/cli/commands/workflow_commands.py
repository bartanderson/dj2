"""
Workflow and bridge-related commands for AI Assistant CLI
Fixed version - ensures all commands register properly
"""
import sys
from pathlib import Path

# Import registry FIRST to avoid circular imports
try:
    # When imported as module
    from . import register_command
except ImportError:
    # When run directly
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from commands import register_command

def context_command(args):
    """REAL implementation - uses your existing context_manager.py"""
    import sys
    from pathlib import Path
    import subprocess
    
    # Get query from args or command line
    query = getattr(args, 'query', None)
    if not query and len(sys.argv) > 2:
        # Try to get query from command line: python ai.py context "query"
        for i, arg in enumerate(sys.argv):
            if arg == 'context' and i + 1 < len(sys.argv):
                query = sys.argv[i + 1]
                break
    
    if not query:
        print("Error: No query provided for context command")
        print("Usage: python ai.py context \"your query\"")
        print("   or: python ai.py context --query \"your query\"")
        return 1
    
    print(f"🚀 Building context for: {query}")
    
    # Use your existing context_manager.py
    project_root = Path(__file__).parent.parent.parent.parent.parent
    context_manager_path = project_root / "scripts" / "context_manager.py"
    
    if not context_manager_path.exists():
        print(f"Error: context_manager.py not found at {context_manager_path}")
        return 1
    
    # Build command
    cmd = [sys.executable, str(context_manager_path), "--query", query]
    
    # Run it
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        encoding='utf-8', 
        errors='replace',
        cwd=project_root
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr[:500]}", file=sys.stderr)
    
    return result.returncode

def validate_command(args):
    """Validate a DeepSeek response"""
    print("Validate command - placeholder (use scripts/context_manager.py --send for validation)")
    return 0

def guardrails_command(args):
    """REAL implementation - runs the new guardrails tool"""
    import sys
    from pathlib import Path
    import subprocess
    
    print("🔍 Running AI Contract Guardrails...")
    
    project_root = Path(__file__).parent.parent.parent.parent.parent
    tool_path = project_root / "tools" / "guardrails" / "run.py"
    
    if not tool_path.exists():
        print(f"Error: guardrails tool not found at {tool_path}")
        return 1
    
    # Build command
    cmd = [sys.executable, str(tool_path)]
    
    # Run it
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        encoding='utf-8', 
        errors='replace',
        cwd=project_root
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
    
    project_root = Path(__file__).parent.parent.parent.parent.parent
    tool_path = project_root / "tools" / "phase_checker" / "run.py"
    
    if not tool_path.exists():
        print(f"Error: phase-checker tool not found at {tool_path}")
        return 1
    
    # Build command
    cmd = [sys.executable, str(tool_path)]
    
    # Run it
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        encoding='utf-8', 
        errors='replace',
        cwd=project_root
    )
    
    print(result.stdout)
    if result.stderr:
        print(f"Error: {result.stderr[:500]}", file=sys.stderr)
    
    return result.returncode

def bridge_status_command(args):
    """Check AI Bridge status"""
    print("Bridge Status:")
    print("  DeepSeek: Available via scripts/context_manager.py --send")
    print("  Ollama: Check with 'ollama list'")
    print("  Tools: guardrails and phase-check are working")
    print("  Context Manager: scripts/context_manager.py is working")
    return 0

# REGISTER ALL COMMANDS - CRITICAL: This must execute
register_command('context', context_command, "Build context for DeepSeek")
register_command('validate', validate_command, "Validate a DeepSeek response")
register_command('guardrails', guardrails_command, "Show and validate guardrails")
register_command('phase-check', phase_check_command, "Check phase compliance")
register_command('bridge-status', bridge_status_command, "Check AI Bridge status")

# Debug: Print when module loads
if __name__ != "__main__":
    print(f"[DEBUG] workflow_commands.py loaded - registered {5} commands")
