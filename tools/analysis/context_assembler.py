# tools/analysis/context_assembler.py
#!/usr/bin/env python3
"""
Context Assembler - Intent-driven file discovery using discovered categories
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
import argparse


class IntentParser:
    """Parse intent using discovered categories"""
    
    def __init__(self, categories_file="ai_context/discovered_categories.json"):
        with open(categories_file) as f:
            data = json.load(f)
            self.clusters = data.get("clusters", [])
    
    def parse(self, intent: str) -> Dict[str, Any]:
        """Match intent to discovered clusters"""
        intent_lower = intent.lower()
        
        matched_clusters = []
        for cluster in self.clusters:
            score = 0
            for concept in cluster.get("concepts", []):
                if concept in intent_lower:
                    score += 1
            
            if score > 0:
                matched_clusters.append({
                    "name": cluster["name"],
                    "score": score,
                    "concepts": cluster["concepts"][:5]
                })
        
        # Also extract explicit mentions
        file_patterns = re.findall(r'[\w/]+\.py', intent)
        class_patterns = re.findall(r'\b[A-Z][a-zA-Z]+\b', intent)
        
        return {
            "matched_clusters": sorted(matched_clusters, key=lambda x: x["score"], reverse=True)[:3],
            "explicit_files": file_patterns,
            "explicit_classes": class_patterns,
            "raw_intent": intent
        }


class FileFinder:
    """Find files based on cluster membership"""
    
    def __init__(self, categories_file="discovered_categories.json"):
        with open(categories_file) as f:
            data = json.load(f)
            self.clusters = data.get("clusters", [])
    
    def find(self, parsed_intent: Dict) -> List[Dict]:
        """Find files from matched clusters"""
        files = []
        seen = set()
        
        # Get files from top clusters
        for cluster in parsed_intent["matched_clusters"]:
            cluster_data = next((c for c in self.clusters if c["name"] == cluster["name"]), None)
            if cluster_data:
                for filepath in cluster_data.get("files", []):
                    if filepath not in seen:
                        files.append({
                            "path": filepath,
                            "cluster": cluster["name"],
                            "relevance": cluster["score"]
                        })
                        seen.add(filepath)
        
        # Add explicit file matches
        for explicit in parsed_intent["explicit_files"]:
            for cluster in self.clusters:
                for filepath in cluster.get("files", []):
                    if explicit in filepath and filepath not in seen:
                        files.append({
                            "path": filepath,
                            "cluster": "explicit",
                            "relevance": 10
                        })
                        seen.add(filepath)
        
        # Sort by relevance
        files.sort(key=lambda x: x["relevance"], reverse=True)
        return files[:5]  # Top 5


class Assembler:
    """Main orchestrator"""
    
    def __init__(self, categories_file="discovered_categories.json"):
        self.parser = IntentParser(categories_file)
        self.finder = FileFinder(categories_file)
    
    def assemble(self, intent: str) -> Dict:
        """Full pipeline: intent → files"""
        parsed = self.parser.parse(intent)
        files = self.finder.find(parsed)
        
        return {
            "intent": intent,
            "matched_clusters": [c["name"] for c in parsed["matched_clusters"]],
            "files": [f["path"] for f in files],
            "file_details": files
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("intent", help="What you want to find (e.g., 'character creation')")
    parser.add_argument("--categories", "-c", default="ai_context/discovered_categories.json")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="text")
    
    args = parser.parse_args()
    
    assembler = Assembler(args.categories)
    result = assembler.assemble(args.intent)
    
    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(f"Intent: {result['intent']}")
        print(f"Clusters: {', '.join(result['matched_clusters'])}")
        print(f"\nFiles to examine:")
        for f in result["file_details"]:
            print(f"  - {f['path']} (from {f['cluster']}, relevance {f['relevance']})")


if __name__ == "__main__":
    main()