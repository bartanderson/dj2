🧭 THE RIGHT MODEL

Bart is not the passive code provider.

Bart is:

repository operator,
local executor,
architectural witness.

ChatGPT is:

structural assessor,
boundary analyst,
governance planner.

That division is actually efficient.
--------------
🎯 WHAT YOU NEED NOW

You need:

a permanent evaluation checklist,
a module classification workflow,
a maturity tracking system,
a governance insertion protocol.

This prevents:

session drift,
repeated reassessment,
contradictory architecture decisions.
--------------------------
DISCOVER
    →
CLASSIFY
    →
ASSESS OWNERSHIP
    →
DETERMINE MATURITY
    →
WRITE GOVERNANCE HEADER
    →
FREEZE OR MARK EVOLVING
--------------------------------
FIRST: Evaluate responsibility and ownership
------------------------------------
Phase 1 [x]

define contracts and ownership boundaries

snapshot owns edge truth
classifier owns bucket assignment
metrics owns aggregation
reducer owns validation
Phase 2 [ ]

enforce those boundaries in code

remove duplication
ensure single ownership per concept
Phase 3 [ ]

THEN add state persistence

because now state has something stable to record
Phase 4 [ ]

optional tooling (UI, replay, etc.)
---------------------------------------

🧱 Code layer
	produces snapshot
📦 Snapshot layer (per file)
	bucket_summary
	edge_count
📊 Metrics layer (global)
	gap_rate
	project_ratio
🧾 Registry layer (THIS JSON)
	collects snapshot + metrics + progress
	provides system-wide view

PROCESS LOOP
1. pick a file and say Lets evaluate [snapshot, metrics]
2. MODULE CARD CHECK ( only track one module at a time
	[SNAPSHOT, CLASSIFIER, METRICS, REDUCER])
	1. What does it OWN?
	2. What does it NOT own?
	3. What does it OUTPUT?
	4. What are its INVARIANTS?
	5. What is its MATURITY?
3. UPDATE CODE or LOCK IT?
	✔ “this is correct → lock it”
	✏️ “this is wrong → adjust code”
	🚫 “this is unclear → pause and clarify ownership”
4. ALIGN/UPDATE REGISTRY with whatever the case is

--------AI rules for recoverability/resync with new session--------
SYSTEM PURPOSE:
- Stabilize analysis pipeline into deterministic module-owned truth system.

NOTE: A module’s file list includes both:
	- owned implementation files
	- required dependency files
Dependency inclusion ≠ ownership.

Classifier defines labels, snapshot consumes them, metrics aggregates snapshot, reducer validates everything.
-----------------------------
CORE MODULES: 
- snapshot → edge extraction + classification
	evaluation_snapshot.py OWNED
	semantic_roles.py (supporting)
	symbol_classifier.py (called dependency)

- classifier → symbol → bucket assignment
	symbol_classifier.py OWNED
	semantic_roles.py OWNED

- metrics → aggregation of snapshot outputs
	extract_metrics.py OWNED

- reducer → validation + invariants
	run_analysis_pipeline.py OWNED (EMBEDDED / ORCHESTRATION RESIDUE)

SUPPORT:
	build_context_bundle.py

SPEC:
	contract_types.py

REGISTRY: human-readable system view
	analysis_state.json

------------------------------
CORE RULES:
- code = truth
- registry = view of truth
- contracts = ownership boundaries
- invariants = must never break
- no module owns more than one responsibility

WORKFLOW:
process → snapshot → metrics → validate → record registry (manual)
