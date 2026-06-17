STATUS NOTE (added 2026-06-16, read-only audit, no content below changed): The
iteration target files largely exist under their planned names (graph/symbol_classifier.py,
graph/symbol_router.py, graph/build_dependency_graph.py, graph/module_resolution.py,
ingestion/scan_project_files.py, ingestion/extract_symbols.py) - so most of this plan's
intent appears to have landed. Two things below are now stale: (1) every "VALIDATION"
section says to run `python tools/analysis/run_analysis_pipeline.py` - that file no longer
exists anywhere in the repo (confirmed via repo-wide search) and has been deleted as part of
the loose-script cleanup; the current real entrypoint is `engine/run_engine.py` (ingestion)
and `ask.py` (querying). (2) Iteration 3's target file
`persistence/persist_file_analysis.py` also does not exist - persistence responsibility now
lives in `persistence/persistence_engine.py` instead. Treat this doc as a historical design
record of the classifier/router/graph layer, not as runnable instructions. A near-duplicate
draft of this same plan (top-level `rewrite plan for routing to classification.md`) was
deleted as redundant - this was the more complete/clean copy of the two, kept for that
reason.

Symbol Classification Stabilization Plan

Objective



Stabilize the analysis pipeline by separating:



symbol ingestion

symbol normalization

symbol routing

symbol classification

persistence responsibilities



The goal is deterministic classification behavior with explicit authority boundaries between pipeline stages.



This plan intentionally avoids graph redesign, semantic inference, or advanced runtime analysis.



Current Known Problem



The system currently mixes multiple identity domains into a single classifier path:



Static AST identities

classify_intent

AIBoundary

world.map.generate_loot

Runtime-derived access chains

self.ai_system

ctx.session

generate_structured_data.self.ai_system

Language/builtin/external symbols

any

max

pathlib.Path

flask.jsonify



These are currently processed through a single comparison system, causing:



false external_unknown

inconsistent project classification

debugging opacity

unstable heuristics

namespace contamination

persistence ambiguity

Target Architecture

RAW SYMBOL

    ↓

NORMALIZATION

    ↓

ROUTER

    ↓

DOMAIN CLASSIFIER

    ↓

PERSISTENCE



Each layer has exactly one authority.



Authority Model

1. Ingestion Authority



Responsible for:



extracting symbols from AST

preserving canonical identities

building project symbol universe



Never responsible for:



classification

runtime inference

persistence

graph semantics

2. Normalization Authority



Responsible for:



canonical comparison identity

stable key extraction



Never responsible for:



classification

routing

persistence

3. Routing Authority



Responsible for:



deciding symbol domain



Example domains:



project

runtime

builtin

stdlib

external



Never responsible for:



persistence

graph construction

semantic interpretation

4. Domain Classification Authority



Responsible for:



classification within a routed domain only



Never responsible for:



routing

normalization

persistence

5. Persistence Authority



Responsible for:



deterministic storage only



Never responsible for:



classification

routing

normalization

graph semantics

------------------------------------------

Iteration 1 — Identity Stabilization

Goal



Create one stable symbol identity system.



Remove conflicting project matching logic and establish canonical comparison behavior.



Files

tools/analysis/graph/symbol_classifier.py

tools/analysis/ingestion/scan_project_files.py

tools/analysis/ingestion/extract_symbols.py

Functions

project_key()



FILE:

symbol_classifier.py



Authority:



canonical comparison identity



Responsibilities:



extract stable comparison leaf



Example:



ai.ai_boundary.AIBoundary.classify_intent

    →

classify_intent

classify_symbol()



FILE:

symbol_classifier.py



Responsibilities:



remove duplicate project logic

remove conflicting prefix logic

centralize project comparison behavior

scan_project_files()



FILE:

scan_project_files.py



Responsibilities:



aggregate project symbol universe

attach stable project symbol set to analysis object

extract_symbols()



FILE:

extract_symbols.py



Responsibilities:



preserve canonical dotted symbol identity



Example:



ai.ai_boundary.AIBoundary.classify_intent

Required Outcomes



By end of iteration:



project matching uses one identity rule only

no duplicate project matching blocks remain

no prefix-based project inference remains

local project functions classify consistently

builtin classification remains stable

debug output exposes comparison operands directly

DO NOT TOUCH

NON-GOALS

no graph redesign

no routing layer creation

no persistence redesign

no runtime inference redesign

no dependency graph changes

no AST parser rewrite

no semantic analysis additions

no type inference

no import resolution redesign

VALIDATION



Run:



python tools/analysis/run_analysis_pipeline.py



Expected:



local functions no longer incorrectly fall through

builtins classify as builtin

project comparisons use stable identity

debug output explicitly shows:

input name

normalized project key

project comparison set

boolean match result

no duplicate project classification branches remain

