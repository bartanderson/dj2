"""Report functions for arch_recon."""
import json
import sqlite3
from pathlib import Path
from typing import Optional, List

def report_hot(db_path: str, limit: int, output_format: str):
    db_path = Path(db_path)
    if not db_path.exists():
        print(f"❌ Scout DB not found: {db_path}")
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
        print(f"❌ Scout DB not found: {db_path}")
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
        print(f"❌ Scout DB not found: {db_path}")
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
        print(f"❌ Scout DB not found: {db_path}")
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
        print(f"❌ Scout DB not found: {db_path}")
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
        print(f"❌ Scout DB not found: {db_path}")
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