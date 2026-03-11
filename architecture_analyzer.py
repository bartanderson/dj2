# architecture_analyzer.py
import ast
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Optional
import re

@dataclass
class FileArchitecture:
    path: str
    file_type: str
    lines_of_code: int
    imports: List[str]
    exports: List[str]  # Functions, classes, variables exported
    dependencies: List[str]  # Other project files it uses
    dependents: List[str]  # Files that use this
    purpose_summary: str  # AI-generated or docstring-based
    complexity_score: int
    interfaces: List[Dict]  # Function signatures, class methods
    data_flows: List[Dict]  # Where data comes from/goes
    key_patterns: List[str]  # Design patterns used
    
class ArchitectureMapper:
    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.files: Dict[str, FileArchitecture] = {}
        self.module_graph = {}
        
    def analyze_all(self):
        """Phase 1: Deep analysis of every file"""
        for file_path in self.root.rglob("*"):
            if file_path.suffix in ['.py', '.js', '.html', '.css']:
                self._analyze_file(file_path)
        
        # Second pass: resolve cross-file dependencies
        self._build_dependency_graph()
        return self
    
    def _analyze_file(self, path: Path):
        content = path.read_text(encoding='utf-8')
        loc = len(content.splitlines())
        
        if path.suffix == '.py':
            analysis = self._parse_python(path, content)
        elif path.suffix == '.js':
            analysis = self._parse_javascript(path, content)
        elif path.suffix == '.html':
            analysis = self._parse_html(path, content)
        else:
            analysis = self._parse_css(path, content)
            
        self.files[str(path.relative_to(self.root))] = analysis
    
    def _parse_python(self, path: Path, content: str) -> FileArchitecture:
        tree = ast.parse(content)
        
        imports = []
        exports = []
        interfaces = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend([alias.name for alias in node.names])
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.extend([f"{module}.{alias.name}" for alias in node.names])
            elif isinstance(node, ast.ClassDef):
                exports.append(node.name)
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                interfaces.append({"type": "class", "name": node.name, "methods": methods})
            elif isinstance(node, ast.FunctionDef):
                exports.append(node.name)
                interfaces.append({
                    "type": "function", 
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args]
                })
        
        return FileArchitecture(
            path=str(path),
            file_type="python",
            lines_of_code=len(content.splitlines()),
            imports=imports,
            exports=exports,
            dependencies=[],  # Filled in second pass
            dependents=[],
            purpose_summary=self._extract_purpose(tree, content),
            complexity_score=self._calc_complexity(tree),
            interfaces=interfaces,
            data_flows=self._trace_data_flow(tree),
            key_patterns=self._detect_patterns(tree)
        )
    
    def _extract_purpose(self, tree, content) -> str:
        """Extract docstring or generate purpose from structure"""
        docstring = ast.get_docstring(tree)
        if docstring:
            return docstring[:200]
        # Fallback: analyze class/function names to infer purpose
        return "Inferred: " + self._infer_from_structure(tree)
    
    def _build_dependency_graph(self):
        """Map which files import/depend on which"""
        for file_path, arch in self.files.items():
            # Resolve imports to local files
            for imp in arch.imports:
                # Map import to actual file path
                resolved = self._resolve_import_to_file(imp, file_path)
                if resolved:
                    arch.dependencies.append(resolved)
                    self.files[resolved].dependents.append(file_path)