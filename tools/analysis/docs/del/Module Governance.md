MODULE NAME:
TYPE: (Ownership / Orchestration)

OWNS:
- what data or truth it is responsible for

DOES NOT OWN:
- what it is forbidden to touch or compute

INPUTS:
- what it receives

OUTPUTS (CONTRACT):
- what it guarantees it produces

INVARIANTS:
- rules that must always be true

MATURITY:
- EXPERIMENTAL / EVOLVING / STABLE / FROZEN
---------------------------------------------------
I’ll do 4 module cards based on what you’ve been building:

snapshot
classifier
metrics
reducer / validation
---------------------------------------------------
🧱 1. SNAPSHOT MODULE CARD
MODULE NAME: build_evaluation_snapshot
TYPE: Ownership

OWNS:
- graph structure interpretation (nodes + edges)
- per-edge structural signal extraction
- graph-derived insights (degree, fanout)
- raw per-file structural representation

DOES NOT OWN:
- bucket classification logic
- global aggregation across files
- metric computation (ratios, totals)
- cross-file reduction logic

INPUTS:
- analysis object (raw file-level analysis)
- graph (edge list / structure)

OUTPUTS (CONTRACT):
- edge_count
- bucket_summary (already aggregated per-file only)
- graph_insights (top nodes, degree metrics)
- structural_signals (high fanout, etc.)
- failure_breakdown (optional raw passthrough)

INVARIANTS:
- edge_count must equal len(graph.edges)
- snapshot must NOT compute global metrics across files
- snapshot must not aggregate across pipeline runs
- bucket_summary must only reflect per-edge classification

MATURITY:
- STABLE
🧱 2. CLASSIFIER MODULE CARD
MODULE NAME: classify_symbol / classify_edge
TYPE: Ownership

OWNS:
- assigning semantic bucket labels to edges/symbols
- mapping raw symbols → bucket categories

DOES NOT OWN:
- counting buckets
- aggregating results
- graph analysis
- metrics computation

INPUTS:
- edge symbol (callee/caller or identifier)
- route/context hints
- project prefixes (optional)

OUTPUTS (CONTRACT):
- single bucket label:
  - project
  - builtin
  - classification_gap (normalized unknowns)

INVARIANTS:
- must return exactly ONE bucket per input
- must NOT aggregate across edges
- must NOT store state
- must be deterministic for same input

MATURITY:
- EVOLVING
🧱 3. METRICS MODULE CARD
MODULE NAME: extract_metrics
TYPE: Orchestration

OWNS:
- aggregation across snapshots
- computation of totals and ratios
- global metrics derivation

DOES NOT OWN:
- classification decisions
- graph structure
- per-file snapshot construction

INPUTS:
- list of snapshots

OUTPUTS (CONTRACT):
- total_edges
- bucket_totals:
  - project
  - builtin
  - classification_gap
- failure_breakdown (aggregated)
- unknown_samples (sampled raw cases)

INVARIANTS:
- sum(bucket_totals) == total_edges
- must be pure aggregation (no classification)
- must not depend on graph internals
- must not mutate snapshot structure

MATURITY:
- EVOLVING
🧱 4. REDUCER / VALIDATION MODULE CARD
MODULE NAME: pipeline reducer / validation layer
TYPE: Orchestration

OWNS:
- cross-snapshot consistency validation
- invariant checking across pipeline stages
- final integrity verification

DOES NOT OWN:
- classification
- metrics computation
- snapshot construction

INPUTS:
- snapshots
- metrics output

OUTPUTS (CONTRACT):
- validation results
- invariant checks
- reconciliation logs

INVARIANTS:
- must NOT modify data
- must only assert / report
- must not introduce new computed truth
- must only verify existing truth

MATURITY:
- STABLE