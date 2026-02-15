"""Test template library for generating high-quality tests from patterns."""
import sqlite3
import json
import re
import ast
from pathlib import Path
from typing import Dict, List, Optional

class TestTemplateLibrary:
    """Manages test patterns extracted from existing high-quality tests."""
    
    def __init__(self, templates_dir: Path = None):
        self.templates_dir = templates_dir or Path(__file__).parent / 'templates'
        self.templates_dir.mkdir(exist_ok=True)
        self._cache = {}
    
    def extract_template_from_file(self, test_file: Path) -> Optional[dict]:
        """Analyze a test file and extract its patterns."""
        try:
            import ast
            with open(test_file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            template = {
                'source_file': str(test_file),
                'patterns': {
                    'imports': [],
                    'fixtures': [],
                    'mock_strategies': [],
                    'assertion_patterns': [],
                    'test_structure': []
                },
                'example_tests': []
            }
            
            # Extract imports
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        template['patterns']['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    names = [a.name for a in node.names]
                    template['patterns']['imports'].append(f"from {module} import {', '.join(names)}")
            
            # Find fixtures and test functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if it's a fixture
                    decorators = [ast.unparse(d) for d in node.decorator_list]
                    is_fixture = any('fixture' in d for d in decorators)
                    
                    if is_fixture:
                        template['patterns']['fixtures'].append({
                            'name': node.name,
                            'args': [a.arg for a in node.args.args],
                            'has_mock_arg': any('mock' in a.arg.lower() for a in node.args.args),
                            'return_type': ast.unparse(node.returns) if node.returns else None
                        })
                    elif node.name.startswith('test_'):
                        # Analyze test function
                        test_info = {
                            'name': node.name,
                            'docstring': ast.get_docstring(node) or '',
                            'uses_mocks': False,
                            'mock_targets': [],
                            'assertion_count': 0,
                            'fixture_deps': [a.arg for a in node.args.args if a.arg != 'self'],
                            'complexity': self._count_assertions(node)
                        }
                        
                        # Find mock usage
                        for subnode in ast.walk(node):
                            if isinstance(subnode, ast.Call):
                                func_str = ast.unparse(subnode.func) if hasattr(ast, 'unparse') else ''
                                if 'patch' in func_str or 'Mock' in func_str:
                                    test_info['uses_mocks'] = True
                                if 'mock_' in func_str or 'call_args' in func_str:
                                    test_info['mock_targets'].append(func_str)
                            
                            if isinstance(subnode, ast.Assert):
                                test_info['assertion_count'] += 1
                        
                        template['patterns']['test_structure'].append(test_info)
                        
                        # Save full example if it's a good one
                        if test_info['assertion_count'] >= 2 and test_info['uses_mocks']:
                            try:
                                # Extract the function source
                                lines = source.split('\n')
                                start_line = node.lineno - 1
                                # Find end by looking for next function or end of file
                                end_line = len(lines)
                                for i, line in enumerate(lines[start_line+1:], start=start_line+1):
                                    if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                                        if line.startswith('def ') or line.startswith('class '):
                                            end_line = i
                                            break
                                
                                test_source = '\n'.join(lines[start_line:end_line])
                                template['example_tests'].append({
                                    'name': node.name,
                                    'source': test_source,
                                    'focus': self._categorize_test(node.name, test_info['docstring'])
                                })
                            except:
                                pass
            
            # Detect mock strategies
            if 'patch' in source:
                template['patterns']['mock_strategies'].append('unittest.mock.patch')
            if 'Mock()' in source or 'Mock(' in source:
                template['patterns']['mock_strategies'].append('Mock instantiation')
            if 'mock_' in source and 'return_value' in source:
                template['patterns']['mock_strategies'].append('return_value configuration')
            if 'call_args' in source or 'call_count' in source:
                template['patterns']['mock_strategies'].append('call verification')
            
            # Detect assertion patterns
            if 'assert' in source:
                if 'call_args' in source:
                    template['patterns']['assertion_patterns'].append('mock_call_verification')
                if '==' in source and 'assert' in source:
                    template['patterns']['assertion_patterns'].append('equality_assertions')
                if 'isinstance' in source or 'type(' in source:
                    template['patterns']['assertion_patterns'].append('type_checking')
                if 'raises' in source:
                    template['patterns']['assertion_patterns'].append('exception_testing')
            
            return template
            
        except Exception as e:
            print(f"Error extracting template from {test_file}: {e}")
            return None
    
    def _count_assertions(self, node: ast.AST) -> int:
        """Count assertions in a test function."""
        count = 0
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Assert):
                count += 1
            # Also count mock assert calls
            if isinstance(subnode, ast.Call):
                if hasattr(subnode.func, 'attr') and 'assert' in subnode.func.attr:
                    count += 1
        return count
    
    def _categorize_test(self, name: str, docstring: str) -> str:
        """Categorize what kind of test this is."""
        text = (name + ' ' + docstring).lower()
        if any(x in text for x in ['create', 'build', 'init', 'construct']):
            return 'construction'
        if any(x in text for x in ['call', 'invoke', 'execute', 'run']):
            return 'execution'
        if any(x in text for x in ['error', 'exception', 'fail', 'invalid']):
            return 'error_handling'
        if any(x in text for x in ['mock', 'patch', 'fake']):
            return 'mocking_strategy'
        return 'general'
    
    def save_template(self, template: dict, name: str):
        """Save a template to disk."""
        path = self.templates_dir / f"{name}.json"
        with open(path, 'w') as f:
            json.dump(template, f, indent=2)
        self._cache[name] = template
    
    def load_template(self, name: str) -> Optional[dict]:
        """Load a template by name."""
        if name in self._cache:
            return self._cache[name]
        
        path = self.templates_dir / f"{name}.json"
        if path.exists():
            with open(path) as f:
                template = json.load(f)
                self._cache[name] = template
                return template
        return None
    
    def find_best_template(self, target_concepts: List[str]) -> Optional[dict]:
        """Find the template most similar to target concepts."""
        best_score = 0
        best_template = None
        
        for template_file in self.templates_dir.glob('*.json'):
            template = self.load_template(template_file.stem)
            if not template:
                continue
            
            # Score based on concept overlap
            score = 0
            template_text = json.dumps(template).lower()
            for concept in target_concepts:
                if concept.lower() in template_text:
                    score += 1
            
            # Bonus for high-quality examples
            score += len(template.get('example_tests', [])) * 0.5
            
            if score > best_score:
                best_score = score
                best_template = template
        
        return best_template if best_score > 0 else None

    def build_generation_prompt(self, target_file: str, contracts: List[dict], 
                                template: dict, module_list: str = "") -> str:
        """Build a prompt for test generation using template patterns."""
        
        # Extract key patterns from template
        imports = '\n'.join(template['patterns']['imports'][:10])
        fixtures = template['patterns']['fixtures']
        mock_strategies = template['patterns']['mock_strategies']
        example = template['example_tests'][0] if template['example_tests'] else None
        
        # Build contracts description
        contracts_desc = []
        for c in contracts[:5]:  # Top 5 most complex contracts
            behaviors = ', '.join(c.get('testable_behaviors', []))
            side_effects = ', '.join(c.get('side_effects', []))
            contracts_desc.append(f"""
Function: {c['function']}({', '.join(c['args'])})
Description: {c['description']}
Side effects: {side_effects}
Testable aspects: {behaviors}
""")
        
        prompt = f"""You are a senior Python test engineer. Write a pytest test file for: {target_file}

**REFERENCE TEMPLATE (from similar tested file):**
Imports used:
```python
{imports}
```
Fixture pattern:
```python
{self._format_fixture(fixtures[0]) if fixtures else '# No fixtures found'}
```
Mock strategies in this codebase: {', '.join(mock_strategies)}
{'Example test from similar file:' if example else ''}
```python
{example['source'] if example else ''}
```
**Existing top‑level modules in this project:** {module_list}
TARGET FUNCTIONS TO TEST:
{chr(10).join(contracts_desc)}
GENERATION RULES (MUST FOLLOW):
Only patch modules and attributes that exist in the codebase – use the exact names shown in the behavioral contracts.
Do not invent new modules, classes, or attributes.
When using @patch, the mock parameter comes AFTER any fixtures in the test function signature (fixtures first, then patched mocks).
Never treat a fixture as a real object; fixtures are setup functions that return objects – pytest injects the return value automatically.
Use the behavioral contracts' function names and file paths to determine correct import paths.
Include tests for error conditions if 'exception_conditions' is in testable_behaviors.
DO NOT just test hasattr – test actual behavior (return values, side effects, exceptions).
Follow the fixture pattern: create dependencies as fixtures with proper mocking.
Output only the complete Python test file, no explanations, no metadata, no commentary. Start with the imports and end with the last line of code. Do not include lines like "Model: ..." or "Here is the test:".
- Each test function must follow the Arrange‑Act‑Assert pattern:
  * Arrange: set up mocks, fixtures, and input data.
  * Act: call the function being tested and store its return value.
  * Assert: verify the return value, side effects, and/or mock calls.
- All variables used in the test must be defined inside the test function (or as fixtures).
- Never leave a test incomplete – every test must contain at least one assertion and the function call it is testing.
- Do not include any placeholder comments like "# Act" without actual code.
"""
        return prompt
    
    def _format_fixture(self, fixture: dict) -> str:
        """Format a fixture for the prompt."""
        args_str = ', '.join(fixture['args'])
        return f"@pytest.fixture\ndef {fixture['name']}({args_str}):\n    # Setup code here\n    return mock_object"

class TestValidator:
    """Validate generated tests against actual codebase structure."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
    
    def validate_mock_target(self, target_path: str) -> tuple[bool, str]:
        """Check if a mock target (e.g., 'dungeon_neo.api.get_image') actually exists."""
        parts = target_path.split('.')
        
        # Try to find the module
        module_parts = []
        for i, part in enumerate(parts):
            candidate = '.'.join(parts[:i+1])
            # Check in scout DB
            row = self.conn.execute(
                "SELECT path FROM files WHERE path LIKE ? LIMIT 1",
                (f"%{candidate.replace('.', '/')}%",)
            ).fetchone()
            if row:
                module_parts.append(part)
            else:
                break
        
        if not module_parts:
            return False, f"Module not found: {parts[0]}"
        
        # Check if attribute exists in the file's exports
        remaining = parts[len(module_parts):]
        if remaining:
            # Check if function/class exists in the file
            file_row = self.conn.execute(
                "SELECT data FROM files WHERE path LIKE ?",
                (f"%{module_parts[-1]}.py%",)
            ).fetchone()
            
            if file_row:
                data = json.loads(file_row['data'])
                available_names = (
                    [c['name'] for c in data.get('classes', [])] +
                    [f['name'] for f in data.get('functions', [])]
                )
                
                for attr in remaining:
                    if attr not in available_names:
                        return False, f"'{attr}' not found in {'.'.join(module_parts)}. Available: {available_names[:10]}"
        
        return True, "Valid"

    def validate_imports(self, code: str) -> list[str]:
        """Check that all imported modules exist in the codebase. Return list of missing modules."""
        import ast
        missing = []
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if not self._module_exists(module):
                        missing.append(module)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module
                    if not self._module_exists(module):
                        missing.append(module)
        return missing

    def _module_exists(self, module: str) -> bool:
        """Check if a dotted module name corresponds to a Python file in the DB."""
        # Convert module to relative path: e.g., 'dungeon_neo.dungeon_system' -> 'dungeon_neo/dungeon_system.py'
        path_candidate = module.replace('.', '/') + '.py'
        # Also check for __init__.py? If module is a package, the file might be __init__.py inside that directory.
        # For simplicity, we'll check both the file and package existence.
        # We'll query the files table for paths that start with the module path as a directory.
        # But a direct file match is easiest.
        cur = self.conn.cursor()
        # Check direct file
        cur.execute("SELECT 1 FROM files WHERE path = ?", (path_candidate,))
        if cur.fetchone():
            return True
        # Check if it's a package: there should be an __init__.py in that directory.
        package_init = module.replace('.', '/') + '/__init__.py'
        cur.execute("SELECT 1 FROM files WHERE path = ?", (package_init,))
        if cur.fetchone():
            return True
        return False
    
    def validate_fixture_usage(self, test_code: str, available_fixtures: list) -> list[str]:
        """Find fixture references that don't exist."""
        issues = []
        
        # Find @pytest.fixture decorated functions
        fixture_pattern = r'@pytest\.fixture.*?\ndef\s+(\w+)'
        defined_fixtures = re.findall(fixture_pattern, test_code, re.DOTALL)
        
        # Find function parameters that look like fixtures
        test_pattern = r'def\s+test_\w+\((.*?)\):'
        for match in re.finditer(test_pattern, test_code):
            params = [p.strip().split(':')[0].split('=')[0].strip() 
                     for p in match.group(1).split(',') if p.strip()]
            
            for param in params:
                if param == 'self':
                    continue
                if param not in defined_fixtures and param not in available_fixtures:
                    # Check if it's a mock from @patch
                    if not f"'{param}'" in test_code:  # Rough heuristic
                        issues.append(f"Undefined fixture '{param}' in {match.group(0)}")
        
        return issues
    
    def suggest_correct_mock(self, wrong_target: str, intended_behavior: str) -> str:
        """Suggest correct mock target based on behavioral contracts in DB."""
        # Search for functions with similar behavior
        rows = self.conn.execute("""
            SELECT file_path, function_name, description
            FROM behavioral_contracts
            WHERE description LIKE ? OR side_effects LIKE ?
            LIMIT 5
        """, (f'%{intended_behavior}%', f'%{intended_behavior}%')).fetchall()
        
        if rows:
            suggestions = [f"{r['file_path']}:{r['function_name']}" for r in rows]
            return f"Did you mean: {', '.join(suggestions)}?"
        return "No similar functions found in codebase"
    