# Architectural Constitution

This document defines the non-negotiable architectural principles governing the simulation system.

Subsystem design documents may evolve.
Implementation details may change.
APIs, schemas, helper methods, and pipeline internals may be refactored.

These principles must remain stable unless explicitly superseded by a deliberate architectural revision.

---

# 1. Core Philosophy

The system is a deterministic simulation engine augmented by constrained AI presentation and interpretation layers.

Simulation truth, causal history, perception state, and narrative expression are separate concerns and must remain separated.

The architecture prioritizes:
- deterministic behavior
- replayability
- inspectable causal flow
- explicit authority boundaries
- implementation evolvability

---

# 2. Source-of-Truth Hierarchy

## WorldState
Canonical simulation truth.

Contains authoritative entity state, positions, combat state, inventories, flags, and persistent world data.

No other system may silently redefine canonical world truth.

---

## EventLog
Authoritative causal history.

Defines:
- what happened
- when it happened
- which systems emitted it

Events are immutable after emission.

EventLog does not determine:
- narrative meaning
- salience
- visibility
- interpretation

---

## EscalationEngine
Deterministic causal propagation layer.

May:
- evaluate rules
- emit derived events
- generate contextual effects
- influence interpretation overlays

Must NOT:
- rewrite prior events
- mutate canonical WorldState directly outside approved flows
- redefine entity resolution structures
- perform narrative reasoning

---

## ContextBuilder
Deterministic perception and context assembly layer.

Responsible for:
- visibility filtering
- awareness derivation
- salience filtering
- knowledge gap construction
- escalation overlay application

ContextBuilder is a consumer of simulation state, not a mutator.

Visibility is computed exactly once per build cycle.

---

## AI / Narrative Layer
Presentation and expression layer only.

May:
- narrate
- summarize
- contextualize
- roleplay
- generate prose

Must NOT:
- mutate authoritative state
- alter structured outputs
- invent canonical truth
- bypass deterministic systems

Structured adjudication outputs must pass through unchanged.

---

# 3. Determinism Requirements

Given:
- identical initial state
- identical inputs
- identical event sequence

The simulation must produce identical outcomes.

The following are forbidden:
- hidden mutable global state
- post-emission event mutation
- nondeterministic causal rewriting
- multiple conflicting authority paths

---

# 4. Authority Boundary Rules

## Only Adjudication-like systems mutate canonical simulation state.

## Only EscalationEngine propagates event depth.

## Only ContextBuilder determines final visibility state for a build cycle.

## Only EventLog defines causal history.

## AI systems never become authoritative simulation actors.

---

# 5. Evolution Rules

The architecture is intentionally evolvable.

The following MAY evolve:
- helper APIs
- schemas
- effect payloads
- internal pipeline structure
- optimization strategies
- subsystem decomposition
- visibility heuristics
- salience weighting
- implementation details

Changes are acceptable IF they preserve:
- deterministic behavior
- replay guarantees
- authority boundaries
- causal integrity
- single-source-of-truth rules

---

# 6. Implementation Reconciliation Rule

Design documents are not treated as infallible specifications.

Implementation, runtime behavior, tests, and existing systems must continuously reconcile against:
- architectural invariants
- actual gameplay needs
- deterministic guarantees

When contradictions appear:
1. identify the true authority boundary being violated
2. determine whether the issue is:
   - implementation bug
   - design flaw
   - missing invariant
   - underspecified behavior
3. refine the smallest responsible layer
4. avoid introducing duplicate authority systems

The solution to ambiguity is clarification and reconciliation, not architectural sprawl.

---

# 7. LLM Governance Rules

LLMs are implementation assistants, not architectural authorities.

All generated code and design proposals must be evaluated against:
- this constitution
- subsystem design docs
- existing runtime behavior
- deterministic constraints

LLMs must not:
- invent hidden authority paths
- collapse layer boundaries
- bypass EventLog
- merge simulation and narrative responsibilities
- introduce duplicate identity or state systems

Implementation convenience is never sufficient justification for violating architectural boundaries.

---

# 8. Change Classification

## Constitutional Changes
Rare.
Require explicit review.

Examples:
- changing authoritative ownership
- removing deterministic guarantees
- allowing AI-driven state mutation
- replacing EventLog authority

---

## Design-Level Changes
Expected during development.

Examples:
- changing effect schema
- adjusting visibility heuristics
- refining salience logic
- restructuring helper APIs
- optimizing pipeline stages

These should remain compatible with constitutional principles.

---

# 9. Practical Development Strategy

Prefer:
- small deterministic implementations
- integration testing
- incremental refinement
- runtime verification
- architecture-preserving iteration

Avoid:
- premature abstraction
- speculative complexity
- hidden state coupling
- parallel authority systems
- rewriting working systems without measured benefit

---

# 10. Primary System Goal

The objective is not architectural purity.

The objective is:
a maintainable, inspectable, replayable, AI-augmented simulation engine capable of supporting emergent narrative gameplay without sacrificing deterministic simulation integrity.