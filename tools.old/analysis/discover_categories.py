# tools/analysis/discover_categories.py
#!/usr/bin/env python3
"""
Discover hierarchical categories from code identifiers
Links to violations/TODOs to find blockers
"""

import ast
import json
import re
from pathlib import Path
from collections import defaultdict
import argparse


def extract_identifiers(filepath):
    """Extract meaningful identifiers from Python file"""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        tree = ast.parse(content)
        
        identifiers = {
            "file": str(filepath),
            "classes": [],
            "functions": [],
            "methods": []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                identifiers["classes"].append(node.name)
            elif isinstance(node, ast.FunctionDef):
                # Skip if it's a method (handled separately)
                if not isinstance(getattr(node, 'parent', None), ast.ClassDef):
                    identifiers["functions"].append(node.name)
        
        return identifiers
    except:
        return None


def split_camel_snake(name):
    """Break CamelCase and snake_case into words"""
    camel_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    return camel_split.replace('_', ' ').lower().split()


def build_vocabulary(identifiers_list):
    """Build concept vocabulary from identifiers"""
    concept_files = defaultdict(set)
    
    for ident in identifiers_list:
        if not ident:
            continue
        filepath = ident.get("file", "")
        
        for name in ident.get("classes", []) + ident.get("functions", []):
            words = split_camel_snake(name)
            for word in words:
                if len(word) > 3:  # Skip short words
                    concept_files[word].add(filepath)
    
    # Convert to frequency list
    vocabulary = []
    for concept, files in concept_files.items():
        vocabulary.append({
            "concept": concept,
            "frequency": len(files),
            "files": list(files)[:10]  # Sample
        })
    
    vocabulary.sort(key=lambda x: x["frequency"], reverse=True)
    return vocabulary


def find_categories(vocabulary):
    """Find natural categories by co-occurrence"""
    # Build co-occurrence matrix
    co_occurrence = defaultdict(lambda: defaultdict(int))
    
    for item in vocabulary:
        concept = item["concept"]
        files = set(item["files"])
        
        for other in vocabulary:
            if other["concept"] != concept:
                overlap = len(files & set(other["files"]))
                if overlap > 0:
                    co_occurrence[concept][other["concept"]] = overlap
    
    # Simple clustering
    visited = set()
    categories = []
    
    for concept in sorted(co_occurrence.keys(), 
                         key=lambda x: sum(co_occurrence[x].values()), 
                         reverse=True):
        if concept in visited:
            continue
        
        related = sorted(co_occurrence[concept].items(), 
                        key=lambda x: x[1], reverse=True)[:5]
        
        if related:
            category = {
                "core_concept": concept,
                "related_concepts": [{"name": r[0], "strength": r[1]} for r in related],
                "files": list(set(
                    f for item in vocabulary if item["concept"] == concept 
                    for f in item["files"]
                ))
            }
            categories.append(category)
            visited.add(concept)
            for r in related:
                visited.add(r[0])
    
    return categories


def load_problems(violations_file, todos_file):
    """Load violations and TODOs if available"""
    problems = []
    
    if violations_file and Path(violations_file).exists():
        try:
            with open(violations_file) as f:
                data = json.load(f)
                for item in data if isinstance(data, list) else []:
                    problems.append({
                        "type": "violation",
                        "file": item.get("file", ""),
                        "description": item.get("description", ""),
                        "severity": "high"
                    })
        except:
            pass
    
    if todos_file and Path(todos_file).exists():
        try:
            with open(todos_file) as f:
                data = json.load(f)
                for item in data if isinstance(data, list) else []:
                    problems.append({
                        "type": "todo",
                        "file": item.get("file", ""),
                        "description": item.get("text", ""),
                        "severity": "low"
                    })
        except:
            pass
    
    return problems


def link_problems(categories, problems):
    """Link problems to categories"""
    for cat in categories:
        cat_problems = []
        for prob in problems:
            if prob["file"] in cat["files"]:
                cat_problems.append(prob)
        
        cat["problems"] = cat_problems
        cat["blocker_score"] = sum(
            3 if p["severity"] == "high" else 1 for p in cat_problems
        )
    
    categories.sort(key=lambda x: x["blocker_score"], reverse=True)
    return categories

def cluster_concepts(vocab, target_clusters=15):
    """Cluster vocabulary into semantic categories"""
    from collections import defaultdict
    
    # Build co-occurrence matrix
    co_occurrence = defaultdict(lambda: defaultdict(int))
    
    for i, v1 in enumerate(vocab):
        files1 = set(v1["files"])
        for v2 in vocab[i+1:]:
            files2 = set(v2["files"])
            overlap = len(files1 & files2)
            if overlap > 0:
                co_occurrence[v1["concept"]][v2["concept"]] = overlap
                co_occurrence[v2["concept"]][v1["concept"]] = overlap
    
    # Agglomerative clustering
    clusters = []
    assigned = set()
    
    # Sort by connectivity
    sorted_concepts = sorted(
        [v["concept"] for v in vocab],
        key=lambda x: sum(co_occurrence.get(x, {}).values()),
        reverse=True
    )
    
    for concept in sorted_concepts:
        if concept in assigned:
            continue
        
        cluster = {
            "name": concept,
            "concepts": [concept],
            "total_frequency": next(v["frequency"] for v in vocab if v["concept"] == concept)
        }
        assigned.add(concept)
        
        # Add related concepts
        related = co_occurrence.get(concept, {})
        for rel, strength in sorted(related.items(), key=lambda x: x[1], reverse=True):
            if rel not in assigned and len(cluster["concepts"]) < 10:
                cluster["concepts"].append(rel)
                cluster["total_frequency"] += next(v["frequency"] for v in vocab if v["concept"] == rel)
                assigned.add(rel)
        
        clusters.append(cluster)
        
        if len(clusters) >= target_clusters:
            break
    
    return clusters


def detect_architectural_smells(identifiers_list):
    """Find code smells beyond phase violations"""
    smells = []
    
    for ident in identifiers_list:
        if not ident:
            continue
            
        filepath = ident.get("file", "")
        
        # God Class: too many methods
        method_count = len(ident.get("methods", []))
        if method_count > 20:
            smells.append({
                "type": "god_class",
                "file": filepath,
                "method_count": method_count,
                "severity": "medium",
                "suggestion": "Consider splitting into smaller classes"
            })
        
        # High imports
        import_count = len(ident.get("imports", []))
        if import_count > 15:
            smells.append({
                "type": "high_fan_out",
                "file": filepath,
                "import_count": import_count,
                "severity": "low",
                "suggestion": "Check for cohesion issues"
            })
    
    # Naming inconsistencies
    naming_patterns = defaultdict(list)
    for ident in identifiers_list:
        if not ident:
            continue
        for cls in ident.get("classes", []):
            for pattern in ["manager", "controller", "service", "system", "handler"]:
                if pattern in cls.lower():
                    naming_patterns[pattern].append(cls)
    
    for pattern, classes in naming_patterns.items():
        if len(classes) > 5:
            smells.append({
                "type": "naming_inconsistency",
                "pattern": pattern,
                "examples": classes[:3],
                "severity": "low",
                "suggestion": f"Standardize naming: {pattern} used {len(classes)} times"
            })
    
    return smells
def main():
    parser = argparse.ArgumentParser(description="Discover categories from code")
    parser.add_argument("--dirs", "-d", nargs="+", default=["world", "dungeon_neo", "core", "engine", "ai", "routes"],
                       help="Directories to scan")
    parser.add_argument("--violations", "-v", help="Violations JSON file")
    parser.add_argument("--todos", "-t", help="TODOs JSON file")
    parser.add_argument("--output", "-o", default="ai_context/discovered_categories.json",
                       help="Output file")
    parser.add_argument("--clusters", "-c", type=int, default=15,
                       help="Target number of clusters")
    
    args = parser.parse_args()
    
    # Scan files
    files = []
    for d in args.dirs:
        files.extend(Path(d).rglob("*.py"))
    
    print(f"Scanning {len(files)} files...")
    
    # Extract identifiers
    identifiers = [extract_identifiers(f) for f in files]
    identifiers = [i for i in identifiers if i]
    
    print(f"Extracted identifiers from {len(identifiers)} files")
    
    # Build vocabulary (341 concepts)
    vocab = build_vocabulary(identifiers)
    print(f"Found {len(vocab)} unique concepts")
    print(f"Top concepts: {', '.join(c['concept'] for c in vocab[:5])}")
    
    # CLUSTER: 341 → ~15 categories
    clusters = cluster_concepts(vocab, args.clusters)
    print(f"Clustered into {len(clusters)} categories")
    

    # Print all clusters with members
    print(f"\n{'='*60}")
    print("ALL CLUSTERS WITH MEMBERS")
    print(f"{'='*60}")
    for i, cl in enumerate(clusters, 1):
        print(f"\n{i}. {cl['name'].upper()}")
        print(f"   Concepts ({len(cl['concepts'])}): {', '.join(cl['concepts'])}")
        print(f"   Files ({len(cl.get('files', []))}): {len(cl.get('files', []))} files")
        if cl.get('problems'):
            print(f"   Problems: {len(cl['problems'])} (score: {cl.get('blocker_score', 0)})")
    print(f"{'='*60}")
    

    # DETECT ARCHITECTURAL SMELLS
    smells = detect_architectural_smells(identifiers)
    if smells:
        print(f"Found {len(smells)} architectural smells")
    
    # Link files to clusters
    for cluster in clusters:
        cluster_files = set()
        for concept in cluster["concepts"]:
            for v in vocab:
                if v["concept"] == concept:
                    cluster_files.update(v["files"])
        cluster["files"] = list(cluster_files)
    
    # Link problems to clusters
    problems = load_problems(args.violations, args.todos)
    if problems:
        for cluster in clusters:
            cluster_problems = []
            for prob in problems:
                if prob["file"] in cluster["files"]:
                    cluster_problems.append(prob)
            cluster["problems"] = cluster_problems
            cluster["blocker_score"] = sum(
                3 if p["severity"] == "high" else 1 for p in cluster_problems
            )
        
        clusters.sort(key=lambda x: x.get("blocker_score", 0), reverse=True)
        print(f"Linked {len(problems)} problems to clusters")
    
    # Save
    output = {
        "vocabulary_size": len(vocab),
        "clusters": clusters,
        "architectural_smells": smells,
        "total_files": len(identifiers)
    }
    
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSaved to {args.output}")
    
    # Print summary
    if clusters:
        print("\nTop clusters by blocker score:")
        for cl in clusters[:5]:
            score = cl.get("blocker_score", 0)
            prob_count = len(cl.get("problems", []))
            print(f"  {cl['name']}: {len(cl['concepts'])} concepts, score={score}, problems={prob_count}")
    
    if smells:
        print("\nArchitectural smells:")
        for smell in smells[:5]:
            print(f"  {smell['type']}: {smell.get('file', 'N/A')} ({smell['severity']})")


if __name__ == "__main__":
    main()