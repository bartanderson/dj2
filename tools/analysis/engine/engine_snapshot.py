# tools/analysis/engine/engine_snapshot.py

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class EngineSnapshot:
    ingestion: Any
    graph: Any
    facts: Any
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]


class EngineSnapshotBuilder:

    def build(self, ingestion, graph, facts) -> EngineSnapshot:

        edge_count = graph["edge_count"]

        metrics = {
            "file_count": facts["file_count"],
            "symbol_ref_count": facts["symbol_ref_count"],
            "edge_count": edge_count,
        }

        return EngineSnapshot(
            ingestion=ingestion,
            graph=graph,
            facts=facts,
            metrics=metrics,
            metadata={},
        )