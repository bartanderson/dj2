# tools/analysis/truth/query_ast.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union, Any

## 2.2 SELECT NODE

@dataclass(frozen=True)
class Select:
    view: str          # STRUCTURE | STABILITY | INTEGRITY | SUMMARY | SUBSYSTEM
    metric: Optional[str] = None  # optional projection field

## 2.3 FILTER NODE

@dataclass(frozen=True)
class Filter:
    key: str
    op: str
    value: Any

# Examples:

# module == "tools.analysis"
# edge_count > 10
# contract == "graph_builder_deterministic_output"

## 2.4 COMBINATION NODE

@dataclass(frozen=True)
class Combine:
    left: "Query"
    right: "Query"


## 2.5 FULL QUERY NODE
Query = Union[Select, Filter, Combine]