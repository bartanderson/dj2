ONE canonical classification entry point for ALL symbols

SINGLE-PIPELINE EXECUTION MODEL

Not “C3 rules in isolation”, but:

one symbol → one deterministic path through all layers → one final classification

🔥 What “single pipeline through all layers” actually means

For every symbol, the system must go through this exact ordered chain:

1. Normalize input
2. Route decision (project / builtin / stdlib / runtime / external / unknown)
3. Hard overrides (builtin / stdlib / runtime)
4. Project matching (ONLY via explicit evidence)
5. External resolution (qualified / alias / import)
6. Final fallback → classification_gap
7. Emit result (NO re-entry, NO secondary promotion)


✔ C3 COMPLETION CRITERION (VALID FORM)
	Enforce strict type boundaries
C3 is DONE when ALL are true:

1. Stability condition
[]	classification_gap does NOT spike unexpectedly across runs
2. Test determinism
[]	test_* → project always
[]	main, Path, HybridPhaseAuditor always stable classification
3. Leakage constraint
[]	runtime symbols never appear as project
[]	project symbols never fall into runtime/builtin/stdlib
4. Route authority correctness
[]	builtin / stdlib / runtime are hard return paths
[]	external never enters project unless explicitly matched
[]	unknown never shortcuts classification
5. Determinism invariant
[]	identical inputs → identical outputs
[]	no dependence on print/debug/order/graph state

C3 = 3-layer classifier:
Layer 1 — Hard gates (must return immediately)
- builtin
- stdlib
- runtime
Layer 2 — Verified project resolution
- project_symbols
- prefixes
- module/leaf match
Layer 3 — fallback classification
- external_lib.*
- unresolved_qualified_reference
- classification_gap (last resort only)

C3 Rules (this is what we are actually enforcing)
1. Output validity constraint

classify_symbol(...) must return ONLY:

project
builtin
stdlib
runtime
external_lib.*
external_unknown
unresolved_qualified_reference
classification_gap (ONLY if truly unknown)
2. No accidental fallback inflation

A symbol is ONLY classification_gap if:

it is not in project_symbols
AND not builtin
AND not stdlib
AND not runtime-bound
AND not qualified external match
3. Route authority hierarchy (IMPORTANT)

Route is authoritative ONLY in this order:

"project" → may return project if verified
"builtin" / "stdlib" / "runtime" → hard return
"external" → only external bucket allowed
"unknown" → full classification logic applies
4. No “silent promotion”

A symbol must NOT become:

project
builtin
stdlib

unless explicitly matched via:

project_symbols
BUILTINS
STDLIB_PREFIXES
runtime_bindings (if used downstream)
5. Classification determinism rule

Given same inputs:

classify_symbol must ALWAYS return same output

No dependence on:

print debugging
execution order artifacts
incidental graph state
-------------------------------------
D — Graph Consistency Layer

Concern:

“Is the graph structurally meaningful?”

Focus:

node ranking
degree stability
fanout detection
noise suppression (print, main, etc.)
E — System Integration Layer

Concern:

“Does the pipeline behave consistently end-to-end?”

Focus:

ingestion → classification → persistence → snapshot
regression detection
test validation
cross-file consistency