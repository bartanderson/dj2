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

## 3. Agent capability layer (design proposal - nothing built yet)

**Status: design only. Not one line of this has been implemented.** The
build-order checklist for this section lives in TRACKER.md under "Agent
Capability Layer build order" - that's where checkboxes belong; this
section is for the reasoning behind them, not for tracking what's done.

### Why this layer exists

The concrete trigger was small: Bart half-remembered a design decision -
"potentials that collapse at trigger time" - and asked for it to be
checked rather than trusted from memory. It checked out, but only
partially: `world_controller.py`'s `potential_locations` and
`generate_location_from_potential`, `world_map.py`'s on-demand-generation
comment, and `travel_system.py`'s `EncounterPoint.activate()` /
`generate_encounter()` all confirmed the mechanism is real and wired up -
but `region_id` is hardcoded `None` at the point a potential is created,
so `generate_location_from_potential` always returns `None` right now.
Wired, but dead.

That's the pattern worth naming: a half-remembered fact about a large
codebase turned out to be mostly right and partly wrong, and the only way
to find out which parts was to go look. This is the same problem the Truth
Kernel already solves one level down - "the AI must not invent structure,
it must read it off the DB" - showing up one level up, for the person
doing the designing. Bart's own framing for this is "the boundary is my
memory": past some size, a codebase stops fitting in one person's head,
and the limiting resource isn't AI capability, it's how much of a large,
changing system one person can keep accurately in mind at once. This
layer is about extending the Truth Kernel's discipline outward to cover
the actual game code (world/, engine/, resolver/, dungeon_neo/, etc.),
which has never been ingested at all - right now, questions about it
require ad-hoc grep, not a query.

### The shape: four layers, one throughline

It's tempting to describe this as four independent features to build.
That's the wrong frame - two of the four layers are already built, because
they're the same mechanism the Truth Kernel runs on, just narrower in
scope than they need to be. The other two are genuinely new, and one of
them depends on a fact about the system that hasn't been checked yet.

**Knowledge - widen the substrate, don't redesign it.** The
`graph_edges`/`symbol_references` tables and the ingestion pipeline that
populates them already exist and already work; they're just scoped to
`tools/analysis` itself. Pointing that same ingestion at `world/` +
`engine/` + `resolver/` + `dungeon_neo/` (with `core/`, `og_system/`,
`routes/`, `ai/` as a second pass) is "run the thing we already have over
more files," not new design.

**Reasoning - proven, but only proven on one corpus.** The query algebra
(Select/Combine), the 6 views, and `Assessor.ask()` as the NL front door
are real, tested, and regression-covered - but every test that proves that
runs against `tools/analysis`'s own code. "This works" and "this works on
a much larger, differently-shaped codebase full of game logic instead of
analysis-tool logic" are different claims, and only the first one has been
checked. Applying this project's own verify-don't-assume discipline to
itself: the reasoning layer should be treated as proven-on-one-corpus, not
proven, until it's actually been run against the widened Knowledge layer.

**Tracking - a durable record has to answer to ground truth, not just
exist.** Nothing like a per-task durable record exists yet; TRACKER.md is
the closest analogue, but it's meta-notes about the analysis tool itself,
not a workspace for tracking an in-progress change to the game code. The
task.md mechanism below is the proposed answer. The reason its
re-open-and-recheck-drift requirement isn't optional: a checklist that
just sits there and gets read is, eventually, "memory in a different file
format" - exactly the failure mode this whole layer exists to avoid. A
task.md only earns its keep if reopening it re-asks the question it was
built from, against current DB state, every time.

**Capability - the payoff layer, and the one most likely to fool you if
skipped past.** An `impact_query` intent already exists in
`api/oracle_router.py`. What's unverified is whether it returns the full
transitive reverse-dependency closure of a target symbol, or only what the
explainability trace's depth budget happens to surface along the way -
those are very different guarantees, and right now nobody has written down
which one it actually provides. This project has hit the "looks done,
isn't" pattern more than once already (orphaned Truth Layer views with
zero real callers, `drift_signals` hardcoded to `[]`, `Filter` nodes that
were referenced but never constructed) - the lesson each time was that an
unverified assumption about what a piece of code actually does is exactly
where the next one of these is hiding. `impact_query` is a plausible next
home for that bug, precisely because it looks finished. It has to be
audited against real data before the task.md mechanism is built on top of
it, not after.

### The task.md mechanism, and where it's deliberately *not* meant to help

Bart's own stated workflow: for a SIMPLE ripple - a rename, a literal
string in a known-small set of places - he already has the right tool,
Sublime Text global search, navigate, edit, and this system shouldn't
insert itself there; that would just be friction for no benefit.

For a NON-simple ripple - where the chain includes pass-through logic,
indirect callers, or effects a literal-string search can't see (an
interface contract, a data shape, a behavior that changes meaning two
calls downstream) - that's the case this is meant to help with. Not by
guessing: by enumerating the real chain from the graph and giving a
structured place to work through it "one at a time in order till we get it
fixed," in his words, including "hate to leave something broken."

A task.md, generated from a ripple/impact query, should contain:

- the target symbol/file and the query that produced this file, so it can
  be regenerated, not just read
- the full discovered chain in both directions, distinguishing "local
  effect at this site" from "pass-through logic that itself needs to
  change" - those are different kinds of work and collapsing them into one
  undifferentiated list would defeat the purpose
