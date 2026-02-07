# tools/ai_assistant/four_layer.py - Patched version
"""
Four-layer analysis - Uses your ast_analyzer as the engine
Patched from Original V2: fixed imports and paths
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

# Fix import: use your actual ast_analyzer location
sys.path.insert(0, str(Path(__file__).parent.parent / "analysis"))
try:
    from ast_analyzer import ASTAnalyzer
    AST_ANALYZER_AVAILABLE = True
except ImportError:
    AST_ANALYZER_AVAILABLE = False
    print("Warning: ast_analyzer not available, limited analysis only")


class FourLayerAnalyzer:
    """Four-layer analysis using your ast_analyzer as the foundation"""
    
    # def __init__(self, indexer=None):
    #     self.indexer = indexer
    #     if AST_ANALYZER_AVAILABLE:
    #         self.ast_analyzer = ASTAnalyzer()
    #     else:
    #         self.ast_analyzer = None
    #         print("Running without AST analyzer - limited analysis available")

    def __init__(self, indexer=None, auto_index=True):
        self.indexer = None
        self.ast_analyzer = None
        
        # Handle indexer
        if indexer is not None:
            self.indexer = indexer
        elif auto_index:
            try:
                from tools.ai_assistant.indexer import CodebaseIndexer
                self.indexer = CodebaseIndexer()
            except Exception as e:
                print(f"Warning: Could not create indexer: {e}")
                self.indexer = None
        
        # Handle AST analyzer (existing pattern, kept for consistency)
        if AST_ANALYZER_AVAILABLE:
            self.ast_analyzer = ASTAnalyzer()
        else:
            print("Warning: AST analyzer not available")
    
    def analyze_for_context(self, topic: str) -> Dict:
        """Return structured 4-layer analysis for a topic"""
        return {
            "layer1_code_reality": self._get_code_reality(topic),
            "layer2_design_intent": self._get_design_intent(topic),
            "layer3_historical_context": self._get_historical_context(topic),
            "layer4_synthesis": self._synthesize(topic)
        }
    
    def _get_code_reality(self, topic: str) -> Dict:
        """Layer 1: What's actually implemented - using your ast_analyzer"""
        # Use indexer if available for search
        if self.indexer:
            results = self.indexer.search(topic, limit=10)
        else:
            results = []
        
        # Enhanced analysis with your ast_analyzer
        enhanced_results = []
        if self.ast_analyzer and results:
            for result in results[:5]:  # Deep analysis of top 5
                file_path = result.get('path', '')
                if Path(file_path).exists():
                    try:
                        ast_analysis = self.ast_analyzer.parse_python_file(file_path)
                        if ast_analysis:
                            enhanced_results.append({
                                'path': file_path,
                                'basic_info': {
                                    'content': result.get('content', ''),
                                    'title': result.get('title', '')
                                },
                                'ast_analysis': {
                                    'classes': ast_analysis['classes'],
                                    'functions': ast_analysis['functions'],
                                    'todos': ast_analysis['todos'],
                                    'phase_violations': ast_analysis['phase_violations'],
                                    'imports': ast_analysis['imports']
                                }
                            })
                    except Exception as e:
                        enhanced_results.append({
                            'path': file_path,
                            'basic_info': {
                                'content': result.get('content', ''),
                                'title': result.get('title', '')
                            },
                            'ast_analysis_error': str(e)
                        })
        
        # Also scan for topic-specific violations across project
        violations = []
        if self.ast_analyzer:
            try:
                project_data = self.ast_analyzer.scan_project(".")
                for file_data in project_data:
                    file_path = file_data['path']
                    if topic.lower() in file_path.lower():
                        for v in file_data.get('phase_violations', []):
                            violations.append({
                                'file': file_path,
                                'line': v.get('line'),
                                'type': v.get('type'),
                                'pattern': v.get('pattern'),
                                'text': v.get('text')
                            })
            except Exception as e:
                print(f"Warning: Could not scan project for violations: {e}")
        
        return {
            "found_files": len(results),
            "key_files": [r.get("path", "unknown") for r in results[:5]],
            "implementation_status": self._assess_implementation(results),
            "enhanced_analysis_available": self.ast_analyzer is not None,
            "enhanced_results": enhanced_results if enhanced_results else None,
            "topic_violations": violations[:10]  # Violations in topic-related files
        }
    
    def _get_design_intent(self, topic: str) -> Dict:
        """Layer 2: What was intended - from your ai_context/"""
        # Updated paths to your current structure
        design_docs = [
            "ai_context/ai_contract.md",
            "ai_context/development_playbook.md",
            "ai_context/development_playbook_mini.md",
            "ai_context/USAGE.md"
        ]
        
        # Also check archive if exists
        archive_docs = [
            "archive/Docs-old/SYSTEM_OWNERSHIP.md",
            "archive/Docs-old/ENGINE_LOOP.md",
            "archive/Docs-old/PHASE_AUDIT.md"
        ]
        
        all_docs = design_docs + archive_docs
        
        intents = []
        project_root = Path("C:/Users/bartl/dev/dj2")
        
        for doc in all_docs:
            doc_path = project_root / doc
            if doc_path.exists():
                try:
                    content = doc_path.read_text(encoding='utf-8', errors='ignore')
                    if topic.lower() in content.lower():
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if topic.lower() in line.lower():
                                context = '\n'.join(lines[max(0, i-2):min(len(lines), i+3)])
                                intents.append({
                                    "document": doc,
                                    "context": context
                                })
                                break
                except Exception as e:
                    print(f"Warning: Could not read {doc}: {e}")
        
        return {
            "design_documents_checked": all_docs,
            "documents_found": len([i for i in intents if not i['document'].startswith('archive')]),
            "archive_documents_found": len([i for i in intents if i['document'].startswith('archive')]),
            "mentions_found": len(intents),
            "relevant_sections": intents[:3]
        }
    
    def _get_historical_context(self, topic: str) -> Dict:
        """Layer 3: What was tried before - from your status_manifest and accomplishments"""
        project_root = Path("C:/Users/bartl/dev/dj2")
        historical = []
        
        # Check status_manifest.json (your current structured status)
        status_path = project_root / "ai_context" / "status_manifest.json"
        if status_path.exists():
            try:
                status = json.loads(status_path.read_text())
                for phase_name, phase_data in status.get("phases", {}).items():
                    if topic.lower() in phase_name.lower():
                        historical.append({
                            "source": "status_manifest",
                            "phase": phase_name,
                            "status": phase_data.get("status"),
                            "completed": phase_data.get("completed", []),
                            "completion_percentage": phase_data.get("completion_percentage", 0)
                        })
                
                # Also check technical debt
                for debt in status.get("technical_debt", []):
                    if topic.lower() in debt.get("component", "").lower():
                        historical.append({
                            "source": "technical_debt",
                            "component": debt.get("component"),
                            "issue": debt.get("issue"),
                            "priority": debt.get("priority")
                        })
            except Exception as e:
                print(f"Warning: Could not parse status_manifest: {e}")
        
        # Check ACCOMPLISHMENTS.md (narrative history)
        acc_path = project_root / "ACCOMPLISHMENTS.md"
        if acc_path.exists():
            try:
                content = acc_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if topic.lower() in line.lower():
                        date_section = ""
                        for j in range(max(0, i-5), i):
                            if j < len(lines) and ("January" in lines[j] or "202" in lines[j]):
                                date_section = lines[j]
                                break
                        
                        context = '\n'.join(lines[max(0, i-2):min(len(lines), i+5)])
                        historical.append({
                            "source": "ACCOMPLISHMENTS.md",
                            "date": date_section,
                            "context": context[:500]
                        })
            except Exception as e:
                print(f"Warning: Could not read ACCOMPLISHMENTS.md: {e}")
        
        # Check WORK files
        try:
            work_files = list(project_root.glob("WORK_*.md"))
            for work_file in work_files[-3:]:  # Last 3 work files
                content = work_file.read_text(encoding='utf-8', errors='ignore')
                if topic.lower() in content.lower():
                    historical.append({
                        "source": f"WORK file: {work_file.name}",
                        "date": work_file.name.replace("WORK_", "").replace(".md", ""),
                        "context": f"Mentioned in {work_file.name}"
                    })
        except Exception as e:
            print(f"Warning: Could not read WORK files: {e}")
        
        return {
            "historical_mentions": len(historical),
            "from_status": len([h for h in historical if h.get("source") == "status_manifest"]),
            "from_accomplishments": len([h for h in historical if h.get("source") == "ACCOMPLISHMENTS.md"]),
            "recent_work": historical[:3]
        }
    
    def _assess_implementation(self, search_results) -> str:
        """Assess implementation status from search results"""
        if not search_results:
            return "Not found"
        
        has_class_def = False
        has_function_def = False
        
        for r in search_results:
            content_preview = str(r.get('content', '') or r.get('content_preview', ''))
            if "class " in content_preview.lower():
                has_class_def = True
            if "def " in content_preview.lower():
                has_function_def = True
        
        if has_class_def:
            return "Class implemented"
        elif has_function_def:
            return "Functions implemented"
        else:
            return "Mentioned in code"
    
    def _synthesize(self, topic: str) -> Dict:
        """Layer 4: Synthesis for DeepSeek"""
        code_reality = self._get_code_reality(topic)
        design_intent = self._get_design_intent(topic)
        historical_context = self._get_historical_context(topic)
        
        # Generate actionable recommendations
        recommendations = []
        
        if code_reality.get("implementation_status") == "Not found":
            recommendations.append("Not implemented - start with design documents")
        elif "implemented" in code_reality.get("implementation_status", ""):
            recommendations.append("Implementation exists - review before modifying")
        
        # Add phase violation warnings if found
        violations = code_reality.get("topic_violations", [])
        if violations:
            recommendations.append(f"Found {len(violations)} phase violations in topic files - fix first")
        
        # Check if in active status
        status_entries = [h for h in historical_context.get("recent_work", []) 
                         if h.get("source") == "status_manifest"]
        if status_entries:
            for entry in status_entries:
                if entry.get("status") == "complete":
                    recommendations.append(f"Phase '{entry.get('phase')}' is complete - verify before reworking")
                elif entry.get("status") == "in_progress":
                    recommendations.append(f"Phase '{entry.get('phase')}' is in progress - check current state")
        
        # Check technical debt
        debt_entries = [h for h in historical_context.get("recent_work", []) 
                       if h.get("source") == "technical_debt"]
        if debt_entries:
            high_priority = [d for d in debt_entries if d.get("priority") == "high"]
            if high_priority:
                recommendations.append(f"High priority technical debt: {high_priority[0].get('component')}")
        
        # Estimate time based on complexity
        if code_reality.get("found_files", 0) > 5:
            estimated_time = "2-3 hours"
        elif code_reality.get("found_files", 0) > 0:
            estimated_time = "1-2 hours"
        else:
            estimated_time = "30 minutes - 1 hour"
        
        # Determine priority
        priority = "Medium"
        if violations:
            priority = "High"
        elif any(d.get("priority") == "high" for d in debt_entries):
            priority = "High"
        
        return {
            "summary": f"Topic '{topic}' is {code_reality.get('implementation_status', 'unknown')}. "
                      f"Found in {design_intent.get('mentions_found', 0)} design documents "
                      f"and {historical_context.get('historical_mentions', 0)} historical references. "
                      f"AST analysis: {'available' if code_reality.get('enhanced_analysis_available') else 'unavailable'}.",
            "recommendations": recommendations,
            "estimated_time": estimated_time,
            "priority": priority,
            "context_hints": [
                "Check ai_contract.md for boundaries",
                "Verify phase compliance with ast_analyzer",
                "Review status_manifest.json for current state",
                "Look for recent work in ACCOMPLISHMENTS.md"
            ]
        }
    
    def batch_analyze_project(self, output_dir: str = "analysis_output") -> Dict:
        """Batch analysis of entire project using your ast_analyzer"""
        if not self.ast_analyzer:
            return {"error": "AST analyzer not available for batch analysis"}
        
        project_root = Path("C:/Users/bartl/dev/dj2")
        output_path = project_root / output_dir
        output_path.mkdir(exist_ok=True)
        
        print("Running batch project analysis...")
        project_data = self.ast_analyzer.scan_project(".")
        
        reports = {
            "files_analyzed": len(project_data),
            "output_files": []
        }
        
        # 1. Phase violations report
        violations = []
        for file_data in project_data:
            for violation in file_data.get('phase_violations', []):
                violation['file'] = file_data['path']
                violations.append(violation)
        
        if violations:
            violations_file = output_path / "phase_violations.json"
            with open(violations_file, 'w') as f:
                json.dump(violations, f, indent=2)
            reports["output_files"].append(str(violations_file))
            reports["phase_violations_count"] = len(violations)
            print(f"  Found {len(violations)} phase violations")
        
        # 2. TODOs report
        todos = []
        for file_data in project_data:
            for todo in file_data.get('todos', []):
                todo['file'] = file_data['path']
                todos.append(todo)
        
        if todos:
            todos_file = output_path / "todos.json"
            with open(todos_file, 'w') as f:
                json.dump(todos, f, indent=2)
            reports["output_files"].append(str(todos_file))
            reports["todos_count"] = len(todos)
            print(f"  Found {len(todos)} TODOs")
        
        # 3. Large classes report
        large_classes = self.ast_analyzer.find_large_classes(project_data)
        if large_classes:
            large_classes_file = output_path / "large_classes.json"
            with open(large_classes_file, 'w') as f:
                json.dump(large_classes, f, indent=2)
            reports["output_files"].append(str(large_classes_file))
            reports["large_classes_count"] = len(large_classes)
            print(f"  Found {len(large_classes)} large classes")
        
        print(f"Reports saved to {output_path}")
        return reports


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Four-layer analysis tool')
    parser.add_argument('topic', help='Topic to analyze')
    parser.add_argument('--batch', action='store_true', help='Run batch analysis of entire project')
    parser.add_argument('--output', default='four_layer_analysis.json', help='Output file')
    
    args = parser.parse_args()
    
    from tools.ai_assistant.indexer import CodebaseIndexer
    indexer = CodebaseIndexer()
    analyzer = FourLayerAnalyzer(indexer=indexer)
    
    if args.batch:
        print("Running batch analysis...")
        result = analyzer.batch_analyze_project()
        print(json.dumps(result, indent=2))
    else:
        print(f"Analyzing topic: {args.topic}")
        result = analyzer.analyze_for_context(args.topic)
        
        output_path = Path("C:/Users/bartl/dev/dj2") / args.output
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nAnalysis saved to {output_path}")
        print(f"Summary: {result.get('layer4_synthesis', {}).get('summary', '')}")
        
        # Also print key recommendations
        recommendations = result.get('layer4_synthesis', {}).get('recommendations', [])
        if recommendations:
            print(f"\nRecommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")


if __name__ == '__main__':
    main()