#!/usr/bin/env python3
"""
arch_recon.py – Architecture Reconnaissance + Scout + Recon + Ask

Modes:
  --scout               : full project scan → SQLite DB
  <intent>              : instant intent‑driven report
  --hot / --mutations   : pre‑canned reports
  --ask                 : natural language questions (interactive or one‑shot)

No SQL. No flags to memorize. Just ask.
"""
import os
import ast
import sys
import re
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
from datetime import datetime

# ----------------------------------------------------------------------
# Project tool imports – with explicit fallback and error messages
# ----------------------------------------------------------------------
try:
    from tools.analysis.ast_analyzer import ASTAnalyzer
except ImportError:
    print("❌ Could not import ASTAnalyzer.", file=sys.stderr)
    print("   Ensure tools/analysis/ast_analyzer.py exists and PYTHONPATH includes project root.", file=sys.stderr)
    sys.exit(1)

try:
    from tools.analysis.context_assembler import IntentParser
    _HAS_CONTEXT_ASSEMBLER = True
except ImportError:
    _HAS_CONTEXT_ASSEMBLER = False
    # Not fatal – we fall back to vocabulary matching


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

# Minimum word length for vocabulary indexing
MIN_CONCEPT_LENGTH = 3


# ----------------------------------------------------------------------
# UTILITY FUNCTIONS
# ----------------------------------------------------------------------
def split_identifier(name: str) -> List[str]:
    """CamelCase + snake_case → words, lowercased, filtered."""
    if not name:
        return []
    # CamelCase: "MovementService" -> "Movement Service"
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    # snake_case: "validate_move" -> "validate move"
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
# AST ANALYSIS – SINGLE PASS (optimized)
# ----------------------------------------------------------------------
def analyze_file_for_scout(filepath: Path, project_root: Path, ignore_dirs: List[str]) -> Optional[Dict]:
    """One‑pass analysis of a single file: AST parse once, extract everything."""
    if should_ignore(filepath, ignore_dirs):
        return None

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError, Exception):
        return None

    # Use existing ASTAnalyzer methods where possible, but avoid re‑parsing
    analyzer = ASTAnalyzer(ignore_dirs=ignore_dirs)  # not used for parsing, just for helpers

    # Extract basic structure
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
            # Pre‑compute read‑only methods for this class
            read_only_methods = []
            for method in class_info.get('methods', []):
                # Find the actual FunctionDef node in the tree
                method_node = next((n for n in ast.walk(node) if isinstance(n, ast.FunctionDef) and n.name == method['name']), None)
                if method_node and not _method_has_mutation(method_node):
                    read_only_methods.append(f"{node.name}.{method['name']}")
            class_info['read_only_methods'] = read_only_methods[:5]
            file_info['classes'].append(class_info)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            file_info['functions'].append(analyzer.extract_function_info(node))

    # Detect state mutations (using same tree)
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

    # Role and hotness
    file_info['role'] = classify_role(file_info['path'])
    file_info['is_hot'] = bool(file_info.get('phase_violations') or mutations)

    return file_info


def _method_has_mutation(node: ast.FunctionDef) -> bool:
    """Check if a method body contains any state‑mutation call."""
    for subnode in ast.walk(node):
        if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Attribute):
            if isinstance(subnode.func.value, ast.Name):
                obj = subnode.func.value.id
                method = subnode.func.attr
                if obj in STATE_HOLDERS and method in MUTATING_METHODS:
                    return True
    return False


