#!/usr/bin/env python3
"""
AI Assistant CLI - Fixed Command Router
Replaces the original with proper module loading.
"""

import sys
import codecs
import argparse
import importlib
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

def load_all_commands():
    """Load all command modules with error reporting."""
    command_modules = [
        'tools.ai_assistant.cli.commands.search_commands',
        'tools.ai_assistant.cli.commands.analysis_commands',
        'tools.ai_assistant.cli.commands.edit_commands',
        'tools.ai_assistant.cli.commands.workflow_commands',
        'tools.ai_assistant.cli.commands.index_commands',
        'tools.ai_assistant.cli.commands.architecture_commands',
        'tools.ai_assistant.cli.commands.tool_commands', 
    ]
    
    #print(f"[DEBUG] Loading {len(command_modules)} command modules...", file=sys.stderr)
    
    loaded = 0
    for module_name in command_modules:
        try:
            #print(f"[DEBUG] Attempting to load: {module_name}", file=sys.stderr)
            module = importlib.import_module(module_name)
            loaded += 1
            #print(f"[DEBUG] [OK] Successfully loaded: {module_name}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] ERROR loading module {module_name}: {e}", file=sys.stderr)
            # Don't print full traceback for missing modules, just the error
    
    #print(f"[DEBUG] Loaded {loaded}/{len(command_modules)} modules", file=sys.stderr)
    return loaded

def setup_argparse() -> argparse.ArgumentParser:
    """Setup argparse with subparsers."""
    parser = argparse.ArgumentParser(
        description="AI Assistant CLI - Code analysis and orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\n
Examples:
  python ai.py search "phase violation"
  python ai.py context "analyze my code"
  python ai.py analyze-project
  python ai.py list-commands
        """
    )
    
    # Common arguments
    parser.add_argument(
        '--index-dir', 
        default='.whoosh_index', 
        help='Whoosh index directory'
    )
    parser.add_argument(
        '--verbose', '-v', 
        action='store_true', 
        help='Verbose output'
    )
    
    # Special commands that don't need subparsers
    if len(sys.argv) > 1 and sys.argv[1] in ['help', 'list-commands']:
        if sys.argv[1] == 'help':
            parser.add_argument('command', nargs='?', help='Command to get help for')
        return parser
    
    subparsers = parser.add_subparsers(
        dest='command',
        title='commands',
        description='Available commands',
        help='Command to execute'
    )
    
    # Load all command modules first
    load_all_commands()
    
    # Import registry after modules are loaded
    from .commands import COMMAND_REGISTRY
    
    # Create parsers for registered commands
    for cmd_name, cmd_info in COMMAND_REGISTRY.items():
        subp = subparsers.add_parser(
            cmd_name, 
            help=cmd_info['help'],
            aliases=cmd_info.get('aliases', [])
        )
        
        # Add common arguments for specific commands
        if cmd_name in ['search', 'archive-search', 'combined-search']:
            subp.add_argument('query', nargs='?', help='Search query (optional)')
            subp.add_argument('--path', '-p', help='File path to examine')
            subp.add_argument('--limit', '-l', type=int, default=10, help='Result limit')
            subp.add_argument('--file-type', help='Filter by file type (comma-separated)')
            subp.add_argument('--group', '-g', 
                              help='Filter by file group: code, docs, config, ui, python, markdown, json, yaml, text, all')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        elif cmd_name == 'analyze':
            subp.add_argument('query', nargs='?', help='Analysis topic (optional)')
            subp.add_argument('--deep', action='store_true', help='Run deep analysis with llama3.2')
            subp.add_argument('--detail', action='store_true', help='Show detailed analysis')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        elif cmd_name in ['violations', 'todos', 'deps', 'structure']:
            subp.add_argument('path', nargs='?', default='.', help='Path to analyze')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        elif cmd_name == 'context':
            subp.add_argument('query', nargs='?', help='Analysis query (optional)')
            subp.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
            subp.add_argument('--output', '-o', help='Output file path')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        elif cmd_name == 'validate':
            subp.add_argument('--response-file', help='File containing DeepSeek response')
            subp.add_argument('--response-text', help='Direct response text')
            subp.add_argument('--output', '-o', help='Output file for validation report')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        elif cmd_name == 'guardrails':
            subp.add_argument('--list', action='store_true', help='List available guardrails')
            subp.add_argument('--summary', action='store_true', help='Show summary only')
            subp.add_argument('--limit', type=int, default=1000, help='Character limit for output')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        elif cmd_name == 'phase-check':
            subp.add_argument('--patterns', help='Comma-separated patterns to check')
            subp.add_argument('--limit', type=int, default=10, help='Result limit')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        elif cmd_name in ['index', 'archive-index']:
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

        elif cmd_name == 'tools':
            subp.add_argument('query', nargs='?', help='Tool search query (optional)')
            subp.add_argument('--ai-suggest', action='store_true', 
                            help='Get AI suggestions for tools')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        elif cmd_name in ['tool-help', 'th']:
            subp.add_argument('tool_name', help='Name of the tool to get help for')
            subp.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        
        # Architecture commands don't need additional args
        
        subp.set_defaults(func=cmd_info['func'])
    
    return parser

def help_command(args):
    """Show help for a command or general help."""
    parser = setup_argparse()
    
    if hasattr(args, 'command') and args.command:
        # Show help for specific command
        try:
            # Build args list for the subcommand
            sub_args = [args.command, '--help']
            parser.parse_args(sub_args)
        except SystemExit:
            pass
    else:
        parser.print_help()
    
    return 0

def list_commands_command(args):
    """List all available commands."""
    # Load command modules first
    load_all_commands()
    
    from .commands import list_commands
    
    print("Available Commands:")
    print("=" * 60)
    
    commands = list_commands()
    for name, help_text in sorted(commands.items()):
        print(f"{name:20} - {help_text[:60]}")
    
    print(f"\nTotal: {len(commands)} commands")
    print("\nUse 'python ai.py help <command>' for detailed help.")
    
    return 0

def main():
    """Main entry point for modular CLI."""
    # Handle help and list-commands specially
    if len(sys.argv) > 1:
        if sys.argv[1] == 'list-commands':
            return list_commands_command(type('Args', (), {})())
        elif sys.argv[1] == 'help':
            # Parse help command
            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument('command', nargs='?', help='Command to get help for')
            try:
                help_args, _ = parser.parse_known_args()
                return help_command(help_args)
            except SystemExit:
                pass
    
    # Parse regular commands
    parser = setup_argparse()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Get and execute the command
    from .commands import get_command
    cmd_info = get_command(args.command)
    
    if not cmd_info:
        print(f"Error: Unknown command '{args.command}'")
        parser.print_help()
        return 1
    
    try:
        return cmd_info['func'](args)
    except Exception as e:
        print(f"Error executing command '{args.command}': {e}")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())