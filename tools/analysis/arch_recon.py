#!/usr/bin/env python3
"""
arch_recon.py – Architecture Reconnaissance + Scout + Recon + Ask + Context + Consult + Test

Modes:
  --scout                     : full project scan → SQLite DB
  <intent>                    : instant intent‑driven report (no truncation)
  --hot / --mutations / etc.  : pre‑canned reports
  --ask                       : interactive menu + free‑form questions
  --context <intent>          : build AI‑ready context package (brief|standard|deep)
  --consult <intent>          : context + send to AI (auto‑routed)
  --test <intent>             : generate pytest file using AI
  --test-update               : update existing test using git diff

No truncation. No guessing. All real data from your live scout DB.
"""
import os
import ast
import sys
import re
import json
import sqlite3
import argparse
import io
import contextlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime

# ----------------------------------------------------------------------
# Project tool imports – with explicit fallback
# ----------------------------------------------------------------------
try:
    from tools.analysis.ast_analyzer import ASTAnalyzer
except ImportError:
    print("❌ Could not import ASTAnalyzer.", file=sys.stderr)
    sys.exit(1)

try:
    from tools.analysis.context_assembler import IntentParser
    _HAS_CONTEXT_ASSEMBLER = True
except ImportError:
    _HAS_CONTEXT_ASSEMBLER = False

# ----------------------------------------------------------------------
# TUNABLE HEURISTICS – modify these to match your architecture
# ----------------------------------------------------------------------
ROLE_RULES = [
    (lambda p: '/routes/' in p, 'Adapter'),
    (lambda p: '/ai/' in p, 'AI-Facing'),
    (lambda p: 'dm_chat_ai' in p or 'ai_boundary' in p, 'Boundary'),
]
DEFAULT_ROLE = 'Core'

MUTATING_METHODS = {'update', 'save', 'delete', 'create', 'add', 'remove', 'insert', 'set', 'put', 'patch'}
STATE_HOLDERS = {'SessionSystem', 'GameEngine', 'WorldState', 'Database', 'Repository'}

MIN_CONCEPT_LENGTH = 3

def ensure_db_fresh(db_path: Path, force: bool = False, no_prompt: bool = False,
                    project_root: str = '.', ignore_dirs: List[str] = None, verbose: bool = False):
    """Check if DB exists/prompt to scan. Returns True if ready, False if cancelled."""
    if db_path.exists() and not force:
        # Optional: check age (e.g., older than 1 day)
        age = datetime.now() - datetime.fromtimestamp(db_path.stat().st_mtime)
        if age.days >= 1 and not no_prompt:
            print(f"🕒 Scout DB is {age.days} day(s) old.")
            answer = input("Rescan now? (Y/n): ").strip().lower()
            if answer != 'n':
                force = True
        # else proceed
    if not db_path.exists() and not no_prompt:
        print("❌ Scout DB not found.")
        answer = input("Run a full scout scan now? (Y/n): ").strip().lower()
        if answer != 'n':
            force = True
        else:
            return False

    if force:
        print("🔄 Running scout scan...")
        run_scout(project_root, str(db_path), force=True, ignore_dirs=ignore_dirs, verbose=verbose)
    return True

# ----------------------------------------------------------------------
# GLOBAL ARCHITECTURE RULES – loaded from files or embedded
# ----------------------------------------------------------------------
def load_global_rules(project_root: Path) -> Dict[str, str]:
    """Load ai_contract.md and development_playbook.md if present."""
    rules = {
        'ai_contract': None,
        'playbook': None,
        'phase_sequence': 'Input → Interpretation → Authority → Mutation → Consequence → Persistence → View',
        'ai_contract_rules': [
            '1. AI NEVER owns state.',
            '2. AI NEVER mutates state directly.',
            '3. AI ONLY requests actions via interfaces.'
        ],
        'role_definitions': '\n'.join([
            '- Core: default role, no special path',
            '- Adapter: paths containing /routes/',
            '- AI-Facing: paths containing /ai/',
            '- Boundary: files matching dm_chat_ai or ai_boundary'
        ])
    }
    ai_contract = project_root / 'ai_context' / 'ai_contract.md'
    if ai_contract.exists():
        try:
            rules['ai_contract'] = ai_contract.read_text(encoding='utf-8')
        except:
            pass
    playbook = project_root / 'ai_context' / 'development_playbook.md'
    if playbook.exists():
        try:
            rules['playbook'] = playbook.read_text(encoding='utf-8')
        except:
            pass
    return rules

# ----------------------------------------------------------------------
# UTILITY FUNCTIONS (from context_manager.py – minimal standalone)
# ----------------------------------------------------------------------
def clean_ascii(text: str) -> str:
    """Replace common Unicode issues with ASCII equivalents."""
    if not text:
        return text
    fixes = {
        '├ó┼ôΓÇª': '...', '├ó┼ôΓÇÜ': ',', '├óΓÇ¥': '"', '├óΓÇ₧': '"',
        '├óΓÇÖ': "'", 'ΓåÆ': '->', 'ΓåÉ': '<-', 'ΓÇ£': '"', 'ΓÇ¥': '"',
        'ΓÇÿ': "'", 'ΓÇÖ': "'", 'ΓÇö': '-', 'ΓÇô': '-', 'ΓÇª': '...',
        '→': '->', '←': '<-', '✓': '[OK]', '✅': '[OK]', '⚠': '[WARN]',
        '🔍': '[SEARCH]', '🏗': '[BUILD]', '💾': '[SAVE]', '📝': '[NOTE]',
        '📋': '[DOC]', '🔧': '[TOOL]', '🎯': '[FOCUS]', '💻': '[CODE]',
        '✅': '[OK]', '❌': '[FAIL]', '•': '*', '—': '-', '…': '...',
    }
    for bad, good in fixes.items():
        text = text.replace(bad, good)
    return ''.join(c if ord(c) < 128 else '?' for c in text)

def split_identifier(name: str) -> List[str]:
    """CamelCase + snake_case → words, lowercased, filtered."""
    if not name:
        return []
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    s = s.replace('_', ' ')
    words = s.lower().split()
    return [w for w in words if len(w) >= MIN_CONCEPT_LENGTH]

def classify_role(path: str) -> str:
    """Infer architectural role from file path."""
    posix_path = path.replace('\\', '/')
    for condition, role in ROLE_RULES:
        if condition(posix_path):
            return role
    return DEFAULT_ROLE

def should_ignore(path: Path, ignore_dirs: List[str]) -> bool:
    """Check if path component matches any ignore_dir."""
    for part in path.parts:
        if part in ignore_dirs:
            return True
    return False

# ----------------------------------------------------------------------
# AST ANALYSIS – SINGLE PASS (for scout)
# ----------------------------------------------------------------------
def analyze_file_for_scout(filepath: Path, project_root: Path, ignore_dirs: List[str]) -> Optional[Dict]:
    if should_ignore(filepath, ignore_dirs):
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

    file_info['role'] = classify_role(file_info['path'])
    file_info['is_hot'] = bool(file_info.get('phase_violations') or mutations)
    return file_info

def _method_has_mutation(node: ast.FunctionDef) -> bool:
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Attribute):
            if isinstance(subnode.func.value, ast.Name):
                obj = subnode.func.value.id
                method = subnode.func.attr
                if obj in STATE_HOLDERS and method in MUTATING_METHODS:
                    return True
    return False

def build_import_map(project_root: Path, ignore_dirs: List[str]) -> Dict[str, List[str]]:
    import_map = defaultdict(list)
    for py_file in project_root.rglob('*.py'):
        if should_ignore(py_file, ignore_dirs):
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

