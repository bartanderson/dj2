#!/usr/bin/env python3
"""
tool_analyzer.py - Multi-source tool analysis
Combines: your descriptions, git history, import analysis, and file metadata
"""

import secrets
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import ast
import re
import os

IGNORE_PATTERNS = ['__pycache__', 'venv', '.git', 'node_modules', 'Lib', 'docs', 'archive']

def get_session_dir():
    """Return Path to session directory if env var is set, else None."""
    session_dir = os.environ.get('NATIVECLAW_SESSION_DIR')
    return Path(session_dir) if session_dir else None

def get_reports_dir():
    """Return path to persistent reports folder (create if needed)."""
    reports_dir = Path(__file__).parent.parent.parent / 'ai_context' / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir

def should_ignore(path):
    path_str = str(path).lower()
    return any(p in path_str for p in IGNORE_PATTERNS)

def main():
    inputs = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    # Determine which action to perform based on input keys
    if 'analysis_data' in inputs or 'analysis_data_file' in inputs:
        result = generate_report(inputs)
    else:
        result = analyze_ecosystem()
    print(json.dumps(result, indent=2, default=str))

# ============================================================================
# DATA SOURCES
# ============================================================================

def analyze_ecosystem():
    # Redirect debug output to stderr
    print("DEBUG: analyze_ecosystem started", file=sys.stderr)
    """Multi-source analysis of all tools."""
    project_root = Path(__file__).parent.parent.parent
    
    print("Scanning files...", file=sys.stderr)
    all_py_files = scan_python_files(project_root)
    print(f"Found {len(all_py_files)} files", file=sys.stderr)
    print("Getting git history...", file=sys.stderr)
    git_stats = {} # get_git_history(project_root, all_py_files)
    print("Analyzing imports...", file=sys.stderr)
    import_graph = analyze_imports(project_root, all_py_files)
    print("Getting descriptions...", file=sys.stderr)
    descriptions = get_known_descriptions()
    print("Combining data...", file=sys.stderr)    
    # Combine sources
    inventory = []
    for file_info in all_py_files:
        rel_path = file_info['path']
        inventory.append({
            'path': rel_path,
            'name': Path(rel_path).name,
            'folder': str(Path(rel_path).parent),
            'size': file_info['size'],
            'modified': file_info['modified'],
            'git': git_stats.get(rel_path, {'commits': 0, 'last_commit': None}),
            'imported_by': import_graph.get(rel_path, []),
            'imports': file_info['imports'],
            'description': descriptions.get(rel_path, descriptions.get(Path(rel_path).name, 'No description')),
            'has_tool_yaml': file_info['has_tool_yaml']
        })
    
    # Analysis
    print("Returning data...", file=sys.stderr)
    full_result = {
        'inventory': inventory,
        'summary': summarize_inventory(inventory),
        'hotspots': find_hotspots(inventory, import_graph),
        'orphans': find_orphans(inventory, import_graph),
        'duplicates': find_duplicates(inventory),
        'dependencies': import_graph,
        'recommendations': generate_recommendations(inventory, import_graph)
    }
    
    # --- NEW: if session directory exists, write to file and return path ---
    session_dir = get_session_dir()
    if session_dir:
        filename = f"ecosystem_data_{secrets.token_hex(4)}.json"
        file_path = session_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(full_result, f, indent=2, default=str)
        # Return relative path (for use in subsequent steps)
        cwd = Path.cwd()
        try:
            rel_path = file_path.relative_to(cwd)
        except ValueError:
            rel_path = file_path
        return {"data_file": str(rel_path)}
    else:
        # No session: return full result (original behavior)
        return full_result

def scan_python_files(root):
    files = []
    scan_dirs = ['tools', 'scripts']  # adjust as needed
    for scan_dir in scan_dirs:
        full_path = root / scan_dir
        if not full_path.is_dir():
            continue
        for py_file in full_path.rglob('*.py'):
            if should_ignore(py_file):
                continue
            try:
                rel_path = str(py_file.relative_to(root))
                stat = py_file.stat()
                # Parse imports
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    imports = extract_imports(content)
                except Exception as e:
                    print(f"Warning: Could not parse {py_file}: {e}", file=sys.stderr)
                    imports = []
                
                files.append({
                    'path': rel_path.replace('\\', '/'),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime),  # works if import is correct
                    'imports': imports,
                    'has_tool_yaml': (py_file.parent / 'tool.yaml').exists()
                })
            except Exception as e:
                print(f"Warning: Skipping {py_file} due to error: {e}", file=sys.stderr)
                continue
    return files

