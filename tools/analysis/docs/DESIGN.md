tools/analysis - DESIGN (consolidated)
=======================================

This file consolidates the design/architecture docs that used to live as
separate files in tools/analysis/docs/. The originals are preserved in
docs/del/ for reference, not deleted, in case anything below was condensed
too aggressively:

- AGENT CAPABILITY LAYER v1.md
- TRUTH KERNEL v1.md
- truth query algebra.md
- contracts  + visibility.md
- Symbol Classification Stabilization Plan.md
- work flow.md

For live status, checklists, and the session-by-session history of what's
actually been built and verified, see TRACKER.md (consolidated from
REFACTOR OPS BOARD.md, Truth Kernel Board.md, Truth.md, todo-done.md - also
in docs/del/). This file is architecture/intent; TRACKER.md is "what's true
right now and how we got there." Per the working agreement in CLAUDE.md, new
accepted design decisions get implemented and then tracked in TRACKER.md -
this file should not turn into a 6th competing source of status truth.

Consolidated 2026-06-17.

---

## 1. Core philosophy (from work flow.md)

The database snapshots are just the substrate. What matters is that you can:

- Run the pipeline on any codebase (or subdirectory) to produce a .db
  snapshot.
- Query that snapshot to answer questions like "what functions are never
  called," "which modules have the most dependencies," "where are side
  effects happening."
- Use those answers to decide what to keep, discard, or refactor.
- Iterate on the tool (better indexing, smarter classification, richer
  contract extraction) knowing you have a repeatable way to measure
  improvement.

No cross-run manifests, timestamps, or decision tables were needed to get
started - those are polish. The core loop is: snapshot -> query -> reason ->
act. This is the philosophy everything else in this doc builds on.

---

## 2. Truth Kernel - query algebra design

This is the current, locked design for how natural-language questions get
turned into deterministic, structured answers. It originates from an
earlier exploratory draft (see "2.1 Earlier draft" below) and was tightened
into the spec actually implemented.

**Core idea, one sentence:** convert questions into a small, closed query
algebra, execute it deterministically, and never allow AI or heuristics to
invent structure beyond that algebra.

### System shape

Exactly 4 things, everything else derived:

1. Query AST (structure)
2. Query Validator (rules)
3. Query Executor (deterministic runtime)
4. Query Compiler (the only AI-facing component)

### Layer 1 - query primitives

AST nodes: `Select(view, metric?)`, `Filter(key, op, value)`, `Combine(left,
right)`. Keep this exact; no expansion unless a real gap forces it.

Checkpoint: the AST can represent all existing test queries, no new node
types required.

### Layer 2 - query validation (the real core)

Every AST must pass: VALID / INVALID + reason. Rules are strict but small:

- **View legality** - only registered views. (Originally STRUCTURE /
  STABILITY / INTEGRITY / SUMMARY / SUBSYSTEM; ROLE was added as a 6th view
  later - see TRACKER.md. This doc's examples below predate that addition
  and should be read as "5 views, now 6.")
- **Metric legality** - must match `QueryPlan.VALID_METRICS[view]`.
- **Combine legality** - only registered pairs are allowed, e.g.
  `(STRUCTURE, STABILITY)`, `(STRUCTURE, INTEGRITY)`, `(SUMMARY, STABILITY)`,
  `(SUBSYSTEM, STRUCTURE)`. No guessing, no fallback logic.
- **Filter legality** - filter keys must be in `allowed_keys(view)`.

Checkpoint: invalid combine, invalid metric, and invalid filter all hard-fail.

### Layer 3 - query executor

Executes a validated AST into deterministic output:

- `Select` returns `view[metric]` or the full view.
- `Filter` wraps a `FilterResult`, no mutation.
- `Combine` is a strict structural join only - `{left: resultA, right:
  resultB}`. It does NOT merge meaning, infer relationships, or rewrite
  data.

Checkpoint: the same query always produces identical JSON, no hidden
sorting randomness, no interpretation logic in this layer.

