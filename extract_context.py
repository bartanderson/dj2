
#!/usr/bin/env python3
"""
DJ2 Context Extractor - Layered Architecture Analysis
Produces persistent, queryable context for world/character generation integration
"""

import json
import ast
import re
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
import sys

@dataclass
class InterfacePoint:
    """A connection between two components"""
    source: str
    target: str
    mechanism: str  # import, api_call, data_flow, template_include
    context: str
    files_involved: List[str]
    impedance_notes: str = ""  # Where friction exists

@dataclass
class ComponentCapsule:
    """Layer 2: Detailed component analysis"""
    name: str
    folder: str
    path: str
    type: str  # generator, service, data_source, interface, template
    responsibilities: List[str]
    key_exports: List[str]
    dependencies: List[str]  # Other components it uses
    dnd_character_touches: List[str]  # What it uses from old system
    og_system_counterparts: List[str]  # Potential replacements
    complexity_score: int
    implementation_status: str  # working, partial, broken, planned
    notes: str

@dataclass  
class SystemMap:
    """Layer 1: High-level system overview"""
    project_root: str
    total_files: int
    components: Dict[str, str]  # name -> brief description
    data_flows: List[str]  # brief descriptions of major flows
    integration_hotspots: List[str]  # Where og_system meets dj2
    current_blockers: List[str]