def extract_imports(content):
    """Extract import statements from Python code."""
    imports = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split('.')[0])
    except:
        # If parsing fails, use regex fallback
        imports = re.findall(r'^import (\w+)|^from (\w+) import', content, re.MULTILINE)
        imports = [i[0] or i[1] for i in imports if any(i)]
    
    return list(set(imports))

def get_git_history(root, files):
    """Get git commit history for each file."""
    stats = {}
    
    try:
        # Get last commit date for each file
        for file_info in files:
            path = file_info['path']
            result = subprocess.run(
                ['git', 'log', '-1', '--format=%ct', '--', path],
                cwd=root, capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                timestamp = int(result.stdout.strip())
                last_commit = datetime.fromtimestamp(timestamp)
            else:
                last_commit = None
            
            # Count commits
            result = subprocess.run(
                ['git', 'rev-list', '--count', 'HEAD', '--', path],
                cwd=root, capture_output=True, text=True
            )
            commits = int(result.stdout.strip()) if result.returncode == 0 else 0
            
            stats[path] = {
                'last_commit': last_commit,
                'commits': commits
            }
    except:
        pass
    
    return stats

def analyze_imports(root, files):
    """Build import graph (who imports whom)."""
    import_graph = {}
    
    # Build mapping from filename to path
    name_to_path = {}
    for f in files:
        name = Path(f['path']).stem
        if name not in name_to_path:
            name_to_path[name] = []
        name_to_path[name].append(f['path'])
    
    # For each file, find what imports it
    for importer in files:
        importer_path = importer['path']
        
        for imported_name in importer['imports']:
            if imported_name in name_to_path:
                for imported_path in name_to_path[imported_name]:
                    if imported_path != importer_path:
                        if imported_path not in import_graph:
                            import_graph[imported_path] = []
                        import_graph[imported_path].append(importer_path)
    
    return import_graph

def get_known_descriptions():
    """Your descriptions from the session (hardcoded but editable)."""
    return {
        # tools/ai_assistant/
        'tools/ai_assistant/context_builder.py': 'BridgeAgent for building context - Simplified version',
        'tools/ai_assistant/editing_commands.py': 'Flexible editing commands - Direct operations only (no backup)',
        'tools/ai_assistant/four_layer.py': 'Four-layer analysis - Uses ast_analyzer as engine',
        
        # tools/analysis/
        'tools/analysis/agent.py': 'Multi-turn ReAct agent for test generation',
        'tools/analysis/arch_recon.py': 'Architecture Reconnaissance + Scout + Recon + Ask + Context + Consult + Test',
        'tools/analysis/ast_analyzer.py': 'Core AST analysis engine for the project',
        'tools/analysis/clean_and_repopulate.py': 'Clean and repopulate dependent tables after scout scan (may be discarded)',
        'tools/analysis/context_assembler.py': 'Intent-driven file discovery using discovered categories',
        'tools/analysis/db_operations.py': 'Part of arch_recon.py',
        'tools/analysis/db_queries.py': 'Part of arch_recon.py',
        'tools/analysis/discover_categories.py': 'Discover hierarchical categories from code identifiers',
        'tools/analysis/dump_context.py': 'Dump full context for test generation',
        'tools/analysis/embedding_model.py': 'all-MiniLM-L6-v2 for text embeddings',
        'tools/analysis/extractors.py': 'Extract imports, dict access, method params',
        'tools/analysis/generate_test.py': 'Generate tests for intents using full context',
        'tools/guardrails/run.py': 'Real guardrails using AST analyzer',
        'tools/analysis/intent_matcher.py': 'Find files for intent using embeddings',
        'tools/analysis/phase_checker.py': 'Phase compliance checking',
        'tools/analysis/populate_imports.py': 'Populate imports table after scout scan',
        'tools/analysis/reporters.py': 'Part of arch_recon.py',
        'tools/analysis/scanner.py': 'Part of arch_recon.py',
        'tools/analysis/test_templates.py': 'Test patterns from existing tests',
        'tools/analysis/test_tools.py': 'Tools for test generation (for agent.py)',
        'tools/analysis/utils.py': 'module_to_file_path, split_identifier, classify_role, should_ignore',
        
        # tools/architecture/
        'tools/architecture/enhanced_architect.py': 'Enhanced Living Architect',
        
        # tools/bridge/
        'tools/bridge/bridge_controller.py': 'Bridge Controller - Uses React bridge for file upload',
        'tools/bridge/deepseek_bridge_react.py': 'React-aware version (backward compatible)',
        'tools/bridge/unified_core.py': 'Internal implementation for compatibility wrappers',
        
        # tools/utils/
        'tools/utils/format_ai_markdown.py': 'Early markdown formatter (not really used)',
        
        # Root files
        'ai.py': 'CLI main command',
        'run_game.py': 'Starts world and dungeon Flask apps',
        'world_app.py': 'Main Flask app for world map, character generation',
        'dungeon_neo_web_app.py': 'Dungeon generation/movement (run by run_game.py)',
        'run_analysis.py': 'Runs all code analysis tools',
        'create_tables.py': 'Original tables creation',
        
        # Scripts
        'scripts/context_manager.py': 'Load documents and files, prepare context for AI',
        'scripts/project_auditor.py': 'Consolidated dashboard with real analysis only',
        'scripts/simple_tool_tester.py': 'Simple, accurate tool tester with real arguments',
    }

# ============================================================================
# ANALYSIS
# ============================================================================

def summarize_inventory(inventory):
    """Basic summary statistics."""
    total = len(inventory)
    with_tool_yaml = sum(1 for f in inventory if f['has_tool_yaml'])
    
    by_folder = {}
    for f in inventory:
        folder = f['folder']
        if folder not in by_folder:
            by_folder[folder] = {'count': 0, 'files': []}
        by_folder[folder]['count'] += 1
        by_folder[folder]['files'].append(f['name'])
    
    return {
        'total_files': total,
        'files_with_tool_yaml': with_tool_yaml,
        'coverage_percent': (with_tool_yaml / total * 100) if total else 0,
        'by_folder': by_folder
    }

def find_hotspots(inventory, import_graph):
    """Find most important files (highly imported, frequently changed)."""
    hotspots = []
    
    for f in inventory:
        score = 0
        reasons = []
        
        # Imported by many
        import_count = len(import_graph.get(f['path'], []))
        if import_count > 2:
            score += import_count * 2
            reasons.append(f'imported by {import_count} files')
        
        # Recently changed
        if f['git']['last_commit']:
            days_ago = (datetime.now() - f['git']['last_commit']).days
            if days_ago < 30:
                score += 10
                reasons.append('changed recently')
        
        # Many commits
        if f['git']['commits'] > 10:
            score += f['git']['commits']
            reasons.append(f"{f['git']['commits']} commits")
        
        # Large file (likely complex)
        if f['size'] > 20000:
            score += 5
            reasons.append('large file')
        
        if score > 10:
            hotspots.append({
                'path': f['path'],
                'name': f['name'],
                'score': score,
                'reasons': reasons,
                'description': f['description']
            })
    
    return sorted(hotspots, key=lambda x: -x['score'])

def find_orphans(inventory, import_graph):
    """Find files not imported by anything (potential orphans)."""
    orphans = []
    
    for f in inventory:
        # Skip if it's imported
        if import_graph.get(f['path']):
            continue
        
        # Skip obvious entry points
        name = f['name']
        if name in ['__init__.py', 'run.py', 'main.py', 'cli.py']:
            continue
        
        # Skip if it's a tool with its own tool.yaml (probably intentional)
        if f['has_tool_yaml']:
            continue
        
        # Check if it's been committed recently
        if f['git']['last_commit']:
            days_ago = (datetime.now() - f['git']['last_commit']).days
            if days_ago < 90:  # Changed in last 3 months
                orphans.append({
                    'path': f['path'],
                    'name': f['name'],
                    'last_commit': f['git']['last_commit'],
                    'description': f['description'],
                    'status': 'active but isolated'
                })
            else:
                orphans.append({
                    'path': f['path'],
                    'name': f['name'],
                    'last_commit': f['git']['last_commit'],
                    'description': f['description'],
                    'status': 'stale'
                })
    
    return orphans

def find_duplicates(inventory):
    """Find files that might be doing similar things."""
    # Group by stem name (without extension)
    by_stem = {}
    for f in inventory:
        stem = Path(f['name']).stem
        if stem not in by_stem:
            by_stem[stem] = []
        by_stem[stem].append(f)
    
    duplicates = []
    for stem, files in by_stem.items():
        if len(files) > 1:
            # Check if they're in different folders
            folders = set(f['folder'] for f in files)
            if len(folders) > 1:
                duplicates.append({
                    'stem': stem,
                    'files': files,
                    'locations': list(folders)
                })
    
    return duplicates

def generate_recommendations(inventory, import_graph):
    """Actionable recommendations."""
    recs = []
    
    # Missing tool.yaml for important files
    hotspots = find_hotspots(inventory, import_graph)
    for h in hotspots[:5]:
        if not any(f['path'] == h['path'] and f['has_tool_yaml'] for f in inventory):
            recs.append({
                'type': 'document',
                'priority': 'high',
                'message': f"Add tool.yaml for {h['name']} - it's a hotspot",
                'file': h['path']
            })
    
    # Orphans to review
    orphans = find_orphans(inventory, import_graph)
    for o in orphans[:5]:
        recs.append({
            'type': 'review',
            'priority': 'medium' if o['status'] == 'active but isolated' else 'low',
            'message': f"{o['name']} appears orphaned ({o['status']})",
            'file': o['path']
        })
    
    # Duplicates to consolidate
    duplicates = find_duplicates(inventory)
    for d in duplicates[:3]:
        recs.append({
            'type': 'consolidate',
            'priority': 'medium',
            'message': f"Multiple files named {d['stem']} in {', '.join(d['locations'])}",
            'files': [f['path'] for f in d['files']]
        })
    
    return recs

# ============================================================================
# REPORTING
# ============================================================================

def generate_report(inputs):
    """Generate human-readable landscape report, optionally from a file, and save to disk."""
    try:
    # --- Data loading (new) ---
        if 'analysis_data_file' in inputs:
            file_path = Path(inputs['analysis_data_file'])
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif 'analysis_data' in inputs:
            data_input = inputs['analysis_data']
            if isinstance(data_input, str):
                # data_input is a file path
                file_path = Path(data_input)
                if not file_path.is_absolute():
                    file_path = Path.cwd() / file_path
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif isinstance(data_input, dict) and 'data_file' in data_input:
                # legacy pointer object from older versions
                file_path = Path(data_input['data_file'])
                if not file_path.is_absolute():
                    file_path = Path.cwd() / file_path
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # assume data_input is the actual data
                data = data_input
        else:
            return {'error': 'Missing analysis_data or analysis_data_file'}
        
        format_type = inputs.get('format', 'summary')
        
        report = "\n" + "="*70 + "\n"
        report += "🔧 TOOL ECOSYSTEM LANDSCAPE\n"
        report += "="*70 + "\n\n"
        
        # Summary
        summary = data.get('summary', {})
        report += f"📊 OVERVIEW\n"
        report += f"   Total Python files: {summary.get('total_files', 0)}\n"
        report += f"   With tool.yaml: {summary.get('files_with_tool_yaml', 0)} ({summary.get('coverage_percent', 0):.1f}%)\n\n"
         
        # Hotspots
        hotspots = data.get('hotspots', [])
        if hotspots:
            report += "🔥 HOTSPOTS (most important files)\n"
            for h in hotspots[:10]:
                report += f"   {h['name']} (score: {h['score']})\n"
                report += f"     {h['description'][:60]}\n"
                report += f"     {' '.join(h['reasons'][:3])}\n"
            report += "\n"
        
        # Orphans
        orphans = data.get('orphans', [])
        if orphans:
            report += "👻 ORPHANS (not imported by anything)\n"
            for o in orphans[:10]:
                status_icon = "⚠️" if o['status'] == 'active but isolated' else "💤"
                report += f"   {status_icon} {o['name']} - {o['status']}\n"
                report += f"     {o['description'][:60]}\n"
            report += "\n"
        
        # Duplicates
        duplicates = data.get('duplicates', [])
        if duplicates:
            report += "🔄 POTENTIAL DUPLICATES\n"
            for d in duplicates[:5]:
                report += f"   {d['stem']} appears in:\n"
                for f in d['files']:
                    report += f"     - {f['folder']}/{f['name']}\n"
            report += "\n"
        
        # Recommendations
        recs = data.get('recommendations', [])
        if recs:
            report += "💡 RECOMMENDATIONS\n"
            for r in recs:
                priority_icon = "🔴" if r['priority'] == 'high' else "🟡" if r['priority'] == 'medium' else "🟢"
                report += f"   {priority_icon} {r['message']}\n"
            report += "\n"
        
        # By folder breakdown
        by_folder = summary.get('by_folder', {})
        report += "📁 FOLDER BREAKDOWN\n"
        for folder, info in sorted(by_folder.items()):
            report += f"   {folder}: {info['count']} files\n"
        
        report += "="*70 + "\n"
        
        reports_dir = get_reports_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base = f"landscape_report_{timestamp}"
        
        # Write plain text
        txt_path = reports_dir / f"{base}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Write HTML (with dark theme)
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Tool Ecosystem Landscape Report</title>
    <style>
        body {{ background: #1e1e1e; color: #d4d4d4; font-family: Consolas, monospace; padding: 20px; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
<pre>{report}</pre>
</body>
</html>"""
        html_path = reports_dir / f"{base}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Return relative paths from project root (for clickability)
        cwd = Path.cwd()
        try:
            rel_txt = txt_path.relative_to(cwd)
            rel_html = html_path.relative_to(cwd)
        except ValueError:
            rel_txt = txt_path
            rel_html = html_path
        
        # Include the paths in the return dictionary
        return {
            'report': report,
            'format': format_type,
            'report_txt': str(rel_txt),
            'report_html': str(rel_html)
        }
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {'error': str(e)}

if __name__ == '__main__':
    main()