# ----------------------------------------------------------------------
# SCOUT MODE
# ----------------------------------------------------------------------
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
    py_files = [f for f in all_py_files if not should_ignore(f, ignore_dirs)]
    print(f"   Found {len(py_files)} Python files (ignored {len(all_py_files) - len(py_files)}).")

    if verbose:
        print("   Building import map...")
    import_map = build_import_map(project_root, ignore_dirs)

    file_infos = []
    vocabulary = defaultdict(list)

    for i, py_file in enumerate(py_files):
        if verbose and (i % 50 == 0):
            print(f"   Processing file {i+1}/{len(py_files)}...")
        file_info = analyze_file_for_scout(py_file, project_root, ignore_dirs)
        if not file_info:
            continue
        module_name = py_file.stem
        file_info['imported_by'] = import_map.get(module_name, [])
        file_infos.append(file_info)

        for cls in file_info.get('classes', []):
            for word in split_identifier(cls['name']):
                vocabulary[word].append(file_info['path'])
        for func in file_info.get('functions', []):
            for word in split_identifier(func['name']):
                vocabulary[word].append(file_info['path'])

    print(f"   Analyzed {len(file_infos)} files.")

    def find_corresponding_test(source_path: str, project_root: Path) -> Optional[str]:
        """Find test file for a source file."""
        source_file = Path(source_path)
        test_dir = project_root / 'tests'
        
        # Pattern 1: tests/test_<module>.py
        test_file = test_dir / f"test_{source_file.stem}.py"
        if test_file.exists():
            return str(test_file.relative_to(project_root))
        
        # Pattern 2: tests/<subdir>/test_<module>.py
        for subdir in test_dir.iterdir():
            if subdir.is_dir():
                nested_test = subdir / f"test_{source_file.stem}.py"
                if nested_test.exists():
                    return str(nested_test.relative_to(project_root))
        
        return None

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    if force:
        cur.execute("DROP TABLE IF EXISTS files")
        cur.execute("DROP TABLE IF EXISTS concepts")
        cur.execute("DROP TABLE IF EXISTS clusters")
        cur.execute("DROP TABLE IF EXISTS meta")

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

    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("scout_timestamp", datetime.now().isoformat()))
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("project_root", str(project_root)))
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("file_count", str(len(file_infos))))

    for file_info in file_infos:
        file_info_copy = file_info.copy()
        file_info_copy.pop('source', None)
        for violation in file_info_copy.get('phase_violations', []):
            violation.pop('text', None)
        cur.execute(
            "INSERT OR REPLACE INTO files (path, data, role, line_count, is_hot) VALUES (?, ?, ?, ?, ?)",
            (
                file_info_copy['path'],
                json.dumps(file_info_copy, default=str),
                file_info_copy.get('role', 'Unknown'),
                file_info_copy.get('line_count', 0),
                1 if file_info_copy.get('is_hot') else 0
            )
        )

    for file_info in file_infos:
        test_path = find_corresponding_test(file_info['path'], project_root)
        cur.execute(
            "INSERT OR REPLACE INTO test_coverage (source_path, test_path, test_exists) VALUES (?, ?, ?)",
            (file_info['path'], test_path, 1 if test_path else 0)
        )

    for word, paths in vocabulary.items():
        for path in set(paths):
            cur.execute("INSERT OR IGNORE INTO concepts (concept, file_path) VALUES (?, ?)", (word, path))

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
                cur.execute("INSERT OR REPLACE INTO clusters (cluster_name, file_paths) VALUES (?, ?)",
                            (name, json.dumps(cluster_files)))
            if verbose:
                print(f"   Loaded {len(clusters)} clusters from {cat_file.name}.")
        except Exception as e:
            print(f"   Warning: could not load clusters: {e}")

    conn.commit()
    conn.close()
    print(f"✅ Scout DB saved: {db_path} ({len(file_infos)} files, {len(vocabulary)} concepts)")

