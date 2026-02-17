"""Scout scanning logic."""
import ast
import json
import sqlite3
import re
import numpy as np
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from tools.analysis import utils
from tools.analysis import extractors
from tools.analysis import db_operations as db
from tools.analysis.embedding_model import embed_text
from tools.analysis.ast_analyzer import ASTAnalyzer  # keep as is
DEBUG = True

MUTATING_METHODS = {'update', 'save', 'delete', 'create', 'add', 'remove', 'insert', 'set', 'put', 'patch'}
STATE_HOLDERS = {'SessionSystem', 'GameEngine', 'WorldState', 'Database', 'Repository'}

def _method_has_mutation(node: ast.FunctionDef) -> bool:
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Attribute):
            if isinstance(subnode.func.value, ast.Name):
                obj = subnode.func.value.id
                method = subnode.func.attr
                if obj in STATE_HOLDERS and method in MUTATING_METHODS:
                    return True
    return False

def calculate_complexity(node: ast.FunctionDef) -> int:
    complexity = 1
    for subnode in ast.walk(node):
        if isinstance(subnode, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(subnode, ast.BoolOp):
            complexity += len(subnode.values) - 1
    return complexity

def extract_behavioral_contracts(tree: ast.AST, source: str) -> List[dict]:
    contracts = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith('_') and not node.name.startswith('__'):
                continue
            docstring = ast.get_docstring(node)
            contract = {
                'function': node.name,
                'line': node.lineno,
                'args': [arg.arg for arg in node.args.args if arg.arg != 'self'],
                'returns': None,
                'description': '',
                'side_effects': [],
                'raises': [],
                'preconditions': [],
                'testable_behaviors': [],
                'complexity_score': calculate_complexity(node),
            }
            if node.returns:
                try:
                    contract['returns'] = ast.unparse(node.returns)
                except:
                    contract['returns'] = str(type(node.returns))
            if docstring:
                lines = docstring.split('\n')
                contract['description'] = lines[0].strip()[:150]
                doc_lower = docstring.lower()
                # side effect patterns
                side_effect_patterns = [
                    (r'(?:updates?|modifies?|changes?|sets?)\s+(?:the\s+)?(\w+)', 'mutates {}'),
                    (r'(?:saves?|persists?|stores?)\s+(?:to|into)?\s+(\w+)', 'saves to {}'),
                    (r'(?:creates?|initializes?|builds?)\s+(?:a\s+)?(?:new\s+)?(\w+)', 'creates {}'),
                    (r'(?:sends?|emits?|triggers?)\s+(?:a\s+)?(\w+)', 'sends {}'),
                    (r'(?:clears?|resets?|removes?)\s+(?:the\s+)?(\w+)', 'clears {}'),
                ]
                for pattern, template in side_effect_patterns:
                    for match in re.finditer(pattern, doc_lower):
                        effect = template.format(match.group(1))
                        if effect not in contract['side_effects']:
                            contract['side_effects'].append(effect)
                if 'raises:' in doc_lower or 'raises ' in doc_lower:
                    raise_section = re.search(r'raises:?\s*(.+?)(?:\n\n|\Z)', doc_lower, re.DOTALL)
                    if raise_section:
                        exceptions = re.findall(r'\b([A-Z][a-zA-Z]*(?:Error|Exception))\b', raise_section.group(1))
                        contract['raises'] = list(set(exceptions))
                if 'example' in doc_lower or '>>>' in docstring:
                    contract['testable_behaviors'].append('has_doctest_examples')
                if 'returns' in doc_lower:
                    contract['testable_behaviors'].append('verifiable_return_value')
                if contract['raises']:
                    contract['testable_behaviors'].append('exception_conditions')
                if contract['side_effects']:
                    contract['testable_behaviors'].append('state_change_verification')
            # infer from AST
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Attribute):
                    if subnode.func.attr in ['generate_text', 'generate_structured_data', 'generate_embedding']:
                        contract['testable_behaviors'].append('ai_dependency_mock_required')
                    if subnode.func.attr in ['execute', 'commit', 'fetchone', 'fetchall']:
                        contract['testable_behaviors'].append('database_interaction')
                if isinstance(subnode, ast.Assign):
                    if isinstance(subnode.targets[0], ast.Attribute):
                        if isinstance(subnode.targets[0].value, ast.Name):
                            if subnode.targets[0].value.id in ['self', 'cls']:
                                contract['testable_behaviors'].append('internal_state_change')
            if (contract['description'] or contract['side_effects'] or contract['testable_behaviors'] or contract['complexity_score'] > 3):
                contracts.append(contract)
    return contracts