class DJ2ContextExtractor:
    def __init__(self, dj2_root: str, og_system_root: Optional[str] = None):
        self.dj2 = Path(dj2_root).resolve()
        self.og = Path(og_system_root).resolve() if og_system_root else None
        
        self.target_folders = ['world', 'core', 'ai', 'templates', 'routes', 'engine']
        self.system_map = None
        self.capsules: Dict[str, ComponentCapsule] = {}
        self.interfaces: List[InterfacePoint] = []
        
    def extract_all(self):
        """Run full extraction"""
        print(f"Extracting context from: {self.dj2}")
        if self.og:
            print(f"Reference system: {self.og}")
        
        self._extract_layer1_system_map()
        self._extract_layer2_capsules()
        self._extract_layer3_interfaces()
        
        return self
    
    def _extract_layer1_system_map(self):
        """Create high-level system overview"""
        components = {}
        
        for folder in self.target_folders:
            folder_path = self.dj2 / folder
            if not folder_path.exists():
                continue
                
            # Quick characterization
            py_files = list(folder_path.rglob("*.py"))
            html_files = list(folder_path.rglob("*.html"))
            
            if folder == "world":
                desc = f"World generation ({len(py_files)} py, {len(html_files)} templates)"
            elif folder == "core":
                desc = f"Core systems/data ({len(py_files)} modules)"
            elif folder == "ai":
                desc = f"AI/decision engines ({len(py_files)} modules)"
            elif folder == "templates":
                desc = f"UI templates ({len(html_files)} html, {len(py_files)} py)"
            elif folder == "routes":
                desc = f"Web routes/API ({len(py_files)} endpoints)"
            elif folder == "engine":
                desc = f"Game engine mechanics ({len(py_files)} modules)"
            else:
                desc = f"{len(py_files)} python files"
            
            components[folder] = desc
        
        # Identify data flows
        flows = [
            "world generation -> entity placement",
            "character creation -> stat generation", 
            "encounter -> combat resolution",
            "player action -> skill check -> outcome"
        ]
        
        # Find dnd_character imports (current blockers)
        blockers = self._find_dnd_character_usage()
        
        self.system_map = SystemMap(
            project_root=str(self.dj2),
            total_files=sum(len(list((self.dj2 / f).rglob("*"))) 
                          for f in self.target_folders 
                          if (self.dj2 / f).exists()),
            components=components,
            data_flows=flows,
            integration_hotspots=[
                "character generation: dnd_character -> og_system entities",
                "monster stats: hardcoded -> og_system bestiary",
                "item data: scattered -> og_system equipment"
            ],
            current_blockers=blockers[:5]  # Top 5 blockers
        )
        
        print(f"  Layer 1: System map with {len(components)} components")
    
    def _find_dnd_character_usage(self) -> List[str]:
        """Find where old dnd_character system is still used"""
        blockers = []
        
        for folder in self.target_folders:
            folder_path = self.dj2 / folder
            if not folder_path.exists():
                continue
                
            for py_file in folder_path.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    if "dnd_character" in content or "from dnd" in content:
                        rel_path = str(py_file.relative_to(self.dj2))
                        # Find specific imports
                        imports = re.findall(r"(from dnd.*?import.*?)$", content, re.MULTILINE)
                        for imp in imports[:2]:  # First 2 imports
                            blockers.append(f"{rel_path}: {imp.strip()}")
                except:
                    continue
        
        return blockers
    
    def _extract_layer2_capsules(self):
        """Create detailed component capsules"""
        
        for folder in self.target_folders:
            folder_path = self.dj2 / folder
            if not folder_path.exists():
                continue
            
            for py_file in folder_path.rglob("*.py"):
                self._analyze_file_capsule(py_file, folder)
        
        print(f"  Layer 2: {len(self.capsules)} component capsules")
    
    def _analyze_file_capsule(self, file_path: Path, folder: str):
        """Analyze single file into capsule"""
        rel_path = str(file_path.relative_to(self.dj2))
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except:
            return
        
        # Parse Python structure
        try:
            tree = ast.parse(content)
        except:
            tree = None
        
        # Extract exports
        exports = []
        responsibilities = []
        if tree:
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    exports.append(f"func:{node.name}")
                    if node.name.startswith("generate") or node.name.startswith("create"):
                        responsibilities.append(f"generates {node.name.replace('generate_', '')}")
                elif isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    exports.append(f"class:{node.name}({len(methods)} methods)")
                    responsibilities.append(f"manages {node.name.lower()} state")
        
        # Find dependencies
        deps = []
        dnd_touches = []
        
        # Check imports
        import_pattern = r"^from\s+(\S+)\s+import|^import\s+(\S+)"
        for line in content.split("\\n"):
            match = re.match(import_pattern, line.strip())
            if match:
                module = match.group(1) or match.group(2)
                if module and not module.startswith("."):
                    if any(target in module for target in self.target_folders):
                        deps.append(module.split(".")[0])
                    if "dnd" in module.lower():
                        dnd_touches.append(line.strip())
        
        # Determine type and status
        name = file_path.stem
        if "test" in name:
            comp_type = "test"
            status = "unknown"
        elif folder == "templates":
            comp_type = "template"
            status = "working" if "htmx" in content else "needs_update"
        elif "generate" in name or "create" in name:
            comp_type = "generator"
            status = "partial" if dnd_touches else "working"
        elif "model" in name or "data" in name:
            comp_type = "data_source"
            status = "broken" if dnd_touches else "working"
        else:
            comp_type = "service"
            status = "unknown"
        
        # Find og_system counterparts
        og_matches = []
        if self.og:
            for og_file in self.og.rglob("*.json"):
                if name.replace("_", "") in og_file.stem.lower():
                    og_matches.append(str(og_file.relative_to(self.og)))
        
        capsule = ComponentCapsule(
            name=name,
            folder=folder,
            path=rel_path,
            type=comp_type,
            responsibilities=responsibilities[:3],
            key_exports=exports[:5],
            dependencies=list(set(deps)),
            dnd_character_touches=dnd_touches[:3],
            og_system_counterparts=og_matches[:3],
            complexity_score=len(content.splitlines()),
            implementation_status=status,
            notes=self._generate_notes(name, folder, dnd_touches, og_matches)
        )
        
        self.capsules[rel_path] = capsule
    
    def _generate_notes(self, name: str, folder: str, dnd_touches: List[str], og_matches: List[str]) -> str:
        """Generate contextual notes"""
        notes = []
        
        if dnd_touches:
            notes.append(f"BLOCKED: Uses dnd_character ({len(dnd_touches)} references)")
        
        if og_matches:
            notes.append(f"REPLACEMENT READY: {len(og_matches)} og_system equivalents found")
        elif dnd_touches:
            notes.append("NO REPLACEMENT: Needs og_system adapter built")
        
        if folder == "world" and "character" in name:
            notes.append("CRITICAL PATH: Character generation integration point")
        
        return "; ".join(notes) if notes else "Standard component"
    
    def _extract_layer3_interfaces(self):
        """Extract specific integration interfaces"""
        
        # Find world <-> character generation interface
        world_caps = [c for c in self.capsules.values() if c.folder == "world"]
        core_caps = [c for c in self.capsules.values() if c.folder == "core"]
        
        # Character generation interface
        char_gens = [c for c in world_caps if "character" in c.name or "char" in c.name]
        for cap in char_gens:
            self.interfaces.append(InterfacePoint(
                source_system=f"world/{cap.name}",
                target="og_system/entities/character",
                mechanism="data_replacement",
                context="Character stat generation",
                files_involved=[cap.path],
                impedance_notes="dnd_character uses different stat array than og_system" if cap.dnd_character_touches else "Ready for integration"
            ))
        
        # Template rendering interfaces
        templates_path = self.dj2 / "templates"
        if templates_path.exists():
            for html_file in templates_path.rglob("*.html"):
                content = html_file.read_text(encoding="utf-8", errors="ignore")
                if "character" in content.lower():
                    self.interfaces.append(InterfacePoint(
                        source_system=f"templates/{html_file.name}",
                        target="world/character_generator",
                        mechanism="template_data_binding",
                        context="Character sheet rendering",
                        files_involved=[str(html_file.relative_to(self.dj2))],
                        impedance_notes="Expects dnd_character object structure" if "dnd" in content.lower() else "May need field name updates"
                    ))
        
        print(f"  Layer 3: {len(self.interfaces)} integration interfaces")
    
    def save(self, output_dir: str = "context_layers"):
        """Save all three layers to JSON"""
        out_path = Path(output_dir)
        out_path.mkdir(exist_ok=True)
        
        # Layer 1: System Map
        with open(out_path / "layer1_system_map.json", "w") as f:
            json.dump(asdict(self.system_map), f, indent=2)
        
        # Layer 2: Component Capsules
        capsules_data = {k: asdict(v) for k, v in self.capsules.items()}
        with open(out_path / "layer2_capsules.json", "w") as f:
            json.dump(capsules_data, f, indent=2)
        
        # Layer 3: Interface Specifications
        interfaces_data = [asdict(i) for i in self.interfaces]
        with open(out_path / "layer3_interfaces.json", "w") as f:
            json.dump(interfaces_data, f, indent=2)
        
        # Summary report
        summary = {
            "extraction_timestamp": str(Path.cwd()),
            "layers": {
                "system_map": str(out_path / "layer1_system_map.json"),
                "capsules": str(out_path / "layer2_capsules.json"),
                "interfaces": str(out_path / "layer3_interfaces.json")
            },
            "statistics": {
                "total_components": len(self.capsules),
                "blocked_by_dnd": len([c for c in self.capsules.values() if c.dnd_character_touches]),
                "og_replacements_available": len([c for c in self.capsules.values() if c.og_system_counterparts]),
                "integration_points": len(self.interfaces)
            },
            "quick_access": {
                "critical_path_components": [
                    c.path for c in self.capsules.values()
                    if "character" in c.name and c.folder == "world"
                ],
                "ready_to_migrate": [
                    c.path for c in self.capsules.values()
                    if c.og_system_counterparts and not c.dnd_character_touches
                ],
                "needs_adapter": [
                    c.path for c in self.capsules.values()
                    if c.dnd_character_touches and not c.og_system_counterparts
                ]
            }
        }
        
        with open(out_path / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\\n💾 Context layers saved to: {out_path}/")
        print(f"   Summary: {summary['statistics']}")
        
        return summary

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract DJ2 architectural context")
    parser.add_argument("dj2_path", nargs="?", default=".", help="Path to dj2 folder (default: current directory)")
    parser.add_argument("--og", default="og_system", help="Path to og_system folder (default: og_system)")
    parser.add_argument("-o", "--output", default="out", help="Output directory (default: out)")
    
    args = parser.parse_args()
    
    extractor = DJ2ContextExtractor(args.dj2_path, args.og)
    extractor.extract_all()
    summary = extractor.save(args.output)
    
    print("\\nNext steps:")
    print("1. Review context_layers/summary.json for overview")
    print("2. Load specific capsules from layer2_capsules.json for component details")
    print("3. Check layer3_interfaces.json for integration points")

if __name__ == "__main__":
    main()