def report_risk_heatmap(db_path: str, min_priority: str = "MEDIUM",
                        output_format: str = 'text', include_tools: bool = False,
                        layers: Optional[List[str]] = None):
    """Show files ranked by risk (hot + untested + widely used)."""
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}", file=sys.stderr)
        return 1

    PRIORITY_WEIGHTS = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    min_weight = PRIORITY_WEIGHTS.get(min_priority.upper(), 2)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # --- Build file filtering conditions (applied to the `files` table) ---
    file_conditions = []
    if not include_tools and (not layers or all(l not in ['tools', 'scripts'] for l in (layers or []))):
        file_conditions.append("REPLACE(f.path, '\\', '/') NOT LIKE 'tools/%'")
        file_conditions.append("REPLACE(f.path, '\\', '/') NOT LIKE 'Scripts/%'")
        file_conditions.append("REPLACE(f.path, '\\', '/') NOT LIKE 'scripts/%'")

    if layers:
        layer_conditions = []
        for layer in layers:
            layer_conditions.append(f"REPLACE(f.path, '\\', '/') LIKE '{layer}/%'")
        if layer_conditions:
            file_conditions.append("(" + " OR ".join(layer_conditions) + ")")

    # Helper to append file conditions to a WHERE clause
    def with_file_conditions(base_where=""):
        if not file_conditions:
            return base_where
        condition_str = " AND ".join(file_conditions)
        if base_where:
            return base_where + " AND " + condition_str
        else:
            return "WHERE " + condition_str

    # --- Diagnostics ---
    total = conn.execute(f"SELECT COUNT(*) FROM files f {with_file_conditions()}").fetchone()[0]
    total_all = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]

    print("📊 DATA DIAGNOSTICS:")
    print("-" * 50)
    if not include_tools:
        print(f"Project files (excl. tools): {total}")
        print(f"Total files (incl. tools): {total_all}")
    else:
        print(f"Total files: {total}")

    hot = conn.execute(f"""
        SELECT COUNT(*) FROM files f
        {with_file_conditions(base_where="WHERE is_hot = 1")}
    """).fetchone()[0]
    print(f"Hot files: {hot}")

    tested = conn.execute(f"""
        SELECT COUNT(*) FROM test_coverage tc
        JOIN files f ON tc.source_path = f.path
        {with_file_conditions(base_where="WHERE tc.test_exists = 1")}
    """).fetchone()[0]
    print(f"Files with tests: {tested}")

    importer_stats = conn.execute(f"""
        SELECT
            MIN(COALESCE(json_array_length(json_extract(data, '$.imported_by')), 0)) as min_imp,
            MAX(COALESCE(json_array_length(json_extract(data, '$.imported_by')), 0)) as max_imp,
            AVG(COALESCE(json_array_length(json_extract(data, '$.imported_by')), 0)) as avg_imp
        FROM files f {with_file_conditions()}
    """).fetchone()
    print(f"Importer count - Min: {importer_stats['min_imp']}, Max: {importer_stats['max_imp']}, Avg: {importer_stats['avg_imp']:.1f}")

    # Top importers
    print(f"\n📈 TOP 10 MOST IMPORTED FILES ({'incl.' if include_tools else 'excl.'} tools):")
    top_importers = conn.execute(f"""
        SELECT
            f.path,
            f.role,
            f.is_hot,
            COALESCE(json_array_length(json_extract(f.data, '$.imported_by')), 0) as importers,
            tc.test_exists,
            f.line_count
        FROM files f
        LEFT JOIN test_coverage tc ON f.path = tc.source_path
        {with_file_conditions()}
        ORDER BY importers DESC
        LIMIT 10
    """).fetchall()

    for row in top_importers:
        test_status = "✅" if row['test_exists'] else "❌"
        hot_status = "🔥" if row['is_hot'] else "  "
        print(f"  {hot_status} {test_status} {row['importers']:>3} imports  {row['path'][:60]}")

    print("\n" + "=" * 100)
    print("🔥 RISK HEATMAP (min priority: {})".format(min_priority))
    print("=" * 100)

    # Main risk query
    query = f"""
        SELECT
            f.path,
            f.role,
            f.line_count,
            f.is_hot,
            COALESCE(json_array_length(json_extract(f.data, '$.imported_by')), 0) as importer_count,
            COALESCE(json_array_length(json_extract(f.data, '$.mutations')), 0) as mutations,
            COALESCE(json_array_length(json_extract(f.data, '$.phase_violations')), 0) as violations,
            tc.test_exists,
            tc.test_path
        FROM files f
        LEFT JOIN test_coverage tc ON f.path = tc.source_path
        {with_file_conditions()}
        ORDER BY f.line_count DESC
    """

    rows = conn.execute(query).fetchall()

    # Calculate risk scores
    risk_items = []
    for row in rows:
        violations = row['violations'] or 0
        mutations = row['mutations'] or 0
        importers = row['importer_count'] or 0
        tested = 1 if row['test_exists'] else 0
        is_hot = row['is_hot'] or 0
        lines = row['line_count'] or 0

        risk_score = 0
        if not tested:
            risk_score += min(importers * 3, 30)
            risk_score += min(lines // 100, 20)
        if is_hot:
            risk_score += 15
        risk_score += violations * 5
        risk_score += mutations * 3
        if tested:
            risk_score -= 5

        if risk_score >= 20:
            priority = "CRITICAL"
        elif risk_score >= 10:
            priority = "HIGH"
        elif risk_score >= 5:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        if PRIORITY_WEIGHTS[priority] >= min_weight:
            risk_items.append({
                'path': row['path'],
                'role': row['role'],
                'risk_score': risk_score,
                'priority': priority,
                'violations': violations,
                'mutations': mutations,
                'importers': importers,
                'tested': bool(tested),
                'test_path': row['test_path'],
                'lines': lines,
                'is_hot': bool(is_hot)
            })

    risk_items.sort(key=lambda x: x['risk_score'], reverse=True)

    if output_format == 'json':
        print(json.dumps(risk_items[:20], indent=2))
    else:
        print(f"{'Priority':<10} {'Score':<6} {'Tested':<7} {'Hot':<5} {'Role':<12} {'Imp/Lines':<15} {'File'}")
        print("-" * 100)

        for item in risk_items[:30]:
            tested_flag = "✅" if item['tested'] else "❌"
            hot_flag = "🔥" if item['is_hot'] else "  "
            stats = f"{item['importers']}/{item['lines']}"
            print(f"{item['priority']:<10} {item['risk_score']:<6} {tested_flag:<7} {hot_flag:<5} {item['role']:<12} {stats:<15} {item['path'][:50]}")

        print("=" * 100)
        print(f"\nShowing {len(risk_items)} files with priority >= {min_priority}")
        print("Scope: " + ("All files" if include_tools else "Project files (excl. tools/ and Scripts/)"))
        if layers:
            print(f"Layers: {', '.join(layers)}")
        print("Risk formula:")
        print("  Untested: +importers*3 (max 30), +lines/100 (max 20)")
        print("  Hot files: +15")
        print("  Legacy issues: +violations*5, +mutations*3")
        print("  Tested: -5")

        untested = [i for i in risk_items if not i['tested']]
        if untested:
            print(f"\n🎯 {len(untested)} untested files found")
            high_untested = [i for i in untested if i['priority'] in ['HIGH', 'CRITICAL']]
            if high_untested:
                print(f"\n🔥 TOP PRIORITY - {len(high_untested)} HIGH/CRITICAL untested files:")
                for item in high_untested[:5]:
                    print(f"   - {item['path']}")
                    print(f"     Score: {item['risk_score']} | Importers: {item['importers']} | Lines: {item['lines']}")
        else:
            print("\n✅ All files are tested!")

    conn.close()
    return 0

# ----------------------------------------------------------------------
# RECON CORE – intent scoring
# ----------------------------------------------------------------------
def _get_top_files_for_intent(intent: str, db_path: Path, categories_path: Optional[str] = None,
                              max_files: int = 5, verbose: bool = False) -> List[Tuple[str, int, Dict]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    matched_clusters = []
    cluster_file_scores = defaultdict(int)

    if categories_path and Path(categories_path).exists():
        if _HAS_CONTEXT_ASSEMBLER:
            try:
                parser = IntentParser(categories_path)
                parsed = parser.parse(intent)
                matched_clusters = [c['name'] for c in parsed.get('matched_clusters', [])]
                for cluster_name in matched_clusters:
                    row = cur.execute("SELECT file_paths FROM clusters WHERE cluster_name = ?", (cluster_name,)).fetchone()
                    if row:
                        files = json.loads(row[0])
                        for f in files:
                            cluster_file_scores[f] += 2
                if verbose:
                    print(f"   Matched clusters: {', '.join(matched_clusters)}", file=sys.stderr)
            except Exception as e:
                if verbose:
                    print(f"   Cluster matching failed: {e}", file=sys.stderr)
        else:
            if verbose:
                print("   context_assembler not available, skipping cluster matching.", file=sys.stderr)
    else:
        if verbose:
            print("   No categories file, using pure vocabulary matching.", file=sys.stderr)

    intent_words = [w for w in intent.lower().split() if len(w) >= MIN_CONCEPT_LENGTH]
    concept_scores = defaultdict(int)
    for word in intent_words:
        rows = cur.execute("SELECT file_path FROM concepts WHERE concept = ?", (word,)).fetchall()
        for row in rows:
            concept_scores[row[0]] += 1

    combined_scores = defaultdict(int)
    for f, score in cluster_file_scores.items():
        combined_scores[f] += score
    for f, score in concept_scores.items():
        combined_scores[f] += score

    if not combined_scores:
        conn.close()
        return []

    top_files = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:max_files]
    result = []
    for file_path, score in top_files:
        row = cur.execute("SELECT data FROM files WHERE path = ?", (file_path,)).fetchone()
        if row:
            file_data = json.loads(row[0])
            file_data['relevance_score'] = score
            result.append((file_path, score, file_data))
    conn.close()
    return result

# ----------------------------------------------------------------------
# RECON MODE (intent‑driven report, no truncation)
# ----------------------------------------------------------------------
def run_recon(intent: str, db_path: str, categories_path: Optional[str] = None,
              max_files: int = 5, output_format: str = 'text', verbose: bool = False):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1

    top_files = _get_top_files_for_intent(intent, db_path, categories_path, max_files, verbose)
    if not top_files:
        print(f"⚠️  No files matched intent '{intent}'. Try broader terms.", file=sys.stderr)
        return 1

    result = {
        'intent': intent,
        'matched_clusters': [],
        'files': [data for _, _, data in top_files]
    }
    result['files'].sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

    if output_format == 'json':
        print(json.dumps(result, indent=2, default=str))
    else:
        print(generate_text_report(result))
    return 0

# ----------------------------------------------------------------------
# REPORT FORMATTING – NO TRUNCATION
# ----------------------------------------------------------------------
def generate_text_report(analysis: Dict[str, Any]) -> str:
    """Produce the ASCII‑art console report – NO TRUNCATION, EVERYTHING SHOWN."""
    lines = []
    lines.append("=" * 80)
    lines.append(f'RECON REPORT: "{analysis["intent"]}"')
    lines.append("=" * 80)
    lines.append("")

    lines.append(f"TERRITORY ({len(analysis['files'])} files mapped):")
    for f in analysis['files']:
        role = f.get('role', 'Unknown')
        path = f.get('path', 'unknown')
        lines.append(f"  {role}: {path}")
    lines.append("")

    lines.append("BOUNDARY FLAGS:")
    for f in analysis['files']:
        if f.get('is_hot'):
            if f.get('phase_violations'):
                line = f['phase_violations'][0]['line'] if f['phase_violations'] else '?'
                lines.append(f"  ⚠️  HOT ZONE: {f['path']} has phase violations (line {line})")
            elif f.get('mutations'):
                lines.append(f"  ⚠️  HOT ZONE: Direct state mutation in {f['path']}")
        else:
            lines.append(f"  ✅ SAFE ZONE: {f['path']} clean {f['role'].lower()} pattern")
    lines.append("")

    lines.append("INTERFACES (signatures only):")
    for f in analysis['files']:
        lines.append(f"  {f['path']}:")
        for cls in f.get('classes', []):
            lines.append(f"    class {cls['name']}:")
            for meth in cls.get('methods', []):
                args = ', '.join(meth.get('args', []))
                ret = f" -> {meth['returns']}" if meth.get('returns') else ''
                lines.append(f"      def {meth['name']}({args}){ret}")
            if cls.get('read_only_methods'):
                ro_list = ', '.join(cls['read_only_methods'])
                lines.append(f"      [read-only: {ro_list}]")
        for func in f.get('functions', []):
            args = ', '.join(func.get('args', []))
            ret = f" -> {func['returns']}" if func.get('returns') else ''
            lines.append(f"    def {func['name']}({args}){ret}")
        imported_by = f.get('imported_by', [])
        if imported_by:
            full_list = ', '.join(Path(p).name for p in imported_by)
            lines.append(f"    Exported to: {len(imported_by)} files ({full_list})")
        lines.append("")

    lines.append("CALL GRAPH (simplified):")
    edges = set()
    for f in analysis['files']:
        for imp in f.get('imports', []):
            if isinstance(imp, dict):
                mods = []
                if imp.get('type') == 'import':
                    mods = [n['name'].split('.')[0] for n in imp.get('names', [])]
                elif imp.get('module'):
                    mods = [imp['module'].split('.')[0]]
                for mod in mods:
                    for other in analysis['files']:
                        if Path(other['path']).stem == mod:
                            edges.add(f"{f['path']} → {other['path']}")
    for edge in sorted(edges):
        lines.append(f"  {edge}")
    for f in analysis['files']:
        for mut in f.get('mutations', []):
            lines.append(f"  {f['path']}:{mut['line']} → {mut['call']} (state mutation)")
    lines.append("")

    lines.append("SAFE MODIFICATION ZONES:")
    safe_count = 0
    for f in analysis['files']:
        if not f.get('is_hot'):
            ro_methods = []
            for cls in f.get('classes', []):
                ro_methods.extend(cls.get('read_only_methods', []))
            if ro_methods:
                all_ro = ', '.join(ro_methods)
                lines.append(f"  • Add logic in {all_ro} (read‑only)")
                safe_count += 1
    if safe_count == 0:
        lines.append("  • No clear safe zones – review hot files first.")
    lines.append("")

    lines.append("REQUIRES ARCHITECTURAL REVIEW:")
    for f in analysis['files']:
        if f.get('is_hot') and f.get('role') == 'Core':
            if f.get('mutations'):
                lines.append(f"  • {f['path']} directly mutates state – consider proposal pattern")
            else:
                lines.append(f"  • {f['path']} has phase violations – review boundaries")
    lines.append("")

    lines.append("RECOMMENDED CONTEXT FOR DEEP ANALYSIS:")
    for f in analysis['files']:
        if f.get('is_hot'):
            lines.append(f"  Full code: {f['path']} (lines with issues)")
        else:
            lines.append(f"  Interfaces only: {f['path']}")
    lines.append("=" * 80)
    return '\n'.join(lines)

# ----------------------------------------------------------------------
# REPORT MODES (pre‑canned, no truncation)
# ----------------------------------------------------------------------
def report_hot(db_path: str, limit: int, output_format: str):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, data FROM files WHERE is_hot = 1 ORDER BY line_count DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    if output_format == 'json':
        output = []
        for row in rows:
            data = json.loads(row['data'])
            output.append({
                'path': row['path'],
                'phase_violations': data.get('phase_violations', []),
                'mutations': data.get('mutations', [])
            })
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n🔥 HOT FILES ({len(rows)} found):")
        print("─" * 80)
        for i, row in enumerate(rows, 1):
            data = json.loads(row['data'])
            print(f"{i}. {row['path']}")
            for v in data.get('phase_violations', []):
                print(f"   ⚠️  Phase violation (line {v.get('line', '?')}): {v.get('pattern', 'unknown')}")
            for m in data.get('mutations', []):
                print(f"   💉 Mutation: {m.get('call', '?')} (line {m.get('line', '?')})")
        print()
    return 0

def report_mutations(db_path: str, limit: int, output_format: str):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, data FROM files WHERE json_extract(data, '$.mutations') != '[]' LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    if output_format == 'json':
        output = []
        for row in rows:
            data = json.loads(row['data'])
            output.append({
                'path': row['path'],
                'mutations': data.get('mutations', [])
            })
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n💉 DIRECT STATE MUTATIONS ({len(rows)} files):")
        print("─" * 80)
        for i, row in enumerate(rows, 1):
            data = json.loads(row['data'])
            print(f"{i}. {row['path']}")
            for m in data.get('mutations', []):
                print(f"   → {m.get('call', '?')} (line {m.get('line', '?')})")
        print()
    return 0

def report_largest(db_path: str, limit: int, output_format: str):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, line_count FROM files ORDER BY line_count DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    if output_format == 'json':
        output = [{'path': r[0], 'lines': r[1]} for r in rows]
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n📏 LARGEST FILES (top {limit}):")
        print("─" * 80)
        for i, row in enumerate(rows, 1):
            print(f"{i}. {row[0]:<60} ({row[1]} lines)")
        print()
    return 0

def report_concepts(db_path: str, limit: int, output_format: str):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT concept, COUNT(*) as freq FROM concepts GROUP BY concept ORDER BY freq DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    if output_format == 'json':
        output = [{'concept': r[0], 'frequency': r[1]} for r in rows]
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n🧠 TOP CONCEPTS (top {limit}):")
        print("─" * 80)
        for i, (concept, freq) in enumerate(rows, 1):
            print(f"{i}. {concept:<20} ({freq} files)")
        print()
    return 0

def report_exporters(db_path: str, limit: int, output_format: str):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, json_array_length(json_extract(data, '$.imported_by')) as imp_count FROM files WHERE imp_count > 0 ORDER BY imp_count DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    if output_format == 'json':
        output = [{'path': r['path'], 'importers': r['imp_count']} for r in rows]
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n📤 TOP EXPORTERS (most imported):")
        print("─" * 80)
        for i, row in enumerate(rows, 1):
            print(f"{i}. {row['path']:<60} ({row['imp_count']} importers)")
        print()
    return 0

def report_summary(db_path: str, output_format: str):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    file_count = cur.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    total_lines = cur.execute("SELECT SUM(line_count) FROM files").fetchone()[0] or 0
    hot_count = cur.execute("SELECT COUNT(*) FROM files WHERE is_hot = 1").fetchone()[0]
    mutation_count = cur.execute("SELECT COUNT(*) FROM files WHERE json_extract(data, '$.mutations') != '[]'").fetchone()[0]
    concept_count = cur.execute("SELECT COUNT(DISTINCT concept) FROM concepts").fetchone()[0]
    cluster_count = cur.execute("SELECT COUNT(*) FROM clusters").fetchone()[0]
    conn.close()
    if output_format == 'json':
        output = {
            'python_files': file_count,
            'total_lines': total_lines,
            'hot_files': hot_count,
            'mutation_files': mutation_count,
            'unique_concepts': concept_count,
            'clusters': cluster_count
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n📊 PROJECT SUMMARY:")
        print("─" * 80)
        print(f"📁 Python files:       {file_count}")
        print(f"📏 Total lines:        {total_lines:,}")
        print(f"🔥 Hot files:          {hot_count}")
        print(f"💉 Mutation files:     {mutation_count}")
        print(f"🧠 Unique concepts:    {concept_count}")
        print(f"🏷️  Clusters:          {cluster_count} (from categories)")
        print()
    return 0

# ----------------------------------------------------------------------
# ASK MODE – Interactive menu + natural language
# ----------------------------------------------------------------------
def ask_mode(db_path: str, question: Optional[str] = None):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    if question:
        answer = answer_question(db_path, question)
        print(answer)
        return 0

    print("🧠 Architecture Reconnaissance – Ask Mode")
    print("────────────────────────────────────────")
    print("Select a question by number, or type your own.\n")

    while True:
        print("\n" + "─" * 60)
        print(" 1. 🔥 What files are hot? (violations / mutations)")
        print(" 2. 💉 Which files mutate state directly?")
        print(" 3. 📏 What are the largest files?")
        print(" 4. 📤 What are the most imported files?")
        print(" 5. 📊 Show project summary")
        print(" 6. 🔎 Show me files related to a feature (e.g., 'movement')")
        print(" 7. 🛠️  How do I fix architectural violations?")
        print(" 8. 📁 Who imports a specific file?")
        print(" 0. ❌ Exit")
        print("─" * 60)

        choice = input("Your choice (0-8 or type a question): ").strip()

        if choice == '0' or choice.lower() in ('quit', 'exit', 'bye'):
            print("Bye!")
            break

        if choice == '1':
            print(_answer_hot(db_path))
        elif choice == '2':
            print(_answer_mutations(db_path))
        elif choice == '3':
            print(_answer_largest(db_path))
        elif choice == '4':
            print(_answer_exporters(db_path))
        elif choice == '5':
            print(_answer_summary(db_path))
        elif choice == '6':
            feature = input("Enter feature name (e.g., 'movement'): ").strip()
            if feature:
                run_recon(feature, str(db_path), max_files=5, output_format='text', verbose=False)
        elif choice == '7':
            print(_answer_how_to_fix())
        elif choice == '8':
            target = input("Enter filename (e.g., 'movement_service.py'): ").strip()
            if target:
                print(_answer_importers_of(db_path, target))
        else:
            answer = answer_question(db_path, choice)
            print(answer)
    return 0

def answer_question(db_path: Path, question: str) -> str:
    q = question.lower()
    if re.search(r'(what|show|list).*(hot|violation|phase|🔥)', q) or re.search(r'(hot|violation|phase).*(files?)', q):
        return _answer_hot(db_path)
    if re.search(r'(what|show|list).*(mutations?|state change|💉)', q) or re.search(r'(mutations?|state change).*(files?)', q):
        return _answer_mutations(db_path)
    if re.search(r'(what|show|list).*(largest|biggest|size|lines?|📏)', q) or re.search(r'(largest|biggest).*(files?)', q):
        return _answer_largest(db_path)
    if re.search(r'(what|show|list).*(most imported|exporters|dependencies?|📤)', q) or re.search(r'(who|what).*(depends on|imports|used by)', q):
        return _answer_exporters(db_path)
    file_match = re.search(r'(depends on|imports|used by)\s+([\w/\\]+\.py)', q)
    if file_match:
        target = file_match.group(2).strip()
        return _answer_importers_of(db_path, target)
    if re.search(r'how (do|can|to) fix', q) or re.search(r'fix (phase|violation|mutation)', q):
        return _answer_how_to_fix()
    if re.search(r'(what|show|summary|stats?|overview|📊)', q) and not re.search(r'(hot|mutation|largest)', q):
        return _answer_summary(db_path)
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        run_recon(question, str(db_path), max_files=5, output_format='text', verbose=False)
    return f.getvalue()

def _answer_hot(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, data FROM files WHERE is_hot = 1 ORDER BY line_count DESC"
    ).fetchall()
    conn.close()
    if not rows:
        return "✅ No hot files found. Architecture is clean!"
    lines = ["🔥 Hot files:"]
    for row in rows:
        data = json.loads(row['data'])
        desc = []
        for v in data.get('phase_violations', []):
            desc.append(f"phase violation (line {v.get('line', '?')})")
        for m in data.get('mutations', []):
            desc.append(f"mutation (line {m.get('line', '?')})")
        lines.append(f"  • {row['path']} – {', '.join(desc)}")
    return "\n".join(lines)

def _answer_mutations(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, data FROM files WHERE json_extract(data, '$.mutations') != '[]'"
    ).fetchall()
    conn.close()
    if not rows:
        return "✅ No direct state mutations found."
    lines = ["💉 Direct state mutations:"]
    for row in rows:
        data = json.loads(row['data'])
        for m in data.get('mutations', []):
            lines.append(f"  • {row['path']}:{m.get('line', '?')} → {m.get('call', '?')}")
    return "\n".join(lines)

def _answer_largest(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, line_count FROM files ORDER BY line_count DESC LIMIT 10"
    ).fetchall()
    conn.close()
    lines = ["📏 Largest files (by line count):"]
    for i, (path, lines_count) in enumerate(rows, 1):
        lines.append(f"  {i}. {path} ({lines_count} lines)")
    return "\n".join(lines)

def _answer_exporters(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, json_array_length(json_extract(data, '$.imported_by')) as imp_count FROM files WHERE imp_count > 0 ORDER BY imp_count DESC LIMIT 10"
    ).fetchall()
    conn.close()
    if not rows:
        return "ℹ️ No import relationships found."
    lines = ["📤 Most imported files:"]
    for i, row in enumerate(rows, 1):
        lines.append(f"  {i}. {row['path']} ({row['imp_count']} importers)")
    return "\n".join(lines)

def _answer_importers_of(db_path: Path, target_file: str) -> str:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    row = cur.execute("SELECT data FROM files WHERE path LIKE ?", (f"%{target_file}",)).fetchone()
    if not row:
        return f"⚠️  File '{target_file}' not found in scout DB."
    data = json.loads(row[0])
    importers = data.get('imported_by', [])
    if not importers:
        return f"ℹ️  No files import '{target_file}'."
    lines = [f"📤 Files that import {target_file}:"]
    for imp in importers:
        lines.append(f"  • {imp}")
    return "\n".join(lines)

def _answer_how_to_fix() -> str:
    return """🛠️  To fix architectural violations:

Phase violations:
  • Move direct AI calls to DMChatAI boundary.
  • Never skip, reverse, or combine adjacent phases.
  • See AI Contract: AI requests actions, does not own or mutate state.

State mutations:
  • Replace direct SessionSystem.update() calls with proposal pattern via GameEngine.
  • Move mutation logic to appropriate Core service.
  • Keep AI‑Facing files read‑only.

Run `arch_recon.py --hot` to see all violations, then inspect each file."""

def _answer_summary(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    file_count = cur.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    total_lines = cur.execute("SELECT SUM(line_count) FROM files").fetchone()[0] or 0
    hot_count = cur.execute("SELECT COUNT(*) FROM files WHERE is_hot = 1").fetchone()[0]
    mutation_count = cur.execute("SELECT COUNT(*) FROM files WHERE json_extract(data, '$.mutations') != '[]'").fetchone()[0]
    concept_count = cur.execute("SELECT COUNT(DISTINCT concept) FROM concepts").fetchone()[0]
    cluster_count = cur.execute("SELECT COUNT(*) FROM clusters").fetchone()[0]
    conn.close()
    return f"""📊 PROJECT SUMMARY
────────────────
📁 Python files:       {file_count}
📏 Total lines:        {total_lines:,}
🔥 Hot files:          {hot_count}
💉 Mutation files:     {mutation_count}
🧠 Unique concepts:    {concept_count}
🏷️  Clusters:          {cluster_count}"""

# ----------------------------------------------------------------------
# CONTEXT PACKAGE GENERATION (tiered, with dynamic phase extraction)
# ----------------------------------------------------------------------
def generate_context_package(intent: str, db_path: Path, categories_path: Optional[str] = None,
                             max_files: int = 5, level: str = 'standard', verbose: bool = False):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1
    top_files = _get_top_files_for_intent(intent, db_path, categories_path, max_files, verbose)
    if not top_files:
        print(f"⚠️  No files matched intent '{intent}'.", file=sys.stderr)
        return 1
    project_root = Path(db_path).parent.parent
    rules = load_global_rules(project_root)

    summary_data = {}
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        report_summary(str(db_path), 'json')
    try:
        summary_data = json.loads(f.getvalue())
    except:
        summary_data = {"error": "Could not parse summary"}

    lines = []
    lines.append("=" * 80)
    lines.append(f"ARCHITECTURE RECONNAISSANCE – CONTEXT PACKAGE")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Intent: {intent}")
    lines.append(f"Context level: {level}")
    lines.append(f"Max files: {max_files}")
    lines.append("=" * 80)
    lines.append("")

    # Global rules
    lines.append("## GLOBAL ARCHITECTURAL RULES")
    if rules['ai_contract']:
        lines.append(clean_ascii(rules['ai_contract']))
    else:
        lines.append("### AI Contract")
        for rule in rules['ai_contract_rules']:
            lines.append(rule)
        lines.append("")
        lines.append("### Phase Sequence")
        lines.append(rules['phase_sequence'])
        lines.append("")
        lines.append("### Role Definitions")
        lines.append(rules['role_definitions'])
    if rules['playbook']:
        lines.append("")
        lines.append("### Development Playbook")
        lines.append(clean_ascii(rules['playbook']))
    lines.append("")

    # Dynamic phase model
    lines.append("## PHASE MODEL (from engine/phases.py)")
    phases_file = project_root / 'engine' / 'phases.py'
    if phases_file.exists():
        try:
            with open(phases_file, 'r', encoding='utf-8') as f:
                content = f.read()
            import ast
            module = ast.parse(content)
            docstring = ast.get_docstring(module)
            if docstring:
                lines.append(docstring.strip())
            phase_order = []
            for node in ast.walk(module):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == 'ALL_PHASES':
                            if isinstance(node.value, ast.List):
                                phase_order = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)]
                            break
            if phase_order:
                lines.append("**Phase sequence:** " + " → ".join(phase_order))
            else:
                lines.append("**Phase sequence:** Input → Interpretation → Authority → Mutation → Consequence → Persistence → View")
        except Exception as e:
            lines.append(f"*[Could not parse phases.py: {e}]*")
    else:
        lines.append("*[engine/phases.py not found – using fallback]*")
        lines.append("Input → Interpretation → Authority → Mutation → Consequence → Persistence → View")
    lines.append("")

    # Project health summary
    lines.append("## PROJECT HEALTH SUMMARY")
    if "error" not in summary_data:
        lines.append(f"- Python files: {summary_data.get('python_files', '?')}")
        lines.append(f"- Total lines: {summary_data.get('total_lines', 0):,}")
        lines.append(f"- Hot files: {summary_data.get('hot_files', '?')}")
        lines.append(f"- Mutation files: {summary_data.get('mutation_files', '?')}")
        lines.append(f"- Unique concepts: {summary_data.get('unique_concepts', '?')}")
        lines.append(f"- Clusters: {summary_data.get('clusters', '?')}")
    else:
        lines.append(f"- {summary_data.get('error')}")
    lines.append("")

    # Intent‑matched files
    lines.append(f"## INTENT-MATCHED FILES (top {len(top_files)})")
    for idx, (file_path, score, data) in enumerate(top_files, 1):
        lines.append("")
        lines.append("---")
        lines.append(f"### {idx}. `{file_path}` (score: {score})")
        lines.append(f"- **Role**: {data.get('role', 'Unknown')}")
        lines.append(f"- **Hot**: {'Yes' if data.get('is_hot') else 'No'}")
        lines.append(f"- **Line count**: {data.get('line_count', 0)}")
        lines.append(f"- **Phase violations**: {len(data.get('phase_violations', []))}")
        for v in data.get('phase_violations', []):
            lines.append(f"  - line {v.get('line', '?')}: {v.get('pattern', 'unknown')}")
        lines.append(f"- **Mutations**: {len(data.get('mutations', []))}")
        for m in data.get('mutations', []):
            lines.append(f"  - line {m.get('line', '?')}: {m.get('call', '?')}")
        lines.append(f"- **Read-only methods**: {', '.join(data.get('read_only_methods', [])) if data.get('read_only_methods') else 'None'}")
        lines.append(f"- **Importers**: {len(data.get('imported_by', []))} files")
        if data.get('imported_by'):
            lines.append(f"  - {', '.join(Path(p).name for p in data['imported_by'])}")
        lines.append(f"- **Imports**: {len(data.get('imports', []))} modules")

        lines.append("")
        lines.append("#### Interfaces")
        lines.append("```python")
        for cls in data.get('classes', []):
            lines.append(f"class {cls['name']}:")
            for meth in cls.get('methods', []):
                args = ', '.join(meth.get('args', []))
                ret = f" -> {meth['returns']}" if meth.get('returns') else ''
                lines.append(f"    def {meth['name']}({args}){ret}")
            if cls.get('read_only_methods'):
                lines.append(f"    # read-only: {', '.join(cls['read_only_methods'])}")
        for func in data.get('functions', []):
            args = ', '.join(func.get('args', []))
            ret = f" -> {func['returns']}" if func.get('returns') else ''
            lines.append(f"def {func['name']}({args}){ret}")
        lines.append("```")
        lines.append("")

        include_source = False
        if level == 'deep':
            include_source = True
        elif level == 'standard':
            if data.get('is_hot') or idx == 1:
                include_source = True
        if include_source:
            try:
                full_path = project_root / file_path
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                        source = f.read()
                    lines_limit = 500 if level == 'deep' else 200
                    source_lines = source.splitlines()
                    if len(source_lines) > lines_limit:
                        source = '\n'.join(source_lines[:lines_limit]) + f"\n... (truncated at {lines_limit} lines)"
                    lines.append("#### Source code")
                    lines.append("```python")
                    lines.append(source)
                    lines.append("```")
                    lines.append("")
            except Exception as e:
                lines.append(f"*[Error reading source: {e}]*")

    lines.append("## RIPPLE IMPACT")
    for file_path, score, data in top_files:
        importers = data.get('imported_by', [])
        if importers:
            lines.append(f"- **{Path(file_path).name}** is imported by {len(importers)} files:")
            lines.append(f"  - {', '.join(Path(p).name for p in importers[:5])}")
            if len(importers) > 5:
                lines.append(f"    ... and {len(importers)-5} more")
        else:
            lines.append(f"- **{Path(file_path).name}** has no direct importers.")
    lines.append("")

    lines.append("## CONCEPTUAL OVERLAP")
    intent_words = set(w for w in intent.lower().split() if len(w) >= MIN_CONCEPT_LENGTH)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    concept_counts = []
    for word in intent_words:
        count = cur.execute("SELECT COUNT(DISTINCT file_path) FROM concepts WHERE concept = ?", (word,)).fetchone()[0]
        if count > 0:
            concept_counts.append((word, count))
    conn.close()
    if concept_counts:
        lines.append("Concepts in your intent and their prevalence:")
        for word, count in sorted(concept_counts, key=lambda x: x[1], reverse=True):
            lines.append(f"- `{word}` appears in {count} files")
    else:
        lines.append("No strong concept overlap found.")
    lines.append("")

    if categories_path and Path(categories_path).exists():
        try:
            with open(categories_path, 'r') as f:
                cat_data = json.load(f)
            clusters = cat_data.get('clusters', [])
            matched_names = set()
            for word in intent_words:
                for cl in clusters:
                    if word in cl.get('concepts', []):
                        matched_names.add(cl['name'])
            if matched_names:
                lines.append("Related clusters (from discovered_categories.json):")
                for name in matched_names:
                    lines.append(f"- {name}")
        except:
            pass

    lines.append("=" * 80)
    print("\n".join(lines))
    return 0

# ----------------------------------------------------------------------
# CONSULT MODE – Context + AI Delivery
# ----------------------------------------------------------------------
def consult_mode(intent: str, db_path: Path, project_root: Optional[Path] = None,
                 categories_path: Optional[str] = None,
                 max_files: int = 5, level: str = 'standard',
                 target: str = 'auto',
                 save_session: bool = False,
                 keep_open: bool = False,
                 verbose: bool = False):
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root).resolve()
    context_output = io.StringIO()
    with contextlib.redirect_stdout(context_output):
        exit_code = generate_context_package(
            intent=intent,
            db_path=db_path,
            categories_path=categories_path,
            max_files=max_files,
            level=level,
            verbose=verbose
        )
    if exit_code != 0:
        return exit_code
    context_text = context_output.getvalue()

    import sys
    scripts_path = project_root / 'scripts'
    if not scripts_path.exists():
        print(f"❌ Scripts directory not found: {scripts_path}", file=sys.stderr)
        return 1
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    try:
        from context_manager import ContextManager
    except ImportError as e:
        print(f"❌ Could not import ContextManager from {scripts_path}: {e}", file=sys.stderr)
        return 1

    mgr = ContextManager(verbose=verbose)
    package = mgr.build_package(intent, target=target)
    package['formatted'] = context_text
    package['query'] = intent

    print("\n" + "="*80)
    print(f"📤 SENDING CONTEXT TO AI (target: {target})...")
    print("="*80)

    success = mgr.send(package, target=target, keep_open=keep_open)
    if not success:
        print("❌ Failed to send context to AI.", file=sys.stderr)
        return 1

    session_dir = mgr.session_dir
    import glob
    response_files = list(session_dir.glob("deepseek_response*.txt")) + \
                     list(session_dir.glob("local_response.txt"))
    if response_files:
        latest = max(response_files, key=lambda p: p.stat().st_mtime)
        response_text = latest.read_text(encoding='utf-8')
        print("\n" + "="*80)
        print("🤖 AI RESPONSE")
        print("="*80)
        print(response_text)
    else:
        print("⚠️  Could not locate AI response file.", file=sys.stderr)
        response_text = ""

    if save_session:
        import json
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_intent = intent.replace(' ', '_')[:20]
        session_file = mgr.session_dir / f"consult_{timestamp}_{safe_intent}.json"
        session_data = {
            "timestamp": datetime.now().isoformat(),
            "intent": intent,
            "context_level": level,
            "max_files": max_files,
            "target": target,
            "context": context_text,
            "ai_response": response_text,
            "model": "user-specified" if target != 'auto' else "auto-routed"
        }
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Full session saved: {session_file}")
    return 0

