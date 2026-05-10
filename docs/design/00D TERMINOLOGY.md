# 00D TERMINOLOGY.md
## System-Wide Semantic Contract Layer

⚠️ STATUS
This document defines canonical meaning of core system terms.
It does NOT define behavior, architecture, or execution order.

It exists solely to prevent semantic drift across subsystems.

---

# 🧠 RULE OF USE

- If a term appears in multiple systems → it MUST be defined here.
- If a term is ambiguous in a bug or design discussion → define it here.
- If a subsystem redefines a term → it is a violation of this contract.

This file is authoritative for MEANING only.

It is NOT authoritative for behavior.

---

# 📦 CORE TERMINOLOGY

## ENTITY

A uniquely identifiable object within the simulation world.

### Canonical meaning:
An Entity is a stable identity reference managed exclusively by the Entity Resolution system.

### Properties:
- Has a globally unique `entity_id`
- Exists independently of perception or visibility
- May or may not be currently observable by a player

### Excludes:
- Narrative descriptions
- UI representations
- Contextual projections (these are derived, not canonical)

---

## EVENT

A discrete, immutable record of something that occurred in the simulation.

### Canonical meaning:
An Event is a time-ordered record stored in the Event Log representing a state change, action, or system occurrence.

### Properties:
- Immutable after creation
- Ordered chronologically
- May reference one or more entities

### Excludes:
- Interpretation
- Narrative summarization
- AI-generated context expansion

---

## VISIBILITY

The determination of whether an entity is perceptible to a player in a given context.

### Canonical meaning:
Visibility is a computed property derived from WorldState, lighting, and perception rules.

### Notes:
- Visibility is NOT identity
- Visibility is NOT knowledge
- Visibility is recomputed per ContextBuilder cycle

---

## SALIENCE

The relevance score or inclusion trigger for events in a context snapshot.

### Canonical meaning:
Salience determines whether an Event is included in a ContextBuilder output.

### Sources of salience:
- explicit EscalationEngine marking
- player involvement
- system-relevant event categories
- interaction with visible entities

---

## ESCALATION EFFECT

A structured rule-derived modification produced by the EscalationEngine.

### Canonical meaning:
An Escalation Effect is a deterministic, non-destructive overlay influencing interpretation of world state.

### Properties:
- has type (e.g. visibility.override)
- has scope (entity/location/global)
- has payload (structured parameters)

### Excludes:
- direct mutation of world state
- identity modification
- event log mutation

---

## CONTEXT

A snapshot representation of the current world state as perceived by the player.

### Canonical meaning:
Context is the output of ContextBuilder combining:
- world state
- event history
- escalation effects
- perception rules

### Notes:
Context is NOT truth. It is a filtered projection of truth.

---

## KNOWLEDGE GAP

A representation of missing or hidden information in the current context.

### Canonical meaning:
Knowledge Gaps describe unknown or partially known elements inferred from visibility constraints and world state limitations.

---

## ACTOR

An Entity capable of initiating actions or events.

### Canonical meaning:
An Actor is an Entity with agency within the simulation system.

### Notes:
All Actors are Entities, but not all Entities are Actors.

---

## STATE

A deterministic snapshot of system conditions at a given moment.

### Canonical meaning:
State refers to structured, machine-readable values representing world conditions at a specific time.

---

# 📌 EXTENSION RULE

If a term is missing:
1. Do NOT guess meaning in code or design docs
2. Mark it as ambiguous
3. Add it here before continuing design work

---

# 🧷 VERSIONING RULE

Definitions in this document are stable unless:
- ambiguity is discovered
- cross-system inconsistency appears
- a design change forces redefinition

All changes must preserve backward compatibility in interpretation where possible.