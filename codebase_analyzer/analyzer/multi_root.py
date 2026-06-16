import json
import re
import difflib
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class FragmentContext:
    """Represents one logical unit of a distributed project (e.g., 'backend', 'mobile-app')"""
    name: str
    root_path: Path
    files: Dict[str, Any] = field(default_factory=dict)  # Stores FileArchitecture objects
    modules: Dict[str, List[str]] = field(default_factory=dict)
    entry_points: List[str] = field(default_factory=list)
    # Cached signals for cross-analysis to avoid repeated disk reads
    api_signals: Set[str] = field(default_factory=set)
    exported_symbols: Set[str] = field(default_factory=set)

@dataclass
class CrossFragmentRelationship:
    """Detailed relationship mapping between two fragments"""
    source_fragment: str
    target_fragment: str
    dependency_type: str  # 'api', 'shared_lib', 'data_contract', 'unknown'
    connections: List[Dict]
    strength: int  # 0-100 score

class MultiRootAnalyzer:
    """Manages analysis and integration planning across multiple codebase fragments"""

    def __init__(self):
        self.fragments: Dict[str, FragmentContext] = {}
        self.cross_relationships: List[CrossFragmentRelationship] = []
        self.shared_patterns: Dict[str, List[str]] = defaultdict(list)
        self.url_regex = re.compile(r'["\']((?:http|/|api/|v1/)[^"\']{3,})["\']')

    def add_fragment(self, name: str, root_path: str, mapper_result: Dict):
        """Register an analyzed fragment and extract signals for cross-linking"""
        from .models import FileArchitecture
        
        context = FragmentContext(
            name=name,
            root_path=Path(root_path).resolve(),
            modules=mapper_result.get('metadata', {}).get('modules', {}),
        )

        # 1. Reconstruct and Cache Files
        for path, data in mapper_result.get('files', {}).items():
            arch = FileArchitecture(**{k: v for k, v in data.items() if k in FileArchitecture.__dataclass_fields__})
            context.files[path] = arch
            
            # 2. Extract context-free signals for cross-fragment matching
            context.exported_symbols.update(arch.exports)
            
            # 3. Detect Entry Points (Low dependents + naming conventions)
            if (data.get('dependents_count', 0) == 0 and data.get('dependencies_count', 0) > 0) or \
               any(x in path.lower() for x in ['main', 'index', 'app', 'server', 'manage.py']):
                if len(context.entry_points) < 10:
                    context.entry_points.append(path)

        self.fragments[name] = context
        return self

    def analyze_relationships(self):
        """Compute how all registered fragments interact"""
        fragment_names = list(self.fragments.keys())
        
        for i, name_a in enumerate(fragment_names):
            for name_b in fragment_names[i+1:]:
                frag_a = self.fragments[name_a]
                frag_b = self.fragments[name_b]
                
                # Check A -> B and B -> A
                rel_ab = self._find_connections(frag_a, frag_b)
                if rel_ab.connections:
                    self.cross_relationships.append(rel_ab)

        self._detect_shared_patterns()
        return self

    def _find_connections(self, source: FragmentContext, target: FragmentContext) -> CrossFragmentRelationship:
        """Finds specific code-level links between two fragments"""
        connections = []

        # Strategy 1: Path-based Import Analysis
        for path_src, arch in source.files.items():
            for imp in arch.imports:
                # Resolve: Does this import string look like a path in the target fragment?
                resolved_target = self._resolve_cross_import(imp, target)
                if resolved_target:
                    connections.append({
                        'type': 'import',
                        'from': f"{source.name}:{path_src}",
                        'to': f"{target.name}:{resolved_target}",
                        'symbol': imp
                    })

        # Strategy 2: Data Contract Overlap (Shared Exports)
        overlap = source.exported_symbols.intersection(target.exported_symbols)
        # Filter out common noise
        noisy_symbols = {'main', 'init', 'setup', 'config', 'data', 'handler'}
        clean_overlap = overlap - noisy_symbols
        
        if clean_overlap:
            connections.append({
                'type': 'shared_contract',
                'symbols': list(clean_overlap)[:10],
                'count': len(clean_overlap)
            })

        # Strategy 3: API/Endpoint Discovery (Only if files are small enough to re-scan)
        # In a production version, this regex should happen during initial mapper parsing
        api_links = self._detect_api_calls(source, target)
        connections.extend(api_links)

        return CrossFragmentRelationship(
            source_fragment=source.name,
            target_fragment=target.name,
            dependency_type=self._classify(connections),
            connections=connections,
            strength=min(len(connections) * 15, 100)
        )

    def _resolve_cross_import(self, import_str: str, target: FragmentContext) -> Optional[str]:
        """Sophisticated matching of import strings to target fragment files"""
        # Normalize: 'apps.users.models' -> 'apps/users/models'
        norm_imp = import_str.replace('.', '/').lower()
        
        for target_path in target.files.keys():
            target_lower = target_path.lower()
            # Direct match or partial path match
            if norm_imp in target_lower or target_lower.endswith(norm_imp):
                return target_path
        return None

    def _detect_api_calls(self, source: FragmentContext, target: FragmentContext) -> List[Dict]:
        """Scans source files for URL patterns that mention the target fragment name"""
        links = []
        target_hint = target.name.lower().replace('-','_')
        
        for path, arch in source.files.items():
            # Optimization: only scan files likely to contain network calls
            if arch.file_type not in ['python', 'javascript', 'typescript']:
                continue
                
            content = self._read_safe(source.root_path / path)
            if not content: continue
            
            urls = self.url_regex.findall(content)
            for url in urls:
                if target_hint in url.lower() or any(ep.split('/')[0] in url for ep in target.entry_points):
                    links.append({
                        'type': 'api_call',
                        'file': f"{source.name}:{path}",
                        'endpoint': url
                    })
        return links

    def _classify(self, connections: List[Dict]) -> str:
        types = {c['type'] for c in connections}
        if 'api_call' in types: return 'api_coupled'
        if 'import' in types: return 'direct_dependency'
        if 'shared_contract' in types: return 'structural_overlap'
        return 'loose_association'

    def _detect_shared_patterns(self):
        for name, frag in self.fragments.items():
            patterns = set()
            for f in frag.files.values():
                patterns.update(f.key_patterns)
            for p in patterns:
                self.shared_patterns[p].append(name)

    def _read_safe(self, path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding='utf-8', errors='ignore')
        except:
            return None

    def get_unified_view(self) -> Dict:
        """Generates the final data structure for LLM consumption"""
        return {
            "system_topology": {
                name: {
                    "type": "fragment",
                    "files": len(ctx.files),
                    "entries": ctx.entry_points,
                    "tech_stack": list({f.file_type for f in ctx.files.values()})
                } for name, ctx in self.fragments.items()
            },
            "inter_fragment_graph": [
                {
                    "source": r.source_fragment,
                    "target": r.target_fragment,
                    "type": r.dependency_type,
                    "strength": r.strength,
                    "sample_connections": r.connections[:3]
                } for r in self.cross_relationships
            ],
            "shared_patterns": {k: v for k, v in self.shared_patterns.items() if len(v) > 1}
        }

    def generate_merge_plan_prompt(self, target_goal: str = "monolith") -> str:
        """Produces a structured prompt for an LLM to plan the integration"""
        view = self.get_unified_view()
        
        prompt = f"""You are a Senior Software Architect. We are consolidating {len(self.fragments)} distinct codebases.
Target Architecture: {target_goal}

### PROJECT TOPOLOGY
{json.dumps(view['system_topology'], indent=2)}

### IDENTIFIED RELATIONSHIPS
{json.dumps(view['inter_fragment_graph'], indent=2)}

### SHARED ARCHITECTURAL PATTERNS
{json.dumps(view['shared_patterns'], indent=2)}

### TASK
Please provide a step-by-step Merge Plan. Address the following:
1. **Dependency Order**: Which fragments should be moved first?
2. **Shared Logic**: How to handle the shared patterns (e.g., creating a /common or /shared directory)?
3. **API Integrity**: How to ensure the 'api_coupled' relationships remain functional during the move.
4. **Namespace Collisions**: Identify risks based on the shared symbols found.

Provide the response in Markdown format with a clear technical roadmap.
"""
        return prompt