# ----------------------------------------------------------------------
# TEST GENERATION MODES
# ----------------------------------------------------------------------
def generate_test(intent: str, db_path: Path, categories_path: Optional[str] = None,
                  project_root: Optional[Path] = None, output_file: Optional[str] = None,
                  verbose: bool = False):
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root).resolve()
    context_output = io.StringIO()
    with contextlib.redirect_stdout(context_output):
        exit_code = generate_context_package(
            intent=intent,
            db_path=db_path,
            categories_path=categories_path,
            max_files=5,
            level='deep',
            verbose=verbose
        )
    if exit_code != 0:
        return exit_code
    context_text = context_output.getvalue()

    prompt = f"""You are a senior Python test engineer. Using the following architectural context, write a **pytest** test file for the feature: "{intent}".

**Requirements:**
- Use `unittest.mock` to mock **all external dependencies** (AI calls, database, file I/O, network).
- Do **not** call real Ollama, real database, or real game systems.
- Only test the **public interfaces** shown in the context.
- Include clear assertions and docstrings.
- The test should be self‑contained and run in <0.1s.

**Architectural context:**
```
{context_text}
```

Output **only** the Python code, no explanations, no markdown.
"""
    if not output_file:
        safe_intent = intent.replace(' ', '_').replace('/', '_')[:30]
        output_file = f"tests/test_{safe_intent}.py"
    output_path = Path(output_file).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    import sys
    scripts_path = project_root / 'scripts'
    if not scripts_path.exists():
        print(f"❌ Scripts directory not found: {scripts_path}", file=sys.stderr)
        return 1
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    try:
        from context_manager import ContextManager
    except ImportError as e:
        print(f"❌ Could not import ContextManager from {scripts_path}: {e}", file=sys.stderr)
        return 1
    mgr = ContextManager(verbose=verbose)
    package = mgr.build_package(intent, target='auto')
    package['formatted'] = prompt
    package['query'] = intent

    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        success = mgr.send(package, target='auto', keep_open=False)
    if not success:
        print("❌ Failed to get AI response.", file=sys.stderr)
        return 1

    # --- Read the response from the saved file (reliable) ---
    session_dir = mgr.session_dir
    import glob
    response_files = list(session_dir.glob("deepseek_response*.txt")) + \
                     list(session_dir.glob("local_response.txt"))
    if response_files:
        latest = max(response_files, key=lambda p: p.stat().st_mtime)
        response = latest.read_text(encoding='utf-8')
    else:
        print("⚠️  Could not locate AI response file.", file=sys.stderr)
        response = ""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(response)
    print(f"✅ Test written to {output_path}")
    return 0