def build_import_map(project_root: Path, ignore_dirs: List[str]) -> Dict[str, List[str]]:
    """Scan all .py files, build module → list of importing files (respects ignore)."""
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
    """Scan entire project, store enriched data in SQLite."""
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
    # Filter ignored directories
    py_files = [f for f in all_py_files if not should_ignore(f, ignore_dirs)]
    print(f"   Found {len(py_files)} Python files (ignored {len(all_py_files) - len(py_files)}).")

    # Build import map once
    if verbose:
        print("   Building import map...")
    import_map = build_import_map(project_root, ignore_dirs)

    # Process each file
    file_infos = []
    vocabulary = defaultdict(list)  # concept → list of file paths

    for i, py_file in enumerate(py_files):
        if verbose and (i % 50 == 0):
            print(f"   Processing file {i+1}/{len(py_files)}...")
        file_info = analyze_file_for_scout(py_file, project_root, ignore_dirs)
        if not file_info:
            continue

        # Add reverse import info
        module_name = py_file.stem
        file_info['imported_by'] = import_map.get(module_name, [])

        file_infos.append(file_info)

        # Build vocabulary from class/function names
        for cls in file_info.get('classes', []):
            for word in split_identifier(cls['name']):
                vocabulary[word].append(file_info['path'])
        for func in file_info.get('functions', []):
            for word in split_identifier(func['name']):
                vocabulary[word].append(file_info['path'])

    print(f"   Analyzed {len(file_infos)} files.")

    # SQLite setup
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

    # Insert meta
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("scout_timestamp", datetime.now().isoformat()))
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("project_root", str(project_root)))
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                ("file_count", str(len(file_infos))))

    # Insert files
    for file_info in file_infos:
        # Strip source to save space – not needed for recon
        file_info_copy = file_info.copy()
        file_info_copy.pop('source', None)  # if ASTAnalyzer includes it
        # Also strip any large fields you don't need
        for violation in file_info_copy.get('phase_violations', []):
            violation.pop('text', None)  # keep line numbers, but not full line text

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

    # Insert vocabulary
    for word, paths in vocabulary.items():
        # Dedup paths per word
        for path in set(paths):
            cur.execute("INSERT OR IGNORE INTO concepts (concept, file_path) VALUES (?, ?)", (word, path))

    # Load clusters from discovered_categories.json (if exists)
    cat_file = project_root / 'ai_context/discovered_categories.json'
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


# ----------------------------------------------------------------------
# RECON MODE (intent‑driven)
# ----------------------------------------------------------------------
def run_recon(intent: str, db_path: str, categories_path: Optional[str] = None,
              max_files: int = 5, output_format: str = 'text', verbose: bool = False):
    """Load scout DB, find files matching intent, generate report."""
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}", file=sys.stderr)
        print("   Run `--scout` first.", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Try cluster‑based matching if categories file provided and exists
    matched_clusters = []
    cluster_file_scores = defaultdict(int)  # file -> +2 per cluster

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

    # 2. Vocabulary matching
    intent_words = [w for w in intent.lower().split() if len(w) >= MIN_CONCEPT_LENGTH]
    concept_scores = defaultdict(int)

    for word in intent_words:
        rows = cur.execute("SELECT file_path FROM concepts WHERE concept = ?", (word,)).fetchall()
        for row in rows:
            concept_scores[row[0]] += 1

    # 3. Combine scores
    combined_scores = defaultdict(int)
    for f, score in cluster_file_scores.items():
        combined_scores[f] += score
    for f, score in concept_scores.items():
        combined_scores[f] += score

    if not combined_scores:
        print(f"⚠️  No files matched intent '{intent}'. Try broader terms.", file=sys.stderr)
        return 1

    # 4. Select top N files
    top_files = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:max_files]

    # 5. Load full file data
    result = {
        'intent': intent,
        'matched_clusters': matched_clusters,
        'files': []
    }
    for file_path, score in top_files:
        row = cur.execute("SELECT data FROM files WHERE path = ?", (file_path,)).fetchone()
        if row:
            file_data = json.loads(row[0])
            file_data['relevance_score'] = score
            result['files'].append(file_data)

    conn.close()

    # 6. Sort files by score (descending)
    result['files'].sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

    if output_format == 'json':
        print(json.dumps(result, indent=2, default=str))
    else:
        print(generate_text_report(result))

    return 0