def analyze_file_for_scout(filepath: Path, project_root: Path, ignore_dirs: List[str]) -> Optional[Dict]:
    if utils.should_ignore(filepath, ignore_dirs):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError, Exception):
        return None

    analyzer = ASTAnalyzer(ignore_dirs=ignore_dirs)

    file_info = {
        'path': str(filepath.relative_to(project_root)),
        'imports': [],
        'classes': [],
        'functions': [],
        'line_count': len(source.splitlines()),
        'phase_violations': analyzer._detect_phase_violations_in_source(source, str(filepath), tree),
    }
    file_info['behavioral_contracts'] = extract_behavioral_contracts(tree, source)
    file_info['contract_count'] = len(file_info['behavioral_contracts'])

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            file_info['imports'].append(analyzer.extract_import_info(node))
        elif isinstance(node, ast.ClassDef):
            class_info = analyzer.extract_class_info(node)
            read_only_methods = []
            for method in class_info.get('methods', []):
                method_node = next((n for n in ast.walk(node) if isinstance(n, ast.FunctionDef) and n.name == method['name']), None)
                if method_node and not _method_has_mutation(method_node):
                    read_only_methods.append(f"{node.name}.{method['name']}")
            class_info['read_only_methods'] = read_only_methods
            file_info['classes'].append(class_info)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            file_info['functions'].append(analyzer.extract_function_info(node))

    mutations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                obj = node.func.value.id
                method = node.func.attr
                if obj in STATE_HOLDERS and method in MUTATING_METHODS:
                    mutations.append({
                        'line': node.lineno,
                        'call': f"{obj}.{method}",
                        'args': ast.unparse(node.args) if hasattr(ast, 'unparse') and node.args else ''
                    })
    file_info['mutations'] = mutations

    file_info['role'] = utils.classify_role(file_info['path'])
    file_info['is_hot'] = bool(file_info.get('phase_violations') or mutations)
    return file_info

def build_import_map(project_root: Path, ignore_dirs: List[str]) -> Dict[str, List[str]]:
    import_map = defaultdict(list)
    for py_file in project_root.rglob('*.py'):
        if utils.should_ignore(py_file, ignore_dirs):
            continue
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                tree = ast.parse(f.read())
            rel_path = str(py_file.relative_to(project_root))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split('.')[0]
                        import_map[mod].append(rel_path)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod = node.module.split('.')[0]
                        import_map[mod].append(rel_path)
        except Exception:
            continue
    return dict(import_map)

def find_corresponding_test(source_path: str, project_root: Path) -> Optional[str]:
    source_file = Path(source_path)
    test_dir = project_root / 'tests'
    test_file = test_dir / f"test_{source_file.stem}.py"
    if test_file.exists():
        return str(test_file.relative_to(project_root))
    for subdir in test_dir.iterdir():
        if subdir.is_dir():
            nested_test = subdir / f"test_{source_file.stem}.py"
            if nested_test.exists():
                return str(nested_test.relative_to(project_root))
    return None