def update_test(test_file: str, diff_range: str, db_path: Path, categories_path: Optional[str] = None,
                project_root: Optional[Path] = None, verbose: bool = False):
    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}", file=sys.stderr)
        return 1
    with open(test_file, 'r', encoding='utf-8') as f:
        existing_test = f.read()

    import subprocess
    cmd = ['git', 'diff', diff_range]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Git diff failed: {result.stderr}", file=sys.stderr)
        return 1
    diff_text = result.stdout

    prompt = f"""You are a senior Python test engineer. I have an existing pytest test file and a git diff of recent changes.

**Existing test:**
```python
{existing_test}
```

Git diff (changes that need to be reflected in the test):
```
{diff_text}
```

Please update the test to match the new code. Keep the same style, mocking strategy, and assertions. Output only the updated Python code, no explanations.
"""
    import sys
    scripts_path = project_root / 'scripts'
    if not scripts_path.exists():
        print(f"❌ Scripts directory not found: {scripts_path}", file=sys.stderr)
        return 1
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    try:
        from context_manager import ContextManager
    except ImportError as e:
        print(f"❌ Could not import ContextManager from {scripts_path}: {e}", file=sys.stderr)
        return 1
    mgr = ContextManager(verbose=verbose)
    package = mgr.build_package("test update", target='auto')
    package['formatted'] = prompt
    package['query'] = "Update test"

    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        success = mgr.send(package, target='auto', keep_open=False)
    if not success:
        print("❌ Failed to get AI response.", file=sys.stderr)
        return 1

    # --- Read the response from the saved file (reliable) ---
    session_dir = mgr.session_dir
    import glob
    response_files = list(session_dir.glob("deepseek_response*.txt")) + \
                     list(session_dir.glob("local_response.txt"))
    if response_files:
        latest = max(response_files, key=lambda p: p.stat().st_mtime)
        response = latest.read_text(encoding='utf-8')
    else:
        print("⚠️  Could not locate AI response file.", file=sys.stderr)
        response = ""

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(response)
    print(f"✅ Test updated: {test_file}")
    return 0
