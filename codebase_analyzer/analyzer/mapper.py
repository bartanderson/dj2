import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
from .models import FileArchitecture
from .parsers import get_parser

class ArchitectureMapper:
    def __init__(self, root_path: str):
        self.root = Path(root_path).resolve()
        self.files: Dict[str, FileArchitecture] = {}
        self.module_graph: Dict[str, List[str]] = defaultdict(list)
        
    def analyze_all(self, include_patterns: List[str] = None, exclude_dirs: List[str] = None):
        """
        Main entry point for Phase 1 analysis
        
        Args:
            include_patterns: File extensions to include (e.g., ['.py', '.js'])
            exclude_dirs: Directory names to skip (e.g., ['node_modules', '__pycache__'])
        """
        include_patterns = include_patterns or ['.py', '.js', '.html', '.css', '.jsx', '.ts']
        exclude_dirs = set(exclude_dirs or ['node_modules', '__pycache__', '.git', 'venv', 'env'])
        
        print(f"🔍 Scanning {self.root}...")
        
        for file_path in self.root.rglob("*"):
            if file_path.is_dir():
                continue
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            if file_path.suffix not in include_patterns:
                continue
                
            self._analyze_file(file_path)
        
        print(f"📊 Analyzed {len(self.files)} files")
        
        # Second pass: resolve dependencies
        self._build_dependency_graph()
        
        # Third pass: identify modules
        self._identify_modules()
        
        return self
    
    def _analyze_file(self, path: Path):
        """Analyze single file"""
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"⚠️  Could not read {path}: {e}")
            return
            
        parser = get_parser(path.suffix)
        if not parser:
            return
            
        try:
            analysis = parser.parse(path, content)
            relative_path = str(path.relative_to(self.root))
            self.files[relative_path] = analysis
        except Exception as e:
            print(f"⚠️  Error parsing {path}: {e}")
    
    def _build_dependency_graph(self):
        """Map file-to-file dependencies"""
        print("🔗 Building dependency graph...")
        
        # Create lookup from import paths to files
        file_lookup = {}
        for path in self.files.keys():
            file_lookup[Path(path).stem] = path
            file_lookup[path.replace('/', '.').replace('\\', '.')] = path
        
        for file_path, arch in self.files.items():
            for imp in arch.imports:
                # Try to resolve import to local file
                resolved = self._resolve_import(imp, file_path, file_lookup)
                if resolved and resolved in self.files:
                    arch.dependencies.append(resolved)
                    self.files[resolved].dependents.append(file_path)
    
    def _resolve_import(self, imp: str, current_file: str, lookup: Dict) -> Optional[str]:
        """Resolve import string to file path"""
        # Handle relative imports
        if imp.startswith('.'):
            current_dir = Path(current_file).parent
            parts = imp.split('/')
            try:
                resolved = current_dir.joinpath(*parts).resolve()
                # Try common extensions
                for ext in ['.js', '.ts', '.jsx', '.py', '/index.js']:
                    candidate = str(resolved.with_suffix(ext)) if not ext.startswith('/') else str(resolved) + ext
                    if candidate in self.files:
                        return candidate
            except:
                pass
        
        # Handle absolute imports by matching stems
        stem = imp.split('/')[-1].split('.')[0]
        if stem in lookup:
            return lookup[stem]
        
        return None
    
    def _identify_modules(self):
        """Group files into logical modules based on directory structure"""
        modules = defaultdict(list)
        for path in self.files.keys():
            parts = Path(path).parts
            if len(parts) > 1:
                module = parts[0]
            else:
                module = "root"
            modules[module].append(path)
        
        self.module_graph = dict(modules)
        print(f"📦 Identified {len(modules)} modules: {list(modules.keys())}")
    
    def save(self, output_path: str):
        """Save analysis to JSON"""
        output = {
            "metadata": {
                "root_path": str(self.root),
                "total_files": len(self.files),
                "modules": self.module_graph
            },
            "files": {k: v.to_dict() for k, v in self.files.items()}
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"💾 Saved analysis to {output_path}")
    
    def load(self, input_path: str):
        """Load previous analysis"""
        with open(input_path) as f:
            data = json.load(f)
        
        self.module_graph = data["metadata"]["modules"]
        # Reconstruct FileArchitecture objects
        for path, file_data in data["files"].items():
            self.files[path] = FileArchitecture(**file_data)
        
        return self