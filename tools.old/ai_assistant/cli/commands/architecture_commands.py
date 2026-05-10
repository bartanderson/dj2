"""
Architecture and advanced analysis commands for AI Assistant CLI
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

def refactor_plan_command(args):
    """Generate refactoring plan"""
    print("Refactor-plan command - placeholder")
    return 0

def js_css_check_command(args):
    """Check JS/CSS separation"""
    print("JS-CSS-check command - placeholder")
    return 0

def analyze_project_command(args):
    """Complete project analysis"""
    print("Analyze-project command - placeholder")
    return 0

def feature_report_command(args):
    """Generate dynamic feature report"""
    print("Feature-report command - placeholder")
    return 0

def living_workflow_command(args):
    """Run complete living system workflow"""
    print("Living-workflow command - placeholder")
    return 0

# REGISTER ALL COMMANDS - CRITICAL: This must execute
register_command('refactor-plan', refactor_plan_command, "Generate refactoring plan")
register_command('js-css-check', js_css_check_command, "Check JS/CSS separation")
register_command('analyze-project', analyze_project_command, "Complete project analysis")
register_command('feature-report', feature_report_command, "Generate dynamic feature report")
register_command('living-workflow', living_workflow_command, "Run complete living system workflow")

# Debug: Print when module loads
if __name__ != "__main__":
    print(f"[DEBUG] architecture_commands.py loaded - registered {5} commands")
