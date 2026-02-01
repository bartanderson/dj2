#tools/analysis/ast_analyzer.py
"""
Core AST analysis engine for the project.
Simplified version without backup dependencies.
"""

import os
import ast
import json
import argparse
from typing import List, Dict, Any, Optional
from pathlib import Path

class ASTAnalyzer:
    """Enhanced AST analyzer with phase violation detection and project scanning"""
    
    def __init__(self, ignore_dirs: List[str] = None):
        self.ignore_dirs = ignore_dirs or [
            '__pycache__', 'venv', '.git', 'Lib', 
            'core', 'archive',
            'node_modules', '.idea', '.vscode',
            'docs', 'DOCS', 'documentation', 'doc',  # Added: ignore documentation
            'tests', 'tools'
        ]
        self.phase_violation_patterns = [
            'direct ai call',
            'ai.*call.*directly',
            'phase.*violation',
            'boundary.*violation'
        ]
    
    @staticmethod
    def extract_function_info(node: ast.FunctionDef) -> Dict[str, Any]:
        """Extract function/method details from AST node"""
        return {
            'name': node.name,
            'args': [arg.arg for arg in node.args.args],
            'decorators': [ast.unparse(d) for d in node.decorator_list],
            'lineno': node.lineno,
            'returns': ast.unparse(node.returns) if node.returns else None
        }

    @staticmethod
    def extract_class_info(node: ast.ClassDef) -> Dict[str, Any]:
        """Extract class details from AST node including methods"""
        class_info = {
            'name': node.name,
            'bases': [ast.unparse(b) for b in node.bases],
            'decorators': [ast.unparse(d) for d in node.decorator_list],
            'methods': [],
            'lineno': node.lineno,
            'docstring': ast.get_docstring(node)
        }
        
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                class_info['methods'].append(ASTAnalyzer.extract_function_info(item))
                
        return class_info

    @staticmethod
    def extract_import_info(node) -> Dict[str, Any]:
        """Extract import statement details"""
        if isinstance(node, ast.Import):
            return {
                'type': 'import',
                'names': [{'name': alias.name, 'asname': alias.asname} for alias in node.names],
                'lineno': node.lineno
            }
        elif isinstance(node, ast.ImportFrom):
            return {
                'type': 'from',
                'module': node.module,
                'names': [{'name': alias.name, 'asname': alias.asname} for alias in node.names],
                'level': node.level,
                'lineno': node.lineno
            }

    def parse_python_file(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Parse a Python file and extract its structure with enhanced analysis"""
        # Skip non-Python files (markdown, JSON, etc.)
        if not filepath.endswith('.py'):
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError, Exception) as e:
            print(f"Error parsing {filepath}: {e}")
            return None

        phase_violations = self._detect_phase_violations_in_source(source, filepath)
        phase_violations.extend(self._detect_ai_boundary_violations(tree, filepath))

        file_info = {
            'path': filepath,
            'imports': [],
            'classes': [],
            'functions': [],
            'source': source,
            'todos': self._extract_todos(source),
            'phase_violations': phase_violations,
            'line_count': len(source.splitlines())
        }

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                file_info['imports'].append(self.extract_import_info(node))
            elif isinstance(node, ast.ClassDef):
                file_info['classes'].append(self.extract_class_info(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                file_info['functions'].append(self.extract_function_info(node))
                
        return file_info
    
    def _extract_todos(self, source: str) -> List[Dict[str, Any]]:
        """Extract TODO and FIXME comments from source"""
        todos = []
        lines = source.split('\n')
        for i, line in enumerate(lines):
            line_num = i + 1
            # Look for TODO/FIXME in comments
            if '#' in line:
                comment_start = line.find('#')
                comment = line[comment_start:].lower()
                if 'todo' in comment or 'fixme' in comment:
                    todos.append({
                        'line': line_num,
                        'text': line.strip(),
                        'type': 'TODO' if 'todo' in comment else 'FIXME'
                    })
        return todos
    
    def _detect_phase_violations_in_source(self, source: str, filepath: str) -> List[Dict[str, Any]]:
        """Detect potential phase violations in source code"""
        
        # Skip the analyzer's own files
        import os
        filename = os.path.basename(filepath)
        
        # Skip both old and new analyzer filenames
        analyzer_files = ['analyze.py', 'ast_analyzer.py', '__init__.py']
        if filename in analyzer_files:
            return []
        
        # Also skip by checking file path patterns
        skip_patterns = ['tools/analysis/', 'tools\\analysis\\']
        for pattern in skip_patterns:
            if pattern in filepath.replace('\\', '/'):
                return []
        
        violations = []
        lines = source.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Remove comments from the line before checking
            if '#' in line:
                code_part = line.split('#')[0]
            else:
                code_part = line
            
            line_lower = code_part.lower().strip()
            
            # Skip empty lines after removing comments
            if not line_lower:
                continue
            
            # Check for phase violation patterns
            for pattern in self.phase_violation_patterns:
                if pattern in line_lower:
                    violations.append({
                        'line': line_num,
                        'pattern': pattern,
                        'text': line.strip(),
                        'file': filepath
                    })
            
            # Check for direct AI calls (simplistic detection)
            if 'ai.' in line_lower and 'call' in line_lower and 'direct' in line_lower:
                violations.append({
                    'line': line_num,
                    'pattern': 'direct_ai_call',
                    'text': line.strip(),
                    'file': filepath
                })
        
        return violations

    def _get_code_context(self, source: str, line_num: int, context_lines: int = 3) -> str:
        """Get lines around the violation for context"""
        lines = source.split('\n')
        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)
        context_lines_output = []
        
        for i in range(start, end):
            line_number = i + 1
            line_text = lines[i]
            if line_number == line_num:
                context_lines_output.append(f">>> {line_number:4d}: {line_text}")
            else:
                context_lines_output.append(f"    {line_number:4d}: {line_text}")
        
        return '\n'.join(context_lines_output)

    def should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored using exact component matching"""
        # Convert to Path object for proper component analysis
        path_obj = Path(str(path))
        
        # Check each path component against ignore_dirs
        for part in path_obj.parts:
            # Exact match (case-insensitive for Windows)
            if part in self.ignore_dirs:
                return True
            
            # Hidden directories (starting with .) except . and ..
            if part.startswith('.') and part not in ['.', '..']:
                # Check if this part is a directory in the current path
                idx = path_obj.parts.index(part)
                test_path = Path(*path_obj.parts[:idx+1])
                if test_path.exists() and test_path.is_dir():
                    return True
        
        return False
    
    def scan_project(self, base_path: str = ".") -> List[Dict[str, Any]]:
        """Scan a project directory and parse all Python files"""
        project_data = []
        base_path = Path(base_path).resolve()

        # Add documentation directories to ignore
        self.ignore_dirs.extend(['docs', 'DOCS', 'documentation', 'doc'])
        
        for root, dirs, files in os.walk(base_path):
            root_path = Path(root)
            
            # Filter directories BEFORE os.walk recurses into them
            dirs[:] = [
                d for d in dirs 
                if not self.should_ignore(root_path / d)
            ]
            
            # Skip ignored root directories
            if self.should_ignore(root_path):
                continue
            
            for file in files:
                if file.endswith('.py'):
                    full_path = root_path / file
                    if not self.should_ignore(full_path):
                        try:
                            file_data = self.parse_python_file(str(full_path))
                            if file_data:
                                project_data.append(file_data)
                        except Exception as e:
                            print(f"Error processing {full_path}: {e}")
        
        return project_data
    
    def _detect_ai_boundary_violations(self, tree, filepath):
        """Detect direct ollama/openai calls outside boundary files"""
        violations = []
        
        # Get the file path in lowercase for comparison
        filepath_lower = filepath.lower()
        
        # Skip boundary files themselves
        if any(x in filepath_lower for x in ['dm_chat_ai', 'ai_boundary', 'context_builder']):
            return violations
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Detect ollama.chat() or openai calls
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if node.func.value.id in ['ollama', 'openai', 'anthropic']:
                        # Get the actual call text
                        try:
                            call_text = ast.unparse(node)
                        except:
                            call_text = f"{node.func.value.id}.{node.func.attr}()"
                        
                        # FIXED: No longer restricting to specific files
                        # Any direct AI call outside boundary files is a violation
                        violations.append({
                            'line': node.lineno,
                            'type': 'DIRECT_AI_CALL',
                            'pattern': f'{node.func.value.id}.{node.func.attr}',
                            'text': call_text,
                            'file': filepath,
                            'message': f'Direct {node.func.value.id} call detected. Should use DMChatAI boundary instead.'
                        })
        return violations
    
    def analyze_dependencies(self, project_data: List[Dict]) -> Dict[str, Any]:
        """Analyze import dependencies between files"""
        dependencies = {}
        
        for file_data in project_data:
            file_path = file_data['path']
            dependencies[file_path] = {
                'imports': [],
                'imported_by': []
            }
            
            for imp in file_data['imports']:
                if imp['type'] == 'from':
                    dependencies[file_path]['imports'].append(imp['module'])
                elif imp['type'] == 'import':
                    for name in imp['names']:
                        dependencies[file_path]['imports'].append(name['name'])
        
        # Build reverse dependencies
        for file_path, deps in dependencies.items():
            for imported_file in deps['imports']:
                for other_file, other_deps in dependencies.items():
                    if imported_file in other_file and other_file != file_path:
                        if 'imported_by' not in dependencies[other_file]:
                            dependencies[other_file]['imported_by'] = []
                        dependencies[other_file]['imported_by'].append(file_path)
        
        return dependencies
    
    def find_large_classes(self, project_data: List[Dict], line_threshold: int = 200) -> List[Dict[str, Any]]:
        """Find classes with many methods or lines"""
        large_classes = []
        
        for file_data in project_data:
            for class_info in file_data['classes']:
                if len(class_info['methods']) > 10:  # More than 10 methods
                    large_classes.append({
                        'file': file_data['path'],
                        'class': class_info['name'],
                        'methods_count': len(class_info['methods']),
                        'line': class_info['lineno'],
                        'reason': 'Too many methods'
                    })
        
        return large_classes


def main():
    """CLI entry point for backward compatibility - FIXED VERSION"""
    parser = argparse.ArgumentParser(description='Extract project structure from Python files')
    parser.add_argument('base_dir', nargs='?', default='.', help='Base directory to scan')
    parser.add_argument('-i', '--ignore', nargs='+', 
                        default=['__pycache__', 'venv', '.git', 'Lib', 'core', 'archive', 
                        'node_modules', '.idea', '.vscode', 'docs', 'DOCS', 'documentation'],
                        help='Directories to ignore')
    parser.add_argument('-o', '--output', default='project_ast.json',
                        help='Output JSON file name')
    parser.add_argument('--mode', choices=['structure', 'deps', 'violations', 'todos'], 
                        default='structure', help='Analysis mode')
    parser.add_argument('--show-code', action='store_true', 
                        help='Show code context for violations')
    
    args = parser.parse_args()
    
    print(f"Scanning project in: {args.base_dir}")
    print(f"Ignoring directories: {', '.join(args.ignore)}")
    print(f"Mode: {args.mode}")
    
    analyzer = ASTAnalyzer(ignore_dirs=args.ignore)
    project_data = analyzer.scan_project(args.base_dir)
    
    print(f"Scanned {len(project_data)} Python files")
    
    if args.mode == 'structure':
        output_data = project_data
    elif args.mode == 'deps':
        output_data = analyzer.analyze_dependencies(project_data)
    elif args.mode == 'violations':
        # Extract all phase violations
        violations = []
        for file_data in project_data:
            for violation in file_data.get('phase_violations', []):
                # Add file info to each violation
                violation['file'] = file_data['path']
                violation['context'] = analyzer._get_code_context(
                    file_data['source'], violation['line']
                )
                violations.append(violation)
        output_data = violations
        
        # SHOW VIOLATIONS IN CONSOLE
        if violations:
            print(f"\n{'='*80}")
            print(f"FOUND {len(violations)} PHASE VIOLATIONS:")
            print(f"{'='*80}")
            for i, violation in enumerate(violations, 1):
                print(f"\n{i}. {violation['file']}:{violation['line']}")
                print(f"   Type: {violation.get('type', 'PHASE_VIOLATION')}")
                print(f"   Pattern: {violation.get('pattern', 'N/A')}")
                if args.show_code or violation.get('context'):
                    print(f"   Code context:")
                    print(f"{violation.get('context', 'No context available')}")
                print(f"   Message: {violation.get('message', 'No message')}")
                print(f"   Line text: {violation.get('text', 'N/A')}")
        else:
            print("\n[OK] No phase violations found!")
            
    elif args.mode == 'todos':
        # Extract all TODOs
        todos = []
        for file_data in project_data:
            for todo in file_data.get('todos', []):
                todo['file'] = file_data['path']
                todo['context'] = analyzer._get_code_context(
                    file_data['source'], todo['line']
                )
                todos.append(todo)
        output_data = todos
    
    # Write to JSON file
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n[OK] Project analysis saved to {args.output}")
        print(f"   Items written: {len(output_data) if isinstance(output_data, list) else 'dict'}")
        
    except Exception as e:
        print(f"[FAIL] Error writing {args.output}: {e}")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({"error": str(e), "files_processed": len(project_data)}, f, indent=2)


if __name__ == '__main__':
    main()