# ----------------------------------------------------------------------
# REPORT MODES (pre‑canned)
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
            for v in data.get('phase_violations', [])[:2]:
                print(f"   ⚠️  Phase violation (line {v.get('line', '?')}): {v.get('pattern', 'unknown')}")
            for m in data.get('mutations', [])[:2]:
                print(f"   💉 Mutation: {m.get('call', '?')} (line {m.get('line', '?')})")
            if len(data.get('phase_violations', [])) > 2 or len(data.get('mutations', [])) > 2:
                print(f"   ... and more")
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
            for m in data.get('mutations', [])[:3]:
                print(f"   → {m.get('call', '?')} (line {m.get('line', '?')})")
            if len(data.get('mutations', [])) > 3:
                print(f"   ... and {len(data['mutations'])-3} more")
        print()
    return 0


def report_largest(db_path: str, limit: int, output_format: str):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    rows = cur.execute(
        "SELECT path, line_count FROM files ORDER BY line_count DESC LIMIT ?",
        (limit,)
    ).fetchall()

    conn.close()

    if output_format == 'json':
        output = [{'path': r['path'], 'lines': r['line_count']} for r in rows]
        print(json.dumps(output, indent=2, default=str))
    else:
        print(f"\n📏 LARGEST FILES (top {limit}):")
        print("─" * 80)
        for i, row in enumerate(rows, 1):
            print(f"{i}. {row['path']:<60} ({row['line_count']} lines)")
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
# ASK MODE – Natural Language Questions
# ----------------------------------------------------------------------
def ask_mode(db_path: str, question: Optional[str] = None):
    """Interactive menu + free‑form questions."""
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}\n   Run `--scout` first.", file=sys.stderr)
        return 1

    if question:
        # One‑shot question (existing behaviour)
        answer = answer_question(db_path, question)
        print(answer)
        return 0

    # Interactive session with menu
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

        # Numbered menu items
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
            # Treat as free‑form question
            answer = answer_question(db_path, choice)
            print(answer)

    return 0


def answer_question(db_path: Path, question: str) -> str:
    """Classify question and return answer."""
    q = question.lower()

    # ---- PATTERN 1: Hot files ----
    if re.search(r'(what|show|list).*(hot|violation|phase|🔥)', q) or \
       re.search(r'(hot|violation|phase).*(files?)', q):
        return _answer_hot(db_path)

    # ---- PATTERN 2: State mutations ----
    if re.search(r'(what|show|list).*(mutations?|state change|💉)', q) or \
       re.search(r'(mutations?|state change).*(files?)', q):
        return _answer_mutations(db_path)

    # ---- PATTERN 3: Largest files ----
    if re.search(r'(what|show|list).*(largest|biggest|size|lines?|📏)', q) or \
       re.search(r'(largest|biggest).*(files?)', q):
        return _answer_largest(db_path)

    # ---- PATTERN 4: Most imported / exporters ----
    if re.search(r'(what|show|list).*(most imported|exporters|dependencies?|📤)', q) or \
       re.search(r'(who|what).*(depends on|imports|used by)', q):
        return _answer_exporters(db_path)

    # ---- PATTERN 5: Dependencies of a specific file ----
    file_match = re.search(r'(depends on|imports|used by)\s+([\w/\\]+\.py)', q)
    if file_match:
        target = file_match.group(2).strip()
        return _answer_importers_of(db_path, target)

    # ---- PATTERN 6: How to fix ----
    if re.search(r'how (do|can|to) fix', q) or re.search(r'fix (phase|violation|mutation)', q):
        return _answer_how_to_fix()

    # ---- PATTERN 7: Project summary ----
    if re.search(r'(what|show|summary|stats?|overview|📊)', q) and \
       not re.search(r'(hot|mutation|largest)', q):  # avoid overlap
        return _answer_summary(db_path)

    # ---- FALLBACK: Treat as intent ----
    # We'll run recon with max_files=5 and return the text report
    # Capture stdout to return as string
    import io
    from contextlib import redirect_stdout

    f = io.StringIO()
    with redirect_stdout(f):
        run_recon(question, str(db_path), max_files=5, output_format='text', verbose=False)
    return f.getvalue()


