TRUTH KERNEL v1 — MINIMAL IMPLEMENTATION DESIGN
Core idea (single sentence)

Convert questions into a small, closed query algebra, execute it deterministically, and never allow AI or heuristics to invent structure beyond that algebra.

1. SYSTEM SHAPE (DO NOT SKIP THIS)

You are building exactly 4 things:

1. Query AST (structure)
2. Query Validator (rules)
3. Query Executor (deterministic runtime)
4. Query Compiler (AI-only component)

Everything else is derived.

2. LAYERED DESIGN (BUILD ORDER)
🔹 LAYER 1 — QUERY PRIMITIVES (LOCK THIS FIRST)
Goal:

Define the entire language surface area

You already mostly have this:
AST Nodes (current state is good)
Select(view, metric?)
Filter(key, op, value)
Combine(left, right)
✔ KEEP THIS EXACT
Minimal addition (ONLY if needed later):

No expansion yet.

CHECKPOINT 1

You are done when:

AST can represent ALL existing test queries
No new node types required
3. LAYER 2 — QUERY VALIDATION (THIS IS THE REAL CORE)

This is where your system becomes deterministic.

RULE: EVERYTHING MUST PASS THIS CHECK
Input:

AST

Output:

VALID / INVALID + reason

VALIDATION RULES (STRICT BUT SMALL)
3.1 View legality

Only:

STRUCTURE
STABILITY
INTEGRITY
SUMMARY
SUBSYSTEM
3.2 Metric legality

Must match:

QueryPlan.VALID_METRICS[view]
3.3 Combine legality (VERY IMPORTANT)

Only allowed pairs:

(STRUCTURE, STABILITY)
(STRUCTURE, INTEGRITY)
(SUMMARY, STABILITY)
(SUBSYSTEM, STRUCTURE)
3.4 Filter legality

Filters must be:

key ∈ allowed_keys(view)

NO guessing. NO fallback logic.

CHECKPOINT 2

You are done when:

invalid combine → hard fail
invalid metric → hard fail
invalid filter → hard fail
4. LAYER 3 — QUERY EXECUTOR (YOU ARE CLOSE HERE)
Goal:

Execute AST into deterministic output

RULES:
Select node:
return view[metric] OR full view
Filter node:

NO mutation

Just wraps:

(FilterResult)
Combine node:

STRICT STRUCTURAL JOIN ONLY

NO semantic merging

return { left: resultA, right: resultB }
IMPORTANT RULE

Combine does NOT:

merge meaning
infer relationships
rewrite data

It is purely structural.

CHECKPOINT 3

You are done when:

same query always produces identical JSON
no hidden sorting randomness
no interpretation logic exists here
5. LAYER 4 — QUERY COMPILER (AI SURFACE ONLY)

This is the ONLY place AI is allowed.

INPUT:

Natural language

OUTPUT:

AST only

RULES (EXTREMELY IMPORTANT)

AI is ONLY allowed to produce:

Select
STRUCTURE
INTEGRITY
STABILITY
SUMMARY
SUBSYSTEM
Combine

ONLY from registry

Filter

ONLY allowed keys per view

NO ALLOWED BEHAVIOR:
no expansion
no synonym injection
no "semantic interpretation"
no guessing new views
no runtime discovery
EXAMPLE

User:

what depends on resolve_analysis_db_path

Compiler outputs:

Combine(
    Select(STRUCTURE),
    Select(INTEGRITY),
    Filter(key="symbol", op="==", value="resolve_analysis_db_path")
)
CHECKPOINT 4

You are done when:

compiler NEVER invents structure
compiler always outputs valid AST
executor does NOT depend on NLP
6. LAYER 5 — VIEW FUNCTIONS (YOU ARE MOSTLY DONE)

These are already correct in your code:

KEEP:
build_structure_view
build_stability_view
build_integrity_view
build_subsystem_view
RULE:

Views must never call other views

They are pure transforms of DB / graph

7. MINIMAL SYSTEM FLOW

This is your runtime:

USER QUESTION
    ↓
QUERY COMPILER (AI)
    ↓
AST
    ↓
VALIDATOR
    ↓
EXECUTOR
    ↓
RESULT OBJECT
    ↓
NARRATOR (optional)
8. WHAT YOU SHOULD BUILD FIRST (IMPORTANT ORDER)

Do NOT build everything at once.

PHASE 1 (HIGHEST VALUE)

✔ Lock validation rules
✔ Lock combine rules
✔ Ensure executor is deterministic

PHASE 2

✔ Hard-test AST coverage
✔ Confirm no missing node types

PHASE 3

✔ Replace any ad-hoc graph inspection paths (you already mostly did)

PHASE 4

✔ Connect compiler safely (last step, not first)

9. WHAT YOU DO NOT NEED YET (IMPORTANT)

DO NOT BUILD:

❌ adaptive query expansion
❌ semantic scoring layer
❌ ML ranking of symbols
❌ heuristic hotspot inference changes
❌ "AI reasoning over graph"

These break determinism.

10. YOUR CURRENT SYSTEM STATUS (honest assessment)

UPDATED 2026-06-16 — re-checked against actual current code, not memory:

Layer   Status
AST ✔ stable
Executor    ✔ stable
Planner/Validator   ✔ stable — was "partially strict", now backed by a
    real 25+ test suite (truth/tests/test_query_algebra.py) covering
    valid/invalid Combine pairs, metrics, and filter keys
Compiler    ✔ implemented — was "leaking semantics" (rule-based stub),
    now a real local-LLM call (Ollama llama3.2:3b) validated through
    QueryPlanner with deterministic rule-based fallback on any failure
    (truth/query_compiler.py). UPDATE 2026-06-16 (later same day): now
    exercised end-to-end against real views via Assessor.ask() /
    tools/analysis/ask.py, run successfully against the live project DB.
Views   ✔ all 5 wired — UPDATE 2026-06-16 (later same day): STRUCTURE/
    STABILITY/INTEGRITY were already wired to real project data via
    assessor.py; SUMMARY and SUBSYSTEM are now wired too, via
    Assessor.summary_view()/subsystem_view(), with direct regression
    coverage against real seeded data in
    tests/regression/test_run_algebra_end_to_end.py. No stub-only views
    remain. Full breakdown in Truth.md Phase 1 findings (now resolved).
11. KEY INSIGHT (THIS IS THE BREAKTHROUGH)

You are not building "analysis".

You are building:

a closed symbolic query machine over program structure

That means:

queries must be enumerable
execution must be deterministic
AI is only a translator, not a thinker
12. VERY SMALL NEXT STEP (DO THIS NEXT)

If you want a clean next move with minimal risk:

Step 1:

Tighten validator (especially Combine)

Step 2:

Write 10–20 test queries in Truth Harness

Step 3:

Lock expected AST outputs

If you want, next I can help you:

👉 convert this into a real test matrix

so you can instantly see:

what the system supports
what it rejects
what will break future changes

That will give you your "thousand errors" safety net without adding complexity.
