import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
from .models import FileArchitecture, ModuleView, SystemView

class LLMContextPacker:
    def __init__(self, files: Dict[str, FileArchitecture], modules: Dict[str, List[str]], max_tokens: int = 6000):
        self.files = files
        self.modules = modules
        self.max_tokens = max_tokens
        self.estimated_tokens_per_char = 0.25  # Rough estimate
        
    def create_hierarchical_views(self) -> Dict[str, Any]:
        """
        Generate abstraction layers optimized for LLM consumption
        """
        return {
            "system_view": self._create_system_view(),
            "module_views": self._create_module_views(),
            "critical_files": self._create_critical_file_details(),
            "dependency_graph": self._create_dependency_summary()
        }
    
    def _create_system_view(self) -> SystemView:
        """High-level system architecture (fits in ~1500 tokens)"""
        entry_points = self._find_entry_points()
        data_stores = self._find_data_stores()
        
        return SystemView(
            total_files=len(self.files),
            modules=self.modules,
            entry_points=entry_points,
            data_stores=data_stores,
            external_deps=self._list_external_deps(),
            architecture_pattern=self._detect_architecture_pattern()
        )
    
    def _find_entry_points(self) -> List[str]:
        """Files that are likely entry points (not imported by others but import others)"""
        entries = []
        for path, arch in self.files.items():
            if len(arch.dependents) == 0 and len(arch.dependencies) > 0:
                entries.append(path)
            if 'main' in path.lower() or 'index' in path.lower() or 'app' in path.lower():
                if path not in entries:
                    entries.append(path)
        return entries[:10]  # Limit to top 10
    
    def _find_data_stores(self) -> List[str]:
        """Files likely handling data/models"""
        stores = []
        for path, arch in self.files.items():
            if any(x in path.lower() for x in ['model', 'schema', 'data', 'store', 'db']):
                stores.append(path)
        return stores
    
    def _list_external_deps(self) -> List[str]:
        """External libraries used across codebase"""
        external = set()
        for arch in self.files.values():
            for imp in arch.imports:
                if not imp.startswith('.') and not imp.startswith('/'):
                    external.add(imp.split('.')[0].split('/')[0])
        return sorted(list(external))[:20]  # Top 20 external deps
    
    def _detect_architecture_pattern(self) -> str:
        """Infer architecture pattern from file structure"""
        has_models = any('model' in p.lower() for p in self.files.keys())
        has_views = any('view' in p.lower() or 'component' in p.lower() for p in self.files.keys())
        has_controllers = any('controller' in p.lower() for p in self.files.keys())
        
        if has_models and has_views and has_controllers:
            return "MVC"
        elif has_models and has_views:
            return "Model-View"
        elif any('component' in p.lower() for p in self.files.keys()):
            return "Component-Based"
        else:
            return "Layered/Modular"
    
    def _create_module_views(self) -> Dict[str, Dict]:
        """Module-level summaries (each ~1000 tokens)"""
        views = {}
        for module_name, file_list in self.modules.items():
            files_in_module = [self.files[f] for f in file_list if f in self.files]
            
            # Calculate module metrics
            total_loc = sum(f.lines_of_code for f in files_in_module)
            all_exports = []
            for f in files_in_module:
                all_exports.extend(f.exports)
            
            views[module_name] = {
                "file_count": len(file_list),
                "total_lines": total_loc,
                "responsibility": self._infer_module_purpose(files_in_module),
                "public_interface": all_exports[:15],  # Top 15 exports
                "internal_complexity": sum(f.complexity_score for f in files_in_module) // max(len(files_in_module), 1),
                "key_files": self._summarize_files(file_list[:5])  # Top 5 files
            }
        return views
    
    def _infer_module_purpose(self, files: List[FileArchitecture]) -> str:
        """Generate description of what a module does"""
        purposes = [f.purpose_summary for f in files if f.purpose_summary]
        if not purposes:
            return "Utility module"
        
        # Simple heuristic: most common words in purposes
        words = ' '.join(purposes).lower().split()
        # Filter out common words
        stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'a', 'an', 'in', 'of', 'to'}
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]
        
        from collections import Counter
        top_words = Counter(keywords).most_common(3)
        return f"Handles {', '.join([w[0] for w in top_words])}" if top_words else "General functionality"
    
    def _summarize_files(self, file_paths: List[str]) -> List[Dict]:
        """Compress file details for module view"""
        summaries = []
        for path in file_paths:
            if path not in self.files:
                continue
            f = self.files[path]
            summaries.append({
                "path": path,
                "type": f.file_type,
                "loc": f.lines_of_code,
                "exports": f.exports[:5],
                "stability": "high" if len(f.dependents) > 5 else "medium" if len(f.dependents) > 0 else "low",
                "complexity": f.complexity_score
            })
        return summaries
    
    def _create_critical_file_details(self) -> Dict[str, Dict]:
        """Deep analysis of hot files (high dependency count)"""
        # Score files by importance (dependents × complexity)
        scored = []
        for path, arch in self.files.items():
            score = len(arch.dependents) * (arch.complexity_score + 1)
            scored.append((path, score, arch))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        critical = {}
        
        for path, score, arch in scored[:10]:  # Top 10 critical files
            critical[path] = {
                "score": score,
                "dependents_count": len(arch.dependents),
                "dependencies_count": len(arch.dependencies),
                "interfaces": arch.interfaces,
                "purpose": arch.purpose_summary,
                "key_patterns": arch.key_patterns,
                "risk_level": "high" if score > 50 else "medium"
            }
        return critical
    
    def _create_dependency_summary(self) -> Dict:
        """Compact dependency representation"""
        edges = []
        for path, arch in self.files.items():
            for dep in arch.dependencies[:5]:  # Limit edges per file
                edges.append(f"{path} -> {dep}")
        
        return {
            "total_edges": sum(len(arch.dependencies) for arch in self.files.values()),
            "sample_edges": edges[:20],  # Sample for context
            "circular_risk": self._detect_circular_risk()
        }
    
    def _detect_circular_risk(self) -> List[str]:
        """Simple circular dependency detection"""
        risks = []
        for path, arch in self.files.items():
            for dep in arch.dependencies:
                if dep in self.files:
                    if path in self.files[dep].dependencies:
                        risks.append(f"{path} <-> {dep}")
        return list(set(risks))[:5]  # Return unique pairs
    
    def package_for_llm(self, focus_module: Optional[str] = None) -> str:
        """
        Create a prompt-ready package, optionally focusing on specific module
        """
        views = self.create_hierarchical_views()
        
        # Estimate token count and compress if needed
        json_str = json.dumps(views, indent=2)
        estimated_tokens = len(json_str) * self.estimated_tokens_per_char
        
        if estimated_tokens > self.max_tokens:
            views = self._compress_views(views)
        
        return json.dumps(views, indent=2)
    
    def _compress_views(self, views: Dict) -> Dict:
        """Aggressive compression for token limits"""
        # Keep system view, reduce module details
        compressed = {
            "system": views["system_view"],
            "modules": {k: {
                "files": v["file_count"],
                "purpose": v["responsibility"],
                "api": v["public_interface"][:5]
            } for k, v in views["module_views"].items()},
            "critical": {k: {
                "deps": v["dependents_count"],
                "risk": v["risk_level"]
            } for k, v in views["critical_files"].items()}
        }
        return compressed
    
    def save_package(self, output_path: str, focus_module: Optional[str] = None):
        """Save LLM-ready package to file"""
        package = self.package_for_llm(focus_module)
        with open(output_path, 'w') as f:
            f.write(package)
        print(f"📦 Packaged for LLM: {output_path} ({len(package)} chars)")