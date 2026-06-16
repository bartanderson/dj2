import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import difflib

@dataclass
class FragmentContext:
    """Represents one piece of the project"""
    name: str                          # Logical name (e.g., "backend", "frontend-v2")
    root_path: Path
    files: Dict[str, 'FileArchitecture'] = field(default_factory=dict)
    modules: Dict[str, List[str]] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    external_interfaces: List[str] = field(default_factory=list)  # What it exposes to other fragments
    
@dataclass
class CrossFragmentRelationship:
    """Relationship between two fragments"""
    source_fragment: str
    target_fragment: str
    dependency_type: str  # 'api', 'shared_lib', 'data_contract', 'unknown'
    connections: List[Dict]  # Specific file-to-file links
    strength: int  # 0-100 based on number of connections
    
class MultiRootAnalyzer:
    """Manages analysis across multiple project fragments"""
    
    def __init__(self):
        self.fragments: Dict[str, FragmentContext] = {}
        self.cross_relationships: List[CrossFragmentRelationship] = []
        self.shared_patterns: Dict[str, List[str]] = defaultdict(list)  # pattern -> fragments
        
    def add_fragment(self, name: str, root_path: str, mapper_result: Dict):
        """Add a analyzed fragment to the multi-root context"""
        from .models import FileArchitecture
        
        context = FragmentContext(
            name=name,
            root_path=Path(root_path).resolve(),
            modules=mapper_result.get('metadata', {}).get('modules', {}),
            entry_points=self._detect_entry_points(mapper_result)
        )
        
        # Reconstruct FileArchitecture objects
        for path, data in mapper_result.get('files', {}).items():
            context.files[path] = FileArchitecture(**{k: v for k, v in data.items() 
                                                      if k in ['path', 'file_type', 'lines_of_code', 
                                                              'imports', 'exports', 'dependencies', 
                                                              'dependents', 'purpose_summary', 
                                                              'complexity_score', 'interfaces', 
                                                              'key_patterns']})
        
        self.fragments[name] = context
        return self
    
    def _detect_entry_points(self, mapper_result: Dict) -> List[str]:
        """Detect likely entry points in fragment"""
        files = mapper_result.get('files', {})
        entries = []
        for path, data in files.items():
            # Low dependents, high dependencies = likely entry/consumer
            # Or conventional names
            if (data.get('dependents_count', 0) == 0 and data.get('dependencies_count', 0) > 0) or \
               any(x in path.lower() for x in ['main', 'index', 'app', 'server', 'client']):
                entries.append(path)
        return entries[:5]
    
    def analyze_cross_fragment_relationships(self):
        """Find how fragments relate to each other"""
        print("🔗 Analyzing cross-fragment relationships...")
        
        fragment_names = list(self.fragments.keys())
        
        for i, frag_a_name in enumerate(fragment_names):
            for frag_b_name in fragment_names[i+1:]:
                frag_a = self.fragments[frag_a_name]
                frag_b = self.fragments[frag_b_name]
                
                relationship = self._find_relationships(frag_a, frag_b)
                if relationship.connections:
                    self.cross_relationships.append(relationship)
                    print(f"   Found {len(relationship.connections)} links: {frag_a_name} <-> {frag_b_name}")
        
        # Detect shared code patterns
        self._detect_shared_patterns()
        
        return self
    
    def _find_relationships(self, frag_a: FragmentContext, frag_b: FragmentContext) -> CrossFragmentRelationship:
        """Find specific relationships between two fragments"""
        connections = []
        
        # Strategy 1: Import path analysis
        for path_a, arch_a in frag_a.files.items():
            for imp in arch_a.imports:
                # Check if import references frag_b
                if self._import_points_to_fragment(imp, frag_b):
                    connections.append({
                        'type': 'import',
                        'from': f"{frag_a.name}/{path_a}",
                        'to': f"{frag_b.name}/{self._resolve_import_path(imp, frag_b)}",
                        'import_path': imp
                    })
        
        # Strategy 2: Shared data contracts (similar exports)
        contracts = self._find_shared_contracts(frag_a, frag_b)
        connections.extend(contracts)
        
        # Strategy 3: API endpoint matching
        api_links = self._find_api_links(frag_a, frag_b)
        connections.extend(api_links)
        
        # Determine relationship type
        dep_type = self._classify_relationship(connections)
        
        return CrossFragmentRelationship(
            source_fragment=frag_a.name,
            target_fragment=frag_b.name,
            dependency_type=dep_type,
            connections=connections,
            strength=min(len(connections) * 10, 100)
        )
    
    def _import_points_to_fragment(self, import_path: str, fragment: FragmentContext) -> bool:
        """Check if an import string likely points to another fragment"""
        # Check if import path contains fragment name or alias
        frag_name_lower = fragment.name.lower()
        if frag_name_lower in import_path.lower():
            return True
        
        # Check if import resolves to a file in fragment
        parts = import_path.split('/')
        for part in parts:
            if any(part in f.lower() for f in fragment.files.keys()):
                return True
        
        return False
    
    def _resolve_import_path(self, import_path: str, fragment: FragmentContext) -> Optional[str]:
        """Try to resolve import to actual file in fragment"""
        # Simple stem matching
        stem = import_path.split('/')[-1].split('.')[0]
        for path in fragment.files.keys():
            if Path(path).stem == stem:
                return path
        return None
    
    def _find_shared_contracts(self, frag_a: FragmentContext, frag_b: FragmentContext) -> List[Dict]:
        """Find similar data structures between fragments"""
        connections = []
        
        # Compare exports for similarity
        for path_a, arch_a in frag_a.files.items():
            for path_b, arch_b in frag_b.files.items():
                # Check for similar class/function names
                common_exports = set(arch_a.exports) & set(arch_b.exports)
                if common_exports:
                    similarity = difflib.SequenceMatcher(None, 
                        arch_a.purpose_summary or "", 
                        arch_b.purpose_summary or "").ratio()
                    
                    if similarity > 0.3 or len(common_exports) > 2:
                        connections.append({
                            'type': 'shared_contract',
                            'from': f"{frag_a.name}/{path_a}",
                            'to': f"{frag_b.name}/{path_b}",
                            'common_exports': list(common_exports),
                            'similarity': round(similarity, 2)
                        })
        
        return connections
    
    def _find_api_links(self, frag_a: FragmentContext, frag_b: FragmentContext) -> List[Dict]:
        """Find API endpoint relationships"""
        connections = []
        
        # Look for URL patterns in code
        url_pattern = r'["\']((?:http|/)[^"\']+)["\']'
        import re
        
        for path_a, arch_a in frag_a.files.items():
            content = self._get_file_content(path_a, frag_a) or ""
            urls = re.findall(url_pattern, content)
            
            for url in urls:
                # Check if URL points to frag_b
                if frag_b.name.lower() in url.lower():
                    connections.append({
                        'type': 'api_call',
                        'from': f"{frag_a.name}/{path_a}",
                        'to': f"{frag_b.name}/[api_endpoint]",
                        'endpoint': url
                    })
        
        return connections
    
    def _get_file_content(self, relative_path: str, fragment: FragmentContext) -> Optional[str]:
        """Retrieve file content for deep analysis"""
        full_path = fragment.root_path / relative_path
        try:
            return full_path.read_text(encoding='utf-8', errors='ignore')
        except:
            return None
    
    def _classify_relationship(self, connections: List[Dict]) -> str:
        """Classify the type of dependency"""
        types = [c['type'] for c in connections]
        
        if 'api_call' in types:
            return 'api'
        elif 'import' in types:
            return 'shared_lib'
        elif 'shared_contract' in types:
            return 'data_contract'
        else:
            return 'unknown'
    
    def _detect_shared_patterns(self):
        """Detect architectural patterns shared across fragments"""
        for name, fragment in self.fragments.items():
            patterns = set()
            for arch in fragment.files.values():
                patterns.update(arch.key_patterns)
            
            for pattern in patterns:
                self.shared_patterns[pattern].append(name)
    
    def generate_unified_view(self) -> Dict:
        """Create a unified architectural view across all fragments"""
        return {
            "fragments": {
                name: {
                    "root": str(ctx.root_path),
                    "file_count": len(ctx.files),
                    "modules": ctx.modules,
                    "entry_points": ctx.entry_points,
                    "architecture_summary": self._summarize_fragment_architecture(ctx)
                }
                for name, ctx in self.fragments.items()
            },
            "cross_fragment_relationships": [
                {
                    "between": [r.source_fragment, r.target_fragment],
                    "type": r.dependency_type,
                    "strength": r.strength,
                    "key_connections": r.connections[:5]  # Top 5
                }
                for r in self.cross_relationships
            ],
            "integration_points": self._identify_integration_points(),
            "shared_patterns": {k: v for k, v in self.shared_patterns.items() if len(v) > 1},
            "merge_recommendations": self._generate_merge_recommendations()
        }
    
    def _summarize_fragment_architecture(self, ctx: FragmentContext) -> str:
        """Generate architectural summary for a fragment"""
        file_types = defaultdict(int)
        for arch in ctx.files.values():
            file_types[arch.file_type] += 1
        
        total_loc = sum(arch.lines_of_code for arch in ctx.files.values())
        
        # Detect likely architecture
        has_html = file_types.get('html', 0) > 0
        has_js = file_types.get('javascript', 0) > 0
        has_py = file_types.get('python', 0) > 0
        
        if has_html and has_js:
            arch_type = "Frontend/UI"
        elif has_py and not has_html:
            arch_type = "Backend/API"
        else:
            arch_type = "Mixed/Fullstack"
        
        return {
            "type": arch_type,
            "files_by_type": dict(file_types),
            "total_lines": total_loc,
            "avg_complexity": sum(arch.complexity_score for arch in ctx.files.values()) // max(len(ctx.files), 1)
        }
    
    def _identify_integration_points(self) -> List[Dict]:
        """Identify specific points where fragments must integrate"""
        points = []
        
        for rel in self.cross_relationships:
            if rel.dependency_type == 'api':
                points.append({
                    "type": "api_boundary",
                    "fragments": [rel.source_fragment, rel.target_fragment],
                    "description": f"API calls from {rel.source_fragment} to {rel.target_fragment}",
                    "files_involved": list(set(c['from'] for c in rel.connections))[:3]
                })
            elif rel.dependency_type == 'shared_lib':
                points.append({
                    "type": "shared_library",
                    "fragments": [rel.source_fragment, rel.target_fragment],
                    "description": f"Shared code dependencies",
                    "risk": "high" if rel.strength > 50 else "medium"
                })
        
        return points
    
    def _generate_merge_recommendations(self) -> List[Dict]:
        """Generate strategic recommendations for merging fragments"""
        recommendations = []
        
        # Check for duplicate functionality
        for pattern, fragments in self.shared_patterns.items():
            if len(fragments) > 1:
                recommendations.append({
                    "type": "deduplication",
                    "priority": "high",
                    "description": f"Pattern '{pattern}' found in {fragments}",
                    "action": f"Consolidate {pattern} implementations into shared library"
                })
        
        # Check for API coupling
        api_rels = [r for r in self.cross_relationships if r.dependency_type == 'api']
        if api_rels:
            recommendations.append({
                "type": "api_consolidation",
                "priority": "medium",
                "description": f"Found {len(api_rels)} API-coupled fragment pairs",
                "action": "Consider unified API gateway or shared service layer"
            })
        
        # Check for structural similarities
        similar_fragments = self._find_similar_fragments()
        for pair, similarity in similar_fragments:
            recommendations.append({
                "type": "merge_candidates",
                "priority": "low" if similarity < 0.5 else "medium",
                "fragments": pair,
                "similarity": similarity,
                "action": "Consider merging if serving similar purposes"
            })
        
        return recommendations
    
    def _find_similar_fragments(self) -> List[Tuple[List[str], float]]:
        """Find structurally similar fragments"""
        similarities = []
        names = list(self.fragments.keys())
        
        for i, name_a in enumerate(names):
            for name_b in names[i+1:]:
                frag_a = self.fragments[name_a]
                frag_b = self.fragments[name_b]
                
                # Compare module structures
                modules_a = set(frag_a.modules.keys())
                modules_b = set(frag_b.modules.keys())
                
                if modules_a and modules_b:
                    intersection = len(modules_a & modules_b)
                    union = len(modules_a | modules_b)
                    similarity = intersection / union if union > 0 else 0
                    
                    if similarity > 0.3:
                        similarities.append(([name_a, name_b], round(similarity, 2)))
        
        return sorted(similarities, key=lambda x: x[1], reverse=True)
    
    def generate_merge_plan_prompt(self, target_structure: str = "unified") -> str:
        """Generate LLM prompt for multi-fragment merge planning"""
        unified = self.generate_unified_view()
        
        prompt = f"""You are planning the integration of a fragmented project consisting of {len(self.fragments)} separate codebases.

## FRAGMENT OVERVIEW
```json
{json.dumps(unified['fragments'], indent=2)}
```
"""