# ---- Answer generators (text only) ----
def _answer_hot(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, data FROM files WHERE is_hot = 1 ORDER BY line_count DESC LIMIT 10"
    ).fetchall()
    conn.close()

    if not rows:
        return "✅ No hot files found. Architecture is clean!"

    lines = ["🔥 Hot files:"]
    for row in rows[:5]:  # top 5
        data = json.loads(row['data'])
        desc = []
        if data.get('phase_violations'):
            desc.append(f"phase violation (line {data['phase_violations'][0].get('line', '?')})")
        if data.get('mutations'):
            desc.append(f"mutation (line {data['mutations'][0].get('line', '?')})")
        lines.append(f"  • {row['path']} – {', '.join(desc)}")
    if len(rows) > 5:
        lines.append(f"  ... and {len(rows)-5} more")
    return "\n".join(lines)


def _answer_mutations(db_path: Path) -> str:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT path, data FROM files WHERE json_extract(data, '$.mutations') != '[]' LIMIT 10"
    ).fetchall()
    conn.close()

    if not rows:
        return "✅ No direct state mutations found."

    lines = ["💉 Direct state mutations:"]
    for row in rows[:5]:
        data = json.loads(row['data'])
        for m in data.get('mutations', [])[:2]:
            lines.append(f"  • {row['path']}:{m.get('line', '?')} → {m.get('call', '?')}")
    if len(rows) > 5:
        lines.append(f"  ... and {len(rows)-5} more files")
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

    # Try exact match first
    row = cur.execute("SELECT data FROM files WHERE path LIKE ?", (f"%{target_file}",)).fetchone()
    if not row:
        return f"⚠️  File '{target_file}' not found in scout DB."

    data = json.loads(row[0])
    importers = data.get('imported_by', [])

    if not importers:
        return f"ℹ️  No files import '{target_file}'."

    lines = [f"📤 Files that import {target_file}:"]
    for imp in importers[:10]:
        lines.append(f"  • {imp}")
    if len(importers) > 10:
        lines.append(f"  ... and {len(importers)-10} more")
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
# REPORT FORMATTING (for intent mode)
# ----------------------------------------------------------------------
def generate_text_report(analysis: Dict[str, Any]) -> str:
    """Produce the ASCII‑art console report for intent mode."""
    lines = []
    lines.append("=" * 80)
    lines.append(f'RECON REPORT: "{analysis["intent"]}"')
    lines.append("=" * 80)
    lines.append("")

    # TERRITORY
    lines.append(f"TERRITORY ({len(analysis['files'])} files mapped):")
    for f in analysis['files']:
        role = f.get('role', 'Unknown')
        path = f.get('path', 'unknown')
        lines.append(f"  {role}: {path}")
    lines.append("")

    # BOUNDARY FLAGS
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

    # INTERFACES (signatures only)
    lines.append("INTERFACES (signatures only):")
    for f in analysis['files']:
        lines.append(f"  {f['path']}:")
        # classes
        for cls in f.get('classes', [])[:2]:
            lines.append(f"    class {cls['name']}:")
            for meth in cls.get('methods', [])[:3]:
                args = ', '.join(meth.get('args', []))
                ret = f" -> {meth['returns']}" if meth.get('returns') else ''
                lines.append(f"      def {meth['name']}({args}){ret}")
            if len(cls.get('methods', [])) > 3:
                lines.append(f"      [{len(cls['methods']) - 3} more methods...]")
            # show read‑only hints
            if cls.get('read_only_methods'):
                ro_sample = ', '.join(cls['read_only_methods'][:2])
                lines.append(f"      [read-only: {ro_sample}]")
        # top-level functions
        for func in f.get('functions', [])[:2]:
            args = ', '.join(func.get('args', []))
            ret = f" -> {func['returns']}" if func.get('returns') else ''
            lines.append(f"    def {func['name']}({args}){ret}")
        # export summary
        imported_by = f.get('imported_by', [])
        if imported_by:
            short = ', '.join(Path(p).name for p in imported_by[:3])
            lines.append(f"    Exported to: {len(imported_by)} files ({short}...)")
        lines.append("")

    # CALL GRAPH (simplified)
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
    # mutation edges
    for f in analysis['files']:
        for mut in f.get('mutations', []):
            lines.append(f"  {f['path']}:{mut['line']} → {mut['call']} (state mutation)")
    lines.append("")

    # SAFE MODIFICATION ZONES
    lines.append("SAFE MODIFICATION ZONES:")
    safe_count = 0
    for f in analysis['files']:
        if not f.get('is_hot'):
            # Collect read‑only methods from classes
            ro_methods = []
            for cls in f.get('classes', []):
                ro_methods.extend(cls.get('read_only_methods', []))
            if ro_methods:
                sample = ', '.join(ro_methods[:2])
                lines.append(f"  • Add logic in {sample} (read‑only)")
                safe_count += 1
    if safe_count == 0:
        lines.append("  • No clear safe zones – review hot files first.")
    lines.append("")

    # REQUIRES ARCHITECTURAL REVIEW
    lines.append("REQUIRES ARCHITECTURAL REVIEW:")
    for f in analysis['files']:
        if f.get('is_hot') and f.get('role') == 'Core':
            if f.get('mutations'):
                lines.append(f"  • {f['path']} directly mutates state – consider proposal pattern")
            else:
                lines.append(f"  • {f['path']} has phase violations – review boundaries")
    lines.append("")

    # RECOMMENDED CONTEXT
    lines.append("RECOMMENDED CONTEXT FOR DEEP ANALYSIS:")
    for f in analysis['files']:
        if f.get('is_hot'):
            lines.append(f"  Full code: {f['path']} (lines with issues)")
        else:
            lines.append(f"  Interfaces only: {f['path']}")
    lines.append("=" * 80)

    return '\n'.join(lines)