### Layer 4 - query compiler (the only AI surface)

Input: natural language. Output: AST only. The compiler may only produce
`Select`/`Combine`/`Filter` nodes built from the registry - no expansion, no
synonym injection, no "semantic interpretation," no guessing new views, no
runtime discovery.

Example: "what depends on resolve_analysis_db_path" compiles to
`Combine(Select(STRUCTURE), Select(INTEGRITY), Filter(key="symbol",
op="==", value="resolve_analysis_db_path"))`.

Checkpoint: the compiler never invents structure, always outputs a valid
AST, and the executor never depends on NLP.

### Layer 5 - view functions

`build_structure_view`, `build_stability_view`, `build_integrity_view`,
`build_subsystem_view` (plus `build_role_view`, added later). Views must
never call other views - they are pure transforms of DB/graph data.

### Full runtime flow

```
USER QUESTION
    -> QUERY COMPILER (AI)
    -> AST
    -> VALIDATOR
    -> EXECUTOR
    -> RESULT OBJECT
    -> NARRATOR (optional)
```

### Build order (as originally planned)

1. Lock validation rules and combine rules; make the executor deterministic.
2. Hard-test AST coverage; confirm no missing node types.
3. Replace ad-hoc graph inspection paths with the algebra.
4. Connect the compiler safely - last step, not first.

### Explicitly out of scope

No adaptive query expansion, no semantic scoring layer, no ML ranking of
symbols, no heuristic hotspot-inference changes, no "AI reasoning over the
graph." These would break determinism, which is the entire point of the
design: AI can only talk about truths that already exist in structured
form. The system is a closed-world reasoning substrate, not an open
reasoning system - combinations must be enumerated, views must be fixed,
filters must be constrained.

For the current build/test status of every layer above (AST, Executor,
Planner/Validator, Compiler, Views, and the 6th ROLE view added after this
spec was written), see TRACKER.md's Truth Kernel Tier Status section - it is
the authoritative "is this actually true today" answer, not this file.

### 2.1 Earlier draft (superseded, kept for historical context)

`truth query algebra.md` was the original sketch of this idea, written
before TRUTH KERNEL v1 above locked in the final shape. The reframe it
argued for - "you are not building a smart AI system or a reasoning graph,
you are building a verifiable system introspection engine with a
constrained query language; AI is only a query compiler and a narrator" -
is the same core idea carried into the spec above, just with different
layer names (it called the views STRUCTURE_VIEW/STABILITY_VIEW/
INTEGRITY_VIEW/SYSTEM_SUMMARY_VIEW instead of bare names, and proposed a
`truth_query_spec.py` file as the source of truth for legal
views/combinations/filters/aggregations). Nothing in it contradicts the
locked design above; it was superseded by it, not overruled. Kept here only
so the evolution of the idea isn't lost - the locked spec above is what to
build against.

---

## 3. Agent capability layer (live design proposal)

**Status:** design proposal, not yet a finished execution checklist.
Written 2026-06-17 to close out a design conversation that started from a
determinism-test fix and Bart's "the boundary is my memory" reframe - he
wants a capable software base enhanced with AI, not an AI that's trying to
be capable on its own. That's the same principle the Truth Kernel already
encodes ("not allowed to invent information"); this section is about
extending that same deterministic-core-plus-AI-narration shape outward to
cover the actual game code, not the analysis tool's own code.

