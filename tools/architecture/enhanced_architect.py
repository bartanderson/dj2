#tools/architecture/enhanced_architect.py
"""
Enhanced Living Architect - Simplified version
"""

import os
import ast
import json
import re
import subprocess
import networkx as nx
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Any, Optional
import sys
import codecs

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

class EnhancedLivingArchitect:
    """Enhanced architect with full project analysis"""
    
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        
    def analyze_full_project(self):
        """Run complete project analysis"""
        print("=" * 80)
        print("ENHANCED LIVING SYSTEM ARCHITECT")
        print("=" * 80)
        
        # Step 1: Structure analysis
        print("\n📁 Step 1: Project structure analysis")
        structure = self.scan_project_structure()
        self._print_structure_summary(structure)
        
        # Step 2: Template analysis
        print("\n🎨 Step 2: Template analysis (HTML/JS/CSS separation)")
        template_analysis = self._analyze_templates(structure)
        
        # Step 3: Phase compliance
        print("\n⚖️ Step 5: Phase compliance analysis")
        violations = self._check_phase_compliance()
        
        return {
            'structure': structure,
            'templates': template_analysis,
            'phase_violations': violations
        }
    
    def scan_project_structure(self) -> Dict[str, List[str]]:
        """Scan and categorize all files in the project"""
        print("🔍 Scanning project structure...")
        
        structure = {
            'python_files': [],
            'template_files': [],
            'static_files': [],
            'documentation_files': [],
            'other_files': [],
            'ignored_dirs': []
        }
        
        IGNORE_DIRS = {
            'Lib', 'tools', 'Scripts', 'tests', 'DOCS', 'generated_images', 'world_images', 'sounds',
            '__pycache__', 'venv', '.venv', 'env', 'node_modules',
            '.git', '.svn', '.hg', '.idea', '.vscode',
            'archive', 'backup', 'temp', 'tmp',
            'dist', 'build', '*.egg-info'
        }
        
        # Walk the project
        for root, dirs, files in os.walk(self.project_root):
            # Remove ignored directories from walk
            root_path = Path(root)
            rel_root = root_path.relative_to(self.project_root)
            
            # Check if we should skip this directory
            if self._should_ignore_directory(rel_root, IGNORE_DIRS):
                structure['ignored_dirs'].append(str(rel_root))
                dirs[:] = []  # Don't recurse into ignored directories
                continue
            
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore_directory(rel_root / d, IGNORE_DIRS)]
            
            # Categorize files
            for file in files:
                file_path = root_path / file
                rel_path = file_path.relative_to(self.project_root)
                
                if file.endswith('.py'):
                    structure['python_files'].append(str(rel_path))
                elif file.endswith('.html') or file.endswith('.jinja') or file.endswith('.jinja2'):
                    structure['template_files'].append(str(rel_path))
                elif file.endswith(('.js', '.css', '.scss', '.less', '.json', '.png', '.jpg', '.svg')):
                    structure['static_files'].append(str(rel_path))
                elif file.endswith(('.md', '.txt', '.rst', '.yml', '.yaml')):
                    structure['documentation_files'].append(str(rel_path))
                else:
                    structure['other_files'].append(str(rel_path))
        
        return structure
    
    def _should_ignore_directory(self, rel_path: Path, ignore_dirs: Set[str]) -> bool:
        """Check if a directory should be ignored"""
        # Check if any parent directory is in IGNORE_DIRS
        for part in rel_path.parts:
            if part in ignore_dirs:
                return True
            # Check patterns like *.egg-info
            if any(pattern in part for pattern in ignore_dirs if '*' in pattern):
                return True
        return False
    
    def _print_structure_summary(self, structure):
        """Print project structure summary"""
        print(f"  Python files: {len(structure['python_files'])}")
        print(f"  Template files: {len(structure['template_files'])}")
        print(f"  Static files: {len(structure['static_files'])}")
        print(f"  Documentation files: {len(structure['documentation_files'])}")
        print(f"  Other files: {len(structure['other_files'])}")
        print(f"  Ignored directories: {len(structure['ignored_dirs'])}")
    
    def _analyze_templates(self, structure):
        """Analyze all templates for JS/CSS separation"""
        print(f"  Analyzing {len(structure['template_files'])} template files...")
        
        # Simple analysis - just count files
        return {
            'template_count': len(structure['template_files']),
            'static_count': len(structure['static_files']),
            'separation_note': 'Use --check-js-css for detailed analysis'
        }
    
    def _check_phase_compliance(self) -> List[Dict]:
        """Check for phase boundary violations - simplified"""
        print("  Checking phase compliance...")
        
        # Import the AST analyzer
        try:
            from tools.analysis.ast_analyzer import ASTAnalyzer
            analyzer = ASTAnalyzer()
            project_data = analyzer.scan_project(str(self.project_root))
            
            violations = []
            for file_data in project_data:
                for violation in file_data.get('phase_violations', []):
                    violations.append(violation)
            
            if violations:
                print(f"  Found {len(violations)} potential phase violations")
            else:
                print("  No phase violations detected")
            
            return violations[:10]  # Return first 10
            
        except ImportError:
            print("  ⚠️ ASTAnalyzer not available for detailed phase analysis")
            return []
    
    def generate_refactoring_plan(self) -> str:
        """Generate comprehensive refactoring plan"""
        plan = []
        plan.append("# COMPREHENSIVE REFACTORING PLAN")
        plan.append("Generated by Enhanced Living System Architect")
        plan.append("")
        
        # Run analysis
        results = self.analyze_full_project()
        
        # 1. Phase Compliance Plan
        violations = results.get('phase_violations', [])
        if violations:
            plan.append("## 1. Phase Compliance Fixes")
            plan.append("### High Priority (Must Fix):")
            for v in violations[:5]:
                plan.append(f"- **{v.get('file', 'unknown')}**: Line {v.get('line', '?')}: {v.get('text', '')[:100]}...")
            plan.append("")
        
        # 2. File Organization
        structure = results.get('structure', {})
        plan.append("## 2. File Organization Improvements")
        
        # Check for Python files in wrong locations
        for python_file in structure.get('python_files', []):
            path = Path(python_file)
            if path.parent.name in ['static', 'templates']:
                plan.append(f"- Move `{python_file}` to appropriate Python directory")
        
        plan.append("")
        
        # 3. Growth Strategy
        plan.append("## 3. System Growth Strategy")
        plan.append("### Adding New Features:")
        plan.append("1. **Phase-first design**: Determine which phase the feature belongs to")
        plan.append("2. **Directory structure**:")
        plan.append("   - Python logic → `engine/`, `world/`, `dungeon_neo/`")
        plan.append("   - Templates → `templates/` with minimal inline JS/CSS")
        plan.append("   - Static files → `static/js/`, `static/css/`")
        plan.append("3. **Phase check**: Run phase compliance analysis before committing")
        plan.append("")
        
        return '\n'.join(plan)

