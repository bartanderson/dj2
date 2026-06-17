Semantic Identity Reconstruction Migration Plan
Core Diagnosis

The primary failure is not classification logic.

The failure is premature semantic flattening.

The pipeline currently collapses semantically rich symbolic entities into presentation-level string tokens before routing, graph construction, persistence, and reasoning occur.

Example:

"dataclass"

is not equivalent to:

"dataclasses.dataclass"

The former is:

a lexical surface token
context-dependent
locally meaningful

The latter is:

a semantic identity
globally comparable
graph-safe

The current architecture incorrectly treats lexical artifacts as semantic identities.

This causes:

routing failures
graph fragmentation
false unknowns
heuristic proliferation
ontology mismatches across subsystems
Critical Architectural Insight

Flattening destroyed semantic linkage information too early.

The original pipeline:

AST
→ extract raw symbol strings
→ discard semantic provenance
→ later attempt classification

created irreversible information loss.

However, most semantic information still exists nearby in:

AST structure
imports
alias maps
runtime bindings
module context
repository topology

Therefore:
semantic reconstruction is feasible.

This is not heuristic guessing from nothing.

It is:

deterministic semantic recovery from retained contextual evidence.

Architectural Principle

The system must distinguish between:

Layer   Meaning
Surface Token   lexical representation
Semantic Candidate  reconstructed contextual identity
Canonical Identity  globally stable graph identity

These are separate ontology layers and must not be conflated.

Canonical Layer Definitions
1. Surface Token

Example:

"dataclass"

Properties:

presentation-oriented
local lexical artifact
AST-visible
unstable globally

Used for:

rendering
source display
debugging

Not suitable for:

graph identity
routing
persistence semantics
2. Semantic Candidate

Example:

ResolvedCandidate(
    leaf="dataclass",
    fqdn="dataclasses.dataclass",
    source="import_alias",
    confidence=1.0,
    evidence=[
        "from dataclasses import dataclass",
        "ast.Name(dataclass)",
    ],
)

Properties:

reconstructed from context
evidence-bearing
provenance-aware
may contain ambiguity
transitional semantic form

Used for:

reconstruction
observability
diffing
AI reasoning
migration bridging
3. Canonical Identity

Example:

"dataclasses.dataclass"

Properties:

globally stable
graph-safe
persistence-safe
immutable semantic identity

Used for:

graph edges
routing
persistence
contracts
dependency analysis
Migration Strategy

A full semantic-native rewrite is currently too expensive because flattening assumptions already exist across:

routing
graph construction
persistence
query systems
rendering
contracts
AI context systems

Therefore:
the migration strategy is phased reconstruction rather than immediate replacement.

Phase 1 — Semantic Reconstruction Layer (NOW)

Current architecture:

AST
→ flatten
→ strings
→ reconstruction
→ routing

Goals:

preserve operational compatibility
avoid destabilizing downstream systems
build observability
validate semantic recovery accuracy

Implement:

deterministic reconstruction layer
TraceCollector
shadow routing pipeline
route diffing
semantic candidate generation

Important:
Production routing behavior remains unchanged.

The reconstruction system operates in parallel.

Phase 2 — Earlier Semantic Recovery (NEXT)

Move semantic reconstruction progressively closer to ingestion.

Architecture evolves toward:

AST
→ contextual extraction
→ semantic candidates
→ legacy adapters
→ existing systems

Goals:

reduce information loss
reduce heuristic recovery burden
begin candidate-aware graph construction
introduce semantic persistence models

At this stage:
legacy string systems still coexist.

Phase 3 — Semantic-Native Pipeline (LATER)

Architecture becomes:

AST
→ semantic identity objects
→ graph/contracts/query/context systems

Flattening becomes presentation-only.

Strings are no longer transport identity.

They are only:

rendering artifacts
display representations
export formats
Final Architectural Goal (EVENTUALLY)

Never flatten semantic identity during:

ingestion
routing
graph construction
persistence
contracts
AI context generation

Flatten only for:

display
rendering
user presentation
Important Operational Principle

The current effort is NOT:

fixing a router
improving string matching
patching classification

The actual goal is:

building a semantic identity recovery system over partially collapsed symbolic information.

That is the true architectural trajectory.