- one checklist line per affected site, each in a state: OPEN / IN
  PROGRESS / DONE / ABANDONED (with reason) - reusing the same state
  machine as durable backlog items generally, rather than inventing a
  second one
- nothing marked DONE on the file as a whole until every line is DONE or
  explicitly ABANDONED with a reason - no silent partial completion

Re-opening a task.md has to do more than display the file: it has to
re-run the query that generated it against current DB state and report
drift - sites that no longer exist, new sites that now match, anything
that changed shape since the file was written. Skip that, and a task.md
from last week goes stale exactly the way a half-remembered design
decision does - which is the thing this whole layer was built to stop
happening.

### Decisions Bart has already made, and why

1. **Where should task.md files live?** Answer: the docs folder, same
   folder as this file. The alternative under consideration was a
   dedicated `tools/analysis/tasks/` directory; the simpler answer won
   because there's no benefit yet to a separate location until there's
   evidence one is needed - matching the project's general preference for
   not building structure ahead of a demonstrated need for it.
2. **Should ABANDONED require a reason every time**, or is that overkill
   for a one-person backlog? Answer: if the AI isn't sure of the reason, it
   should ask; if Bart says he doesn't care, fall back to a sensible
   default (e.g. "user ok'd"). This keeps the state machine honest without
   making it bureaucratic - the point of requiring a reason is to prevent
   silent abandonment, not to extract paperwork.
3. **For "pass-through logic," is structural call-chain enumeration enough
   for v1**, or should the existing contract/classification machinery
   (section 5 below) be pulled in too, to flag behavioral/type risk along
   the chain? Answer: keep v1 to structural call-chain enumeration only;
   add more later if a real case demonstrates the need. This is the same
   discipline as decision 1 - resist scope creep that isn't backed by
   evidence yet, especially here, where section 5's contract systems are
   themselves only partially reconciled with each other.

Build sequencing, what's actually started, and current status all live in
TRACKER.md - intentionally not duplicated here.

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

### The shadow/observability layer (added after this plan; not in the original design)

This wasn't in the original Symbol Classification Stabilization Plan, but
it's real and live in `graph/symbol_router.py` / `graph/route_trace.py`
today, and it isn't documented anywhere else, so it belongs here.

`route_symbol()` is still the only production entrypoint - a thin wrapper
over `_route_symbol_core()`, explicitly commented in the source as "the
historical routing truth source... must remain deterministic and
structurally stable." Nothing about that has changed.

Alongside it, `route_symbol_shadow()` runs the same core router but also
attaches a `TraceCollector` that records CP0-CP4 checkpoints (raw input,
canonical/normalized form, classification input, project/runtime/
builtin/stdlib match flags, final result) plus a parallel "CP2.5 semantic
observation" pass that records lexical/decomposition signals and candidate
semantic identities (surface, fqdn guess, module, confidence, evidence).
The source comments are unusually explicit about what this layer is and
is not: "This is NOT a production routing path," "MUST NOT influence CP3
routing decisions," "All routing decisions in this module are final
within the pipeline" (referring to the CP3 stage the legacy router owns).
It's a pure observation/audit channel, not an alternate routing path.

This is the resolution of an older, larger ambition. The
"semantic identity reconstruction" line of work (see
`docs/del/Semantic Identity Reconstruction Migration Plan.md`) originally
proposed a phased migration - through CP2.5 and CP3 checkpoint stages,
comparing a shadow semantic-aware router against the legacy one - toward
eventually replacing `route_symbol()` with identity-aware resolution. The
code comments confirm that the comparison/shadow infrastructure got built
close to as specified, but the end state didn't: a full "CP2.5 semantic
observation layer" that could influence routing was tried, then marked
`(DEPRECATED)` and removed from execution, then replaced by the current
"SEED DISCOVERY LAYER" (DB-backed symbol lookup, explicitly "no semantic
interpretation, no identity reconstruction") plus the permanent
trace-only CP2.5 that exists today. In other words: the diagnosis behind
the migration plan was correct and the audit tooling it called for got
built, but the project deliberately stopped short of the planned
pipeline replacement and settled on "legacy router stays sole authority
forever, shadow/trace layer watches and records but never decides." That's
a quieter, more conservative outcome than the original plan envisioned,
and it's consistent with this section's own authority-model principle:
one layer, one authority, and "use the shadow output to inform a human or
a future decision" is a different thing from "let the shadow output make
the decision."

No open item currently tracks whether this shadow/trace layer is being
used for anything (e.g. periodic comparison runs, drift detection) or
just sitting there instrumented but uncalled outside of
`classification/classify_references.py`'s direct use of
`route_symbol_shadow()`. Worth a real audit before the Agent Capability
Layer's Knowledge-widening work (section 3) starts touching this part of
the pipeline.

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
truth-extraction layer = snapshots/metrics/classifier outputs;
constraint layer = contracts in all their forms) is still a reasonable way
to think about where a future "contract precedence" system would sit, if
one is ever built. It is not currently built, and nothing in section 2's
Truth Kernel design depends on it - the Truth Kernel's STABILITY view reads
real contract violation reports directly rather than going through any
arbitration layer. Worth a skim if this idea is revisited; don't treat any
file/entrypoint name in the original as current.
