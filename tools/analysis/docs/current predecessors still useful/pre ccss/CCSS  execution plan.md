STATUS NOTE (added 2026-06-17, Pass 2 read-only audit): this was actually
built. `tools/analysis/ccss - redesign into tool over analysis db/`
contains a real PASS1/PASS2/PASS3 implementation matching this plan's
identity model and pass boundaries. But PASS2 enrichment and PASS3 gap
detection are structural stubs only - no real semantic role/confidence
classification, `gaps` is hardcoded empty - and it's not wired into the
main pipeline. See TRACKER.md item 15 for the full finding and the open
decision (finish / integrate / shelve).

Current execution plan (locked state)

We proceed with CCSS in minimal viable form:

Phase 1 — Static grounding (no execution complexity yet)

We will implement only:

1. ContractAxis registry (manual seed from current code)
runtime_binding
identity_resolution
classification
routing
persistence (optional, if already present in tests)

This is just a list at first. No intelligence.

2. Test → Signal extraction (light parser)

We scan tests and extract only:

test name
referenced symbols
obvious contract axis tags (via heuristics: filename + assertion content)

No AST overengineering yet.

3. Signal → Axis mapping (deterministic rules only)

Examples:

test_runtime_* → runtime_binding
classify_* → classification
route_* or route_type assertions → routing

This is intentionally crude at first.

4. Coverage table (the first useful output)

We produce:

Axis → [tests]
Axis → [symbols covered]
Axis → [missing coverage flags]

That’s the first real deliverable.

Phase 2 — only after Phase 1 is useful

We refine:

AST signal extraction
better symbol linking
contract-aware grouping
duplication detection

But NOT yet.

Hard guardrail (keeps this from becoming another system)

We enforce:

If it does not improve “coverage visibility”, it is not allowed in Phase 1.

That blocks:

AI inference
semantic expansion
architecture modeling
test generation
abstraction creep
What I will do next (when you’re ready)

When you say go, I’ll help you implement:

ccss/scan_tests.py
extracts raw test signals
ccss/map_axes.py
assigns contract axis labels
ccss/coverage_report.py
prints a simple matrix
What you should NOT worry about yet

Ignore for now:

correctness perfection
semantic precision
full AST coverage
edge cases

We are building a radar, not a compiler.

Key stability point

You are now operating under a stable invariant:

The system cannot become larger than what the tests already reveal.

That is what prevents the “monster system” problem you were worried about.