def run_scout(project_root: str, db_path: str, force: bool = False, ignore_dirs: List[str] = None, verbose: bool = False):
    project_root = Path(project_root).resolve()
    db_path = Path(db_path)
    if not ignore_dirs:
        ignore_dirs = ['__pycache__', 'venv', '.git', 'node_modules', 'Lib', 'docs', 'archive']
    if db_path.exists() and not force:
        print(f"✅ Scout DB already exists: {db_path} (use --force to rescan)")
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print("🔎 Scout: scanning project...")
    all_py_files = list(project_root.rglob('*.py'))
    py_files = [f for f in all_py_files if not utils.should_ignore(f, ignore_dirs)]
    print(f"   Found {len(py_files)} Python files (ignored {len(all_py_files) - len(py_files)}).")

    if verbose:
        print("   Building import map...")
    import_map = build_import_map(project_root, ignore_dirs)

    file_infos = []
    vocabulary = defaultdict(list)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    if force:
        # Drop main tables (keep schema)
        cur.execute("DROP TABLE IF EXISTS files")
        cur.execute("DROP TABLE IF EXISTS concepts")
        cur.execute("DROP TABLE IF EXISTS clusters")
        cur.execute("DROP TABLE IF EXISTS meta")
        cur.execute("DROP TABLE IF EXISTS test_coverage")
        cur.execute("DROP TABLE IF EXISTS behavioral_contracts")
        cur.execute("DROP TABLE IF EXISTS imports")
        cur.execute("DROP TABLE IF EXISTS method_params")
        cur.execute("DROP TABLE IF EXISTS dict_key_access")
        cur.execute("DROP TABLE IF EXISTS class_constructors")
        cur.execute("DROP TABLE IF EXISTS file_embeddings")
        cur.execute("DROP TABLE IF EXISTS test_patterns")

        # Create tables if they don't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                role TEXT,
                line_count INTEGER,
                is_hot INTEGER
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                concept TEXT,
                file_path TEXT,
                PRIMARY KEY (concept, file_path),
                FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clusters (
                cluster_name TEXT PRIMARY KEY,
                file_paths TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_coverage (
                source_path TEXT PRIMARY KEY,
                test_path TEXT,
                test_exists INTEGER DEFAULT 0,
                FOREIGN KEY (source_path) REFERENCES files(path)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS behavioral_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                function_name TEXT,
                line_number INTEGER,
                description TEXT,
                side_effects TEXT,  -- JSON array
                testable_behaviors TEXT,  -- JSON array
                complexity_score INTEGER,
                FOREIGN KEY (file_path) REFERENCES files(path)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS imports (
                importer_path TEXT,
                full_module TEXT,
                import_type TEXT,
                line_number INTEGER,
                FOREIGN KEY (importer_path) REFERENCES files(path) ON DELETE CASCADE
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_imports_importer ON imports(importer_path)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_imports_full_module ON imports(full_module)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS method_params (
                file_path TEXT,
                class_name TEXT,
                method_name TEXT,
                param_name TEXT,
                param_position INTEGER,
                FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dict_key_access (
                file_path TEXT,
                function_name TEXT,
                dict_var TEXT,
                key TEXT,
                FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS class_constructors (
                file_path TEXT,
                class_name TEXT,
                param_name TEXT,
                param_position INTEGER,
                FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS file_embeddings (
                file_path TEXT PRIMARY KEY,
                embedding BLOB NOT NULL,
                FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_file TEXT,
                pattern_type TEXT,
                pattern_data TEXT,
                extracted_from TEXT,
                FOREIGN KEY (source_file) REFERENCES files(path)
            )
        """)


    for i, py_file in enumerate(py_files):
        if verbose and (i % 50 == 0):
            print(f"   Processing file {i+1}/{len(py_files)}...")
        file_info = analyze_file_for_scout(py_file, project_root, ignore_dirs)
        if not file_info:
            continue

        # Insert file record FIRST
        db.insert_file(conn,
                       file_info['path'],
                       file_info,
                       file_info.get('role', 'Unknown'),
                       file_info.get('line_count', 0),
                       file_info.get('is_hot', False))

        module_name = py_file.stem
        file_info['imported_by'] = import_map.get(module_name, [])
        file_infos.append(file_info)

        # Extract detailed API information (dict keys, params, etc.) and insert
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            tree = ast.parse(source)

            for func_node in ast.walk(tree):
                if isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Determine if it's a method (enclosed in class)
                    in_class = False
                    for parent in ast.walk(tree):
                        if parent != func_node and isinstance(parent, ast.ClassDef):
                            for child in ast.walk(parent):
                                if child is func_node:
                                    in_class = True
                                    break
                            if in_class:
                                break
                    # Dict key accesses
                    for dict_var, key in extractors.extract_dict_key_accesses(func_node):
                        db.insert_dict_key(conn, file_info['path'], func_node.name, dict_var, key)
                    # Parameters (top-level only)
                    if not in_class:
                        for param_name, pos in extractors.extract_method_params(func_node):
                            db.insert_method_param(conn, file_info['path'], None, func_node.name, param_name, pos)
            # Classes: constructor and methods
            for cls in file_info.get('classes', []):
                cls_name = cls['name']
                class_node = None
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == cls_name:
                        class_node = node
                        break
                if class_node:
                    # __init__
                    for param_name, pos in extractors.extract_constructor_params(class_node):
                        db.insert_class_constructor(conn, file_info['path'], cls_name, param_name, pos)
                    # Other methods
                    for method_node in class_node.body:
                        if isinstance(method_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_name = method_node.name
                            for param_name, pos in extractors.extract_method_params(method_node):
                                db.insert_method_param(conn, file_info['path'], cls_name, method_name, param_name, pos)
        except Exception as e:
            if verbose:
                print(f"   Warning: could not extract detailed info from {py_file}: {e}")

        # Generate and store embedding
        try:
            with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            tree = ast.parse(source)
            summary_parts = []
            module_doc = ast.get_docstring(tree)
            if module_doc:
                summary_parts.append(module_doc)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        summary_parts.append(doc)
            identifiers = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    identifiers.append(node.id)
            if identifiers:
                summary_parts.append(" ".join(identifiers))
            summary = "\n".join(summary_parts)
            if summary.strip():
                emb = embed_text(summary)
                emb_bytes = emb.astype(np.float32).tobytes()
                db.insert_embedding(conn, file_info['path'], emb_bytes)
        except Exception as e:
            if verbose:
                print(f"   Warning: could not generate embedding for {py_file}: {e}")

        # Insert imports
        imports_found = extractors.extract_imports_from_ast(tree, file_info['path'])
        if DEBUG:
            print(f"DEBUG: imports_found = {imports_found}") 
            print(f"DEBUG: Imports found in {py_file.name}: {imports_found}")
        for (full_mod, imp_type, lineno) in imports_found:
            db.insert_import(conn, file_info['path'], full_mod, imp_type, lineno)

        # Add to vocabulary (for concept table) – now outside the try block
        for cls in file_info.get('classes', []):
            for word in utils.split_identifier(cls['name']):
                vocabulary[word].append(file_info['path'])
        for func in file_info.get('functions', []):
            for word in utils.split_identifier(func['name']):
                vocabulary[word].append(file_info['path'])

    # After first loop, insert test coverage, behavioral contracts, concepts, clusters
    for file_info in file_infos:
        test_path = find_corresponding_test(file_info['path'], project_root)
        db.insert_test_coverage(conn, file_info['path'], test_path, test_path is not None)

        for contract in file_info.get('behavioral_contracts', []):
            db.insert_behavioral_contract(
                conn,
                file_info['path'],
                contract['function'],
                contract['line'],
                contract['description'],
                contract.get('side_effects', []),
                contract.get('testable_behaviors', []),
                contract.get('complexity_score', 0)
            )

    # Insert concepts
    for word, paths in vocabulary.items():
        for path in set(paths):
            db.insert_concept(conn, word, path)

    # Load clusters from categories file
    cat_file = project_root / 'ai_context' / 'discovered_categories.json'
    if cat_file.exists():
        try:
            with open(cat_file, 'r', encoding='utf-8') as f:
                categories = json.load(f)
            clusters = categories.get('clusters', [])
            all_paths = {f['path'] for f in file_infos}
            for cluster in clusters:
                name = cluster.get('name', 'unknown')
                cluster_files = [f for f in cluster.get('files', []) if f in all_paths]
                db.insert_cluster(conn, name, cluster_files)
            if verbose:
                print(f"   Loaded {len(clusters)} clusters from {cat_file.name}.")
        except Exception as e:
            print(f"   Warning: could not load clusters: {e}")

    # Insert meta data
    db.insert_meta(conn, "scout_timestamp", datetime.now().isoformat())
    db.insert_meta(conn, "project_root", str(project_root))
    db.insert_meta(conn, "file_count", str(len(file_infos)))

    conn.commit()
    conn.close()
    print(f"✅ Scout DB saved: {db_path} ({len(file_infos)} files, {len(vocabulary)} concepts)")