# ----------------------------------------------------------------------
# CLI ENTRY POINT
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
    description='Architecture Reconnaissance – Scout + Recon + Ask + Context + Consult + Test',
    epilog='Examples:\n'
    ' arch_recon.py --scout\n'
    ' arch_recon.py "character creation"\n'
    ' arch_recon.py --context "movement" --context-level deep\n'
    ' arch_recon.py --consult "session persistence" --target deepseek\n'
    ' arch_recon.py --test "tool_system" --output tests/test_tool_system.py\n'
    ' arch_recon.py --test-update --test-file tests/test_character_builder.py --diff HEAD~1'
    )
    parser.add_argument('intent', nargs='?', help='Natural language intent (required for recon/context/consult/test)')
    parser.add_argument('--scout', action='store_true', help='Run scout (full project scan)')
    parser.add_argument('--db', default='ai_context/scout.db', help='SQLite DB path (default: ai_context/scout.db)')
    parser.add_argument('--categories', '-c', help='Path to discovered_categories.json (for intent parsing)')
    parser.add_argument('--project-root', '-r', default='.', help='Project root directory (for scout/consult/test)')
    parser.add_argument('--max-files', '-m', type=int, default=5, help='Max files in recon report or context')
    parser.add_argument('--format', '-f', choices=['text', 'json'], default='text', help='Output format (recon/report modes)')
    parser.add_argument('--force', action='store_true', help='Force rescan (with --scout)')
    parser.add_argument('--ignore-dirs', '-i', nargs='+',
    default=['__pycache__', 'venv', '.git', 'node_modules', 'Lib', 'docs', 'archive'],
    help='Directories to ignore (scout only)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    # Report modes
    parser.add_argument('--hot', action='store_true', help='List all hot files')
    parser.add_argument('--mutations', action='store_true', help='List files with direct state mutations')
    parser.add_argument('--largest', action='store_true', help='Show largest files by line count')
    parser.add_argument('--concepts', action='store_true', help='Show most frequent concepts')
    parser.add_argument('--exporters', action='store_true', help='Show most imported files')
    parser.add_argument('--summary', action='store_true', help='Show project summary statistics')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Limit for report modes')

    # ASK mode
    parser.add_argument('--ask', nargs='?', const='', help='Natural language question (if no argument, interactive)')

    # Context mode
    parser.add_argument('--context', action='store_true', help='Generate AI‑ready context package (requires intent)')
    parser.add_argument('--context-level', choices=['brief', 'standard', 'deep'], default='standard',
                        help='Detail level for context package (default: standard)')

    # Consult mode
    parser.add_argument('--consult', action='store_true', help='Generate context and send to AI (requires intent)')
    parser.add_argument('--target', choices=['auto', 'ollama', 'deepseek'], default='auto',
                        help='AI backend for consult mode (default: auto)')
    parser.add_argument('--save-session', action='store_true', help='Save the consultation session (context + response)')
    parser.add_argument('--keep-open', '-k', action='store_true', help='Leave DeepSeek browser open')

    # Test generation mode
    parser.add_argument('--test', action='store_true', help='Generate a pytest file for the given intent (requires --output or will auto‑name)')
    parser.add_argument('--test-update', action='store_true', help='Update an existing test based on git diff (requires --test-file and --diff)')
    parser.add_argument('--diff', help='Git revision range (e.g., HEAD~1) for test update')
    parser.add_argument('--test-file', help='Path to existing test file to update')
    parser.add_argument('--output', '-o', help='Output file path for generated test (default: tests/test_<intent>.py)')

    parser.add_argument('--risk-heatmap', action='store_true', help='Show risk-ranked files')
    parser.add_argument('--min-priority', default='MEDIUM', choices=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'])
    parser.add_argument('--include-tools', action='store_true', 
                    help='Include tools/ and Scripts/ folders in analysis (default: excluded)')
    parser.add_argument('--layer', action='append', choices=['world', 'dungeon_neo', 'engine', 'ai', 'tools', 'scripts'],
                    help='Filter by layer (can be used multiple times)')
    parser.add_argument('--no-prompt', action='store_true',
                    help='Skip interactive prompts (use existing DB or fail)')

    args = parser.parse_args()

    # Scout mode
    if args.scout:
        run_scout(
            project_root=args.project_root,
            db_path=args.db,
            force=args.force,
            ignore_dirs=args.ignore_dirs,
            verbose=args.verbose
        )
        return 0

    # Report modes
    if args.hot:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_hot(args.db, args.limit, args.format)
    if args.mutations:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_hot(args.db, args.limit, args.format)
    if args.largest:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_hot(args.db, args.limit, args.format)
    if args.concepts:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_hot(args.db, args.limit, args.format)
    if args.exporters:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_hot(args.db, args.limit, args.format)
    if args.summary:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_summary(args.db, args.format)

    # ASK mode
    if args.ask is not None:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        question = args.ask if args.ask else None
        return ask_mode(args.db, question)

    # Context mode
    if args.context:
        if not args.intent:
            print("❌ --context requires an intent (e.g., --context 'character creation')", file=sys.stderr)
            return 1
        if not args.categories:
            default_cat = Path(args.db).parent / 'discovered_categories.json'
            if default_cat.exists():
                args.categories = str(default_cat)
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        question = args.ask if args.ask else None
        return ask_mode(args.db, question)
        return generate_context_package(
            intent=args.intent,
            db_path=Path(args.db),
            categories_path=args.categories,
            max_files=args.max_files,
            level=args.context_level,
            verbose=args.verbose
        )

    # Consult mode
    if args.consult:
        if not args.intent:
            print("❌ --consult requires an intent (e.g., --consult 'character creation')", file=sys.stderr)
            return 1
        if not args.categories:
            default_cat = Path(args.db).parent / 'discovered_categories.json'
            if default_cat.exists():
                args.categories = str(default_cat)
        project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
        return consult_mode(
            intent=args.intent,
            db_path=Path(args.db),
            project_root=project_root,
            categories_path=args.categories,
            max_files=args.max_files,
            level=args.context_level,
            target=args.target,
            save_session=args.save_session,
            keep_open=args.keep_open,
            verbose=args.verbose
        )

    # Test generation mode
    if args.test:
        if not args.intent:
            print("❌ --test requires an intent (e.g., --test 'character creation')", file=sys.stderr)
            return 1
        if not args.categories:
            default_cat = Path(args.db).parent / 'discovered_categories.json'
            if default_cat.exists():
                args.categories = str(default_cat)
        project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
        return generate_test(
            intent=args.intent,
            db_path=Path(args.db),
            categories_path=args.categories,
            project_root=project_root,
            output_file=args.output,
            verbose=args.verbose
        )

    if args.risk_heatmap:
        if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                               project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                               verbose=args.verbose):
            return 1
        return report_risk_heatmap(args.db, args.min_priority, args.format,
                                   args.include_tools, args.layer)

    # Test update mode
    if args.test_update:
        if not args.test_file or not args.diff:
            print("❌ --test-update requires --test-file and --diff", file=sys.stderr)
            return 1
        if not args.categories:
            default_cat = Path(args.db).parent / 'discovered_categories.json'
            if default_cat.exists():
                args.categories = str(default_cat)
        project_root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
        return update_test(
            test_file=args.test_file,
            diff_range=args.diff,
            db_path=Path(args.db),
            categories_path=args.categories,
            project_root=project_root,
            verbose=args.verbose
        )

    if not ensure_db_fresh(Path(args.db), force=args.force, no_prompt=False,
                           project_root=args.project_root, ignore_dirs=args.ignore_dirs,
                           verbose=args.verbose):
        return 1

    # Recon mode (requires intent)
    if not args.intent:
        parser.print_help()
        return 1

    if not args.categories:
        default_cat = Path(args.db).parent / 'discovered_categories.json'
        if default_cat.exists():
            args.categories = str(default_cat)

    return run_recon(
        intent=args.intent,
        db_path=args.db,
        categories_path=args.categories,
        max_files=args.max_files,
        output_format=args.format,
        verbose=args.verbose
    )
if __name__ == '__main__':
    sys.exit(main())