def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Enhanced Living System Architect - Complete project analysis'
    )
    parser.add_argument('--analyze', action='store_true', help='Analyze full project')
    parser.add_argument('--refactor-plan', action='store_true', help='Generate refactoring plan')
    parser.add_argument('--check-js-css', action='store_true', help='Check JS/CSS separation')
    
    args = parser.parse_args()
    
    architect = EnhancedLivingArchitect()
    
    if args.analyze:
        results = architect.analyze_full_project()
        
        # Save results
        with open('enhanced_analysis.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("\n📊 Analysis saved to enhanced_analysis.json")
    
    if args.refactor_plan:
        plan = architect.generate_refactoring_plan()
        print("\n" + "=" * 80)
        print("REFACTORING PLAN")
        print("=" * 80)
        print(plan)
        
        with open('refactoring_plan.md', 'w', encoding='utf-8') as f:
            f.write(plan)
        print("\n📄 Plan saved to refactoring_plan.md")
    
    if args.check_js_css:
        print("\n🎨 JavaScript/CSS Separation Report:")
        print("-" * 40)
        print("Use the full analyze command for detailed JS/CSS analysis")
        print("or run: python ai.py analyze-project")
    
    if not any(vars(args).values()):
        print("No arguments provided. Use --help for options.")

if __name__ == "__main__":
    main()