# ----------------------------------------------------------------------
# CLI ENTRY POINT
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Architecture Reconnaissance – Scout + Recon + Ask',
        epilog='Examples:\n'
               '  arch_recon.py --score                 # full scan → SQLite\n'
               '  arch_recon.py "movement authority"    # instant intent report\n'
               '  arch_recon.py --hot                   # list hot files\n'
               '  arch_recon.py --ask "what is hot"     # natural language question\n'
               '  arch_recon.py --ask                   # interactive session'
    )
    parser.add_argument('intent', nargs='?', help='Natural language intent (required for recon)')
    parser.add_argument('--scout', action='store_true', help='Run scout (full project scan)')
    parser.add_argument('--db', default='ai_context/scout.db', help='SQLite DB path (default: ai_context/scout.db)')
    parser.add_argument('--categories', '-c', help='Path to discovered_categories.json (for intent parsing)')
    parser.add_argument('--project-root', '-r', default='.', help='Project root directory (for scout)')
    parser.add_argument('--max-files', '-m', type=int, default=5, help='Max files in recon report')
    parser.add_argument('--format', '-f', choices=['text', 'json'], default='text', help='Output format')
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

    # Report modes (no intent needed)
    if args.hot:
        return report_hot(args.db, args.limit, args.format)
    if args.mutations:
        return report_mutations(args.db, args.limit, args.format)
    if args.largest:
        return report_largest(args.db, args.limit, args.format)
    if args.concepts:
        return report_concepts(args.db, args.limit, args.format)
    if args.exporters:
        return report_exporters(args.db, args.limit, args.format)
    if args.summary:
        return report_summary(args.db, args.format)

    # ASK mode
    if args.ask is not None:
        # args.ask is either empty string (interactive) or a question
        question = args.ask if args.ask else None
        return ask_mode(args.db, question)

    # Recon mode (requires intent)
    if not args.intent:
        parser.print_help()
        return 1

    # Default categories path: if not provided, look next to DB
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