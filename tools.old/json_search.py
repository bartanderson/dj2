# tools/json_search.py
"""
Wrapper around ai.py search that outputs JSON
"""
import subprocess
import json
import sys
import re
from pathlib import Path

def search_to_json(query: str, limit: int = 10) -> list:
    """
    Run ai.py search and return results as JSON
    
    Returns: List of dicts with 'file', 'score', 'exists', 'is_python' keys
    """
    cmd = [sys.executable, "ai.py", "search", query, "--limit", str(limit), "--group", "python"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).parent.parent)
        )
        
        if result.returncode != 0:
            return []
        
        # Parse the output
        results = []
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or not line[0].isdigit():
                continue
                
            # Parse: "1. path (score: X)"
            match = re.match(r'^(\d+)\.\s+(.+?)\s+\(score:\s*([\d.]+)\)$', line)
            if match:
                rank, file_path, score = match.groups()
                results.append({
                    'rank': int(rank),
                    'file': file_path,
                    'score': float(score),
                    'exists': Path(file_path).exists(),
                    'is_python': file_path.endswith('.py')
                })
        
        return results
        
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []

def main():
    """CLI interface for JSON search"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Search with JSON output")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Number of results")
    parser.add_argument("--human", action="store_true", help="Also show human-readable output")
    
    args = parser.parse_args()
    
    results = search_to_json(args.query, args.limit)
    
    if args.human:
        print("Human-readable output:")
        subprocess.run([sys.executable, "ai.py", "search", args.query, "--limit", str(args.limit)])
        print("\n" + "="*60 + "\n")
    
    print(json.dumps(results, indent=2))
    
if __name__ == "__main__":
    main()