The concrete trigger: Bart half-remembered a design decision ("potentials
that collapse at trigger time") and asked for it to be checked rather than
trusted from memory. It was found (world_controller.py's
potential_locations + generate_location_from_potential, world_map.py's
on-demand-generation comment, travel_system.py's EncounterPoint.activate()
+ generate_encounter()) along with a live gap: region_id is hardcoded None
at creation, so generate_location_from_potential always returns None right
now - wired but dead. That lookup-and-verify cycle is exactly the
capability being designed for here: how to make it repeatable without
re-grepping from scratch every time, and how to extend the same idea to
ripple/impact analysis.

### Four layers - status today vs. gap vs. proposed

**1. Knowledge layer (what facts exist about the codebase)**
Today: `graph_edges`/`symbol_references` tables, populated by ingestion,
scoped only to tools/analysis itself. The actual game code - world/,
engine/, resolver/, dungeon_neo/, etc. - has never been ingested, so
questions about it require ad-hoc grep instead of a query.
Proposed: point ingestion at world/ + engine/ + resolver/ + dungeon_neo/
(core/, og_system/, routes/, ai/ as a second pass). Same DB, same schema -
"run the thing we already have over more files," no new design needed here.

**2. Reasoning layer (how facts get turned into answers)**
Today: the Truth Kernel query algebra (Select/Combine), 6 views
(STRUCTURE/STABILITY/INTEGRITY/SUMMARY/SUBSYSTEM/ROLE), `Assessor.ask()` as
the NL front door - real, tested, regression-covered (see TRACKER.md for
the current pass count). No structural gap; this layer is solid and just
needs to be fed more (layer 1) and asked more (layer 4).

**3. Tracking layer (durable record of in-progress work across sessions)**
Today: doesn't exist in DB-backed form. TRACKER.md (this file's
counterpart) is the closest analogue, but it's meta-tool notes about the
analysis tool itself, not a per-ripple work surface for changes to the game
code. Proposed: the task.md mechanism below.

**4. Capability layer (the actual analyses built on top of 1-3)**
Today: an `impact_query` intent exists in `api/oracle_router.py`, but its
full semantics are unverified - it's not yet confirmed whether it returns
the complete transitive reverse-dependency closure of a target symbol, or
only what the expansion-depth budget for the explainability trace happens
to surface. This needs to be checked before anything is built on top of it.
Proposed: ripple/blast-radius analysis (true transitive closure, both
directions) as the first new capability, since it's the direct prerequisite
for the task.md workflow below.

### The task.md proposal

Bart's own stated workflow: for a SIMPLE ripple (a rename, a literal string
in a known-small set of places) he already has the right tool - Sublime
Text global search, navigate, edit - and this system shouldn't insert
itself there, that would just be friction.

For a NON-simple ripple - where the chain includes pass-through logic,
indirect callers, or effects a literal-string search can't see (an
interface contract, a data shape, a behavior that changes meaning two calls
downstream) - that's the case this is meant to help with. Not by guessing:
by enumerating the real chain from the graph and giving a structured place
to work through it "one at a time in order till we get it fixed," in his
words, including "hate to leave something broken."

A task.md, generated from a ripple/impact query, should contain:

- the target symbol/file and the query that produced this file (so it can
  be regenerated, not just read)
- the full discovered chain: direct callers, direct callees, and transitive
  reach in both directions, distinguishing "local effect at this site" from
  "pass-through logic that itself needs to change"
- one checklist line per affected site, each in a state: OPEN / IN PROGRESS
  / DONE / ABANDONED (with reason) - reusing the same state machine
  proposed for durable backlog items generally, rather than inventing a
  second one
- nothing marked DONE on the file as a whole until every line is DONE or
  explicitly ABANDONED with a reason - no silent partial completion

Re-opening a task.md later has to do more than display the file: the tool
should re-run the query that generated it against current DB state and
report drift (sites that no longer exist, new sites that now match,
anything that changed shape since the file was written). Otherwise a
task.md from last week silently goes stale exactly the way conversation
memory does, defeating the point.

### Build order (smallest safe slices, in dependency order)

1. [ ] Widen ingestion scope to world/ + engine/ + resolver/ + dungeon_neo/.
   No new code - run existing ingestion over more files, plus whatever
   path-config change that requires. Verify with a regression test that
   asserts a known real symbol (e.g.
   `generate_location_from_potential`) shows up in `graph_edges` after
   ingestion.