-----------------------------------------------------------

Iteration 2 — Routing Layer Separation

Goal



Separate symbol domains before classification.



This iteration restores control over classification flow.



New File

tools/analysis/graph/symbol_router.py

New Functions

route_symbol()



Responsibilities:



determine symbol domain before classification



Output domains:



project

runtime

builtin

stdlib

external

unknown

is_runtime_symbol()



Responsibilities:



identify runtime-derived access paths



Examples:



self.ai_system

ctx.session

app.world

generate.foo.bar

is_builtin_symbol()



Responsibilities:



builtin detection only

is_static_project_symbol()



Responsibilities:



static project symbol determination only



Uses:



project_key(name) in project_roots

Modified File

tools/analysis/graph/symbol_classifier.py



Changes:



classifier no longer performs routing decisions

classifier assumes routed domain

external fallback simplified

Required Outcomes



By end of iteration:



runtime symbols never enter project matching

builtins never enter project comparison path

static project symbols classify deterministically

external symbols no longer contaminate project matching

fallthrough logs significantly reduce

DO NOT TOUCH

NON-GOALS

no persistence changes

no graph redesign

no AST extraction redesign

no database schema changes

no dependency graph modifications

no runtime execution tracing

no semantic graph inference

no import resolver rewrite

VALIDATION



Run:



python tools/analysis/run_analysis_pipeline.py



Expected:



runtime symbols routed before classification

builtins never hit project matcher

project symbols do not reach external fallback

reduced CLASSIFY FALLTHROUGH volume

routing decisions visible in debug output

no mixed-domain comparison behavior

--------------------------------------------------

Iteration 3 — Persistence Stabilization

Goal



Remove semantic authority from persistence layer.



Persistence becomes deterministic storage only.



File

tools/analysis/persistence/persist_file_analysis.py

Functions

persist_file_analysis()



Responsibilities:



insert rows

commit transactions

store already-classified entities



No longer responsible for:



classification

routing

normalization

semantic interpretation

Logic Removed From Persistence

project matching

bucket inference

classification heuristics

normalization logic

fallback decisions

Required Outcomes



By end of iteration:



persistence layer becomes deterministic

classification occurs fully upstream

persistence debugging becomes minimal

storage behavior becomes predictable

graph storage no longer mutates symbol meaning

DO NOT TOUCH

NON-GOALS

no graph redesign

no router redesign

no AST changes

no dependency graph changes

no database redesign

no semantic enrichment

no runtime inference changes

no classification redesign

VALIDATION



Run:



python tools/analysis/run_analysis_pipeline.py



Expected:



persistence inserts only pre-classified symbols

persistence layer contains no semantic branching

symbol categories remain stable before/after insertion

persistence debug output significantly reduced

classification outputs unchanged by persistence execution

----------------------------------------------------------------

Iteration 4 — Graph Consistency Stabilization

Goal



Stabilize graph relationships using already-separated symbol domains.



Graph construction becomes trustworthy only after routing and classification are stable.



Files

tools/analysis/graph/build_dependency_graph.py

tools/analysis/graph/module_resolution.py



(possible limited modifications only)



Functions

Dependency edge builders



Responsibilities:



construct edges from stable identities only

avoid runtime contamination

preserve deterministic graph relationships

Required Outcomes



By end of iteration:



dependency edges become stable

project ownership becomes trustworthy

external boundaries become deterministic

runtime references remain isolated from static dependency graph

graph output becomes reproducible across runs

DO NOT TOUCH

NON-GOALS

no semantic AI analysis

no type inference

no runtime execution modeling

no persistence redesign

no AST redesign

no router redesign

no symbol extraction redesign

no database redesign

VALIDATION



Run:



python tools/analysis/run_analysis_pipeline.py



Expected:



dependency graph builds consistently

graph edges remain stable across reruns

runtime traces do not appear as static project edges

external libraries remain isolated correctly

no project symbol contamination from runtime chains

Final Expected Architecture

                RAW SYMBOLS

                      │

                      ▼

             INGESTION LAYER

                      │

                      ▼

            NORMALIZATION LAYER

                      │

                      ▼

               ROUTING LAYER

                      │

        ┌─────────────┼─────────────┐

        ▼             ▼             ▼



   PROJECT        RUNTIME      BUILTIN/EXT

  CLASSIFIER     CLASSIFIER     CLASSIFIER



        └─────────────┼─────────────┘

                      ▼

               PERSISTENCE

                      │

                      ▼

              DEPENDENCY GRAPH

Final Success Criteria



The system is considered stabilized when:



symbol domains are separated before classification

project identity is deterministic

runtime traces do not contaminate static analysis

persistence performs storage only

graph relationships remain reproducible

debugging becomes localized by layer

each layer has exactly one authority

classification behavior becomes predictable and explainable