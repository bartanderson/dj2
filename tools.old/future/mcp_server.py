#!/usr/bin/env python3
"""
MCP server for Dungeon Journey 2 - DIRECT IMPORT VERSION (PROVEN WORKING)
"""
import sys
import os
import io
from mcp.server.fastmcp import FastMCP

# Initialize server
mcp = FastMCP("dj2-project-tools")

def run_cli_directly(args):
    """
    DIRECT IMPLEMENTATION - PROVEN TO WORK BY YOUR DIAGNOSTIC
    Calls tools.ai_assistant.cli.main() and captures output exactly as test.py did.
    """
    # Save original state
    old_argv = sys.argv.copy()
    old_stdout = sys.stdout
    old_stderr = sys.stderr

    try:
        # 1. Set up output capture (EXACTLY as in your working test)
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        # 2. Set command line arguments (EXACTLY as ai.py expects)
        # args format: ['search', 'GameEngine', '--limit', '5']
        sys.argv = ['ai.py'] + args

        # 3. Import and run the CLI (EXACTLY as in your working test)
        from tools.ai_assistant.cli import main

        exit_code = 0
        try:
            main()
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 0

        # 4. Get the captured output
        output = stdout_capture.getvalue()

        # 5. Return results
        if exit_code == 0:
            return output.strip() or "(Command succeeded with no output)"
        else:
            return f"CLI Error[{exit_code}]: {output}"

    except Exception as e:
        return f"ERROR: {str(e)}"
    finally:
        # Restore original state
        sys.argv = old_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr

@mcp.tool()
def project_search(query: str, limit: int = 5) -> str:
    """Searches the project codebase. Example: project_search GameEngine"""
    return run_cli_directly(["search", query, "--limit", str(limit)])

@mcp.tool()
def analyze_component(component_name: str) -> str:
    """Extracts and analyzes a component. Example: analyze_component GameEngine"""
    return run_cli_directly(["extract", "--component", component_name])

if __name__ == "__main__":
    # Simple startup message
    print(f"✓ DJ2 MCP Server ready (PID: {os.getpid()})", file=sys.stderr)
    mcp.run()