2. [ ] Audit `impact_query`'s actual semantics against real data: full
   transitive closure, or only what the explainability trace's depth
   budget surfaces? Write this down as fact either way before building on
   it -"verify, don't assume" is the point of this whole section.
3. [ ] If a gap is found in #2, fix it or add a separate full-closure
   ripple query (both directions) as a new, explicit capability - not
   silently repurposing the explainability trace for a job it wasn't built
   for.
4. [ ] Build the task.md generator off the ripple query from #2/#3.
   Markdown, plain checklist format, matching the existing doc voice (see
   TRACKER.md for the style to match).
5. [ ] Build the "re-reference a task.md" path: read file -> extract the
   originating query -> re-run against current DB -> diff -> report.

### Open questions, answered by Bart

1. **Where should task.md files live?** A new tools/analysis/tasks/
   directory, git-tracked? Or something more disposable that isn't meant
   to survive a `git status` check?
   - A: docs folder (same folder as this file) is fine.
2. **Should ABANDONED require a reason every time**, or is that overkill
   for a one-person backlog?
   - A: if the AI isn't sure of the reason, it should ask the user for one;
     if the user says he doesn't care, use a sensible default (e.g. "user
     ok'd").
3. **For "pass-through logic," is structural call-chain enumeration enough
   for v1**, or should the existing contract/classification systems (see
   section 5 below) be pulled in too, to flag behavioral/type risk along
   the chain?
   - A: keep v1 simple; add more later if needed.

This section is still open work - see TRACKER.md for whether any of the
build-order items above have been started.

---

## 4. Symbol classification & routing architecture

This was originally a 4-iteration execution plan (Symbol Classification
Stabilization Plan.md). As of 2026-06-16, the target files largely exist
under their planned names (graph/symbol_classifier.py,
graph/symbol_router.py, graph/build_dependency_graph.py,
graph/module_resolution.py, ingestion/scan_project_files.py,
ingestion/extract_symbols.py) and most of the plan's intent has landed.
Two things in the original plan are now stale and should not be followed
literally: every "VALIDATION" step said to run
`python tools/analysis/run_analysis_pipeline.py`, which no longer exists
anywhere in the repo (deleted in the loose-script cleanup - see TRACKER.md;
the real entrypoints are `engine/run_engine.py` for ingestion and
`ask.py` for querying); and Iteration 3's target file
`persistence/persist_file_analysis.py` doesn't exist either - persistence
now lives in `persistence/persistence_engine.py`. Treat what follows as the
historical design record of the classifier/router/graph layer, not as
runnable instructions.

### Objective

Stabilize the analysis pipeline by separating symbol ingestion, symbol
normalization, symbol routing, symbol classification, and persistence
responsibilities into a deterministic pipeline with explicit authority
boundaries between stages. Deliberately avoids graph redesign, semantic
inference, or advanced runtime analysis.

### The problem this solved

The system used to mix multiple identity domains into a single classifier
path: static AST identities (`AIBoundary`, `world.map.generate_loot`),
runtime-derived access chains (`self.ai_system`, `ctx.session`,
`generate_structured_data.self.ai_system`), and language/builtin/external
symbols (`any`, `max`, `pathlib.Path`, `flask.jsonify`) - all run through
one comparison system. That caused false `external_unknown`
classifications, inconsistent project classification, debugging opacity,
unstable heuristics, namespace contamination, and persistence ambiguity.

### Target architecture (the part that's still the live mental model)

```
RAW SYMBOL -> NORMALIZATION -> ROUTER -> DOMAIN CLASSIFIER -> PERSISTENCE
```

Each layer has exactly one authority, and is explicitly never responsible
for the others' jobs:

1. **Ingestion authority** - extracts symbols from AST, preserves canonical
   identities, builds the project symbol universe. Never classifies, never
   does runtime inference, never persists, never touches graph semantics.
2. **Normalization authority** - canonical comparison identity, stable key
   extraction (e.g. `ai.ai_boundary.AIBoundary.classify_intent` ->
   `classify_intent`). Never classifies, routes, or persists.
3. **Routing authority** - decides symbol domain only: project / runtime /
   builtin / stdlib / external. Never persists, builds graph, or does
   semantic interpretation. Implemented as `route_symbol()`,
   `is_runtime_symbol()`, `is_builtin_symbol()`, `is_static_project_symbol()`
   in `graph/symbol_router.py`.
4. **Domain classification authority** - classifies only within an
   already-routed domain. Never routes, normalizes, or persists.
5. **Persistence authority** - deterministic storage only (insert rows,
   commit transactions, store already-classified entities). Never
   classifies, routes, normalizes, or does semantic interpretation - no
   project matching, bucket inference, classification heuristics,
   normalization logic, or fallback decisions belong here.

Final expected shape:

```
RAW SYMBOLS -> INGESTION -> NORMALIZATION -> ROUTING
                                                |
                       +------------------------+------------------------+
                       v                        v                        v
                  PROJECT                  RUNTIME                BUILTIN/EXT
                 CLASSIFIER               CLASSIFIER               CLASSIFIER
                       |                        |                        |
                       +------------------------+------------------------+
                                                v
                                          PERSISTENCE
                                                v
                                       DEPENDENCY GRAPH
```

### Success criteria (the bar this was measured against)

Symbol domains separated before classification; project identity
deterministic; runtime traces don't contaminate static analysis;
persistence performs storage only; graph relationships stay reproducible;
debugging localized by layer; each layer has exactly one authority;
classification behavior predictable and explainable.

The original plan broke this into 4 iterations (identity stabilization,
routing layer separation, persistence stabilization, graph consistency
stabilization), each with its own target files, required outcomes, and
non-goals. Per the status note above, that level of detail is now mostly
historical - the files and authority boundaries it specified are in place.
If the authority model above is ever violated by future changes, this
section is the reference for what "violated" means.

---

## 5. Contracts & governance - exploratory notes (superseded)

This section is a condensed version of `contracts  + visibility.md`, kept
for the conceptual framing even though its concrete proposal is moot. The
original read as an AI-assisted brainstorming transcript rather than a
committed plan; its concrete proposal - plugging a "safe evolution
protocol" into `run_analysis_pipeline` and `debug_run.py` - is moot because
both of those files were deleted in the loose-script cleanup (see
TRACKER.md; the pipeline module never existed, debug_run.py only imported
it). The conceptual framing below predates, and was effectively superseded
by, the Truth Kernel / oracle work in section 2 above, which is further
along and already running against real data.

**The observation that mattered:** the codebase already had (and may still
have) 4 overlapping contract systems, not one - a JSON contract registry
(`tool_system_contract.json`, classification boundary rules, CP0-CP1
pipeline rules), Python contract modules
(`semantic_pipeline_contract.py`, `classification_contract.py`,
`contract_validator.py`), embedded inline contracts (LOCKED-comment style
invariants in `evaluation_snapshot.py`/`symbol_classifier.py`/
`semantic_candidate_builder.py`), and structural contracts in the
ingestion/graph layer (`BehavioralContract`,
`_extract_behavioral_contracts`, `FileAnalysis.behavioral_contracts`). The
real problem identified wasn't "we need to design a contract system" - it
already existed, distributed and partially inconsistent - it was "there is
no single arbitration layer deciding which contract is authoritative when
they disagree."

**The 3-layer mental model proposed** (reality layer = the actual codebase;
truth-extraction layer = CCSS/snapshots/metrics/classifier outputs;
constraint layer = contracts in all their forms) is still a reasonable way
to think about where a future "contract precedence" system would sit, if
one is ever built. It is not currently built, and nothing in section 2's
Truth Kernel design depends on it - the Truth Kernel's STABILITY view reads
real contract violation reports directly rather than going through any
arbitration layer. Worth a skim if this idea is revisited; don't treat any
file/entrypoint name in the original as current.
