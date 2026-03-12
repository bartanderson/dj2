from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path

@dataclass
class FileArchitecture:
    path: str
    file_type: str
    lines_of_code: int = 0
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    purpose_summary: str = ""
    complexity_score: int = 0
    interfaces: List[Dict] = field(default_factory=list)
    data_flows: List[Dict] = field(default_factory=list)
    key_patterns: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'path': self.path,
            'file_type': self.file_type,
            'lines_of_code': self.lines_of_code,
            'imports': self.imports,
            'exports': self.exports[:10] if len(self.exports) > 10 else self.exports,  # Limit exports
            'dependencies_count': len(self.dependencies),
            'dependents_count': len(self.dependents),
            'purpose_summary': self.purpose_summary[:150] if self.purpose_summary else "",
            'complexity_score': self.complexity_score,
            'interfaces': self.interfaces[:5],  # Top 5 interfaces only
            'key_patterns': self.key_patterns
        }

@dataclass
class ModuleView:
    name: str
    files: List[str]
    responsibility: str = ""
    public_api: List[Dict] = field(default_factory=list)
    inbound_connections: List[str] = field(default_factory=list)
    outbound_connections: List[str] = field(default_factory=list)
    
@dataclass
class SystemView:
    total_files: int
    modules: Dict[str, List[str]]
    entry_points: List[str]
    data_stores: List[str]
    external_deps: List[str]
    architecture_pattern: str