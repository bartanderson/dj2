from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProjectGraphContext:

    project_prefixes: list[str] = field(default_factory=list)

    project_symbols: set[str] = field(default_factory=set)

    runtime_bindings: dict[str, str] = field(default_factory=dict)