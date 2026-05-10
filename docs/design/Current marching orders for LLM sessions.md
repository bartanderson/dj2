It is your LLM operating procedure for the remainder of stabilization + implementation.

📦 MASTER SESSION FLOW

Each new session should follow this exact pattern:

Establish authority hierarchy
Establish current implementation phase
Load only active subsystem docs
Load only directly relevant code
Compare:
docs ↔ code
boundaries
ownership
ordering
Produce:
contradictions
required fixes
safe implementation path
Implement/tests
Move forward one layer only
🧱 SESSION 0 — FOUNDATION STABILIZATION
PURPOSE

Lock:

Event Log
Escalation Engine
their interaction boundaries

before touching higher systems.

📄 FILES TO PROVIDE
Authoritative docs
type "docs\design\00A ARCHITECTURAL_CONSTITUTION.md" >prompt1.txt
type "docs\design\00B SYSTEM_CONSTRAINTS.md" >>prompt1.txt
type "docs\design\00C IMPLEMENTATION_SEQUENCE.md">>prompt1.txt
rem Active subsystem docs
type "docs\design\01 event log v1.3.md" >>prompt1.txt
type "docs\design\02 escalation engine v1.3.md" >>prompt1.txt
type "world\event_log.py" >>prompt1.txt
type "world\escalation_engine.py" >>prompt1.txt
type "world\world_controller.py" >>prompt1.txt

Optional only if already tightly coupled:

type "world\adjudication_engine.py" >prompt1.
🧠 SESSION 0 PROMPT

We are now in implementation stabilization mode, not architecture redesign.

Authoritative hierarchy:

00A ARCHITECTURAL_CONSTITUTION.md
00B SYSTEM_CONSTRAINTS.md
00C IMPLEMENTATION_SEQUENCE.md
00D TERMINOLOGY.md
Active subsystem docs
Existing code implementation

The architecture has already converged sufficiently for implementation.

Your job is:

compare subsystem docs against existing code
identify contradictions, drift, hidden authority violations, mutation leaks, or ordering inconsistencies
preserve subsystem boundaries
preserve deterministic execution ordering
preserve separation between simulation truth, escalation, interpretation, and presentation

Do NOT redesign architecture unless contradictions are discovered between:

authoritative docs
subsystem docs
existing working code

Existing code is part of the truth surface and may expose ambiguities or impractical assumptions in docs.

We refine surgically, not globally.

Current subsystem focus:

Event Log
Escalation Engine

Primary concerns:

event ownership
event emission path integrity
deterministic escalation behavior
elimination of hidden global state
prevention of side-channel mutations

Tasks:

Compare docs against code
Identify mismatches
Identify dangerous ambiguity
Recommend only necessary fixes
Distinguish:
must-fix
safe-to-ignore
future concern
Then guide implementation/testing order
🧱 SESSION 1 — CONTEXT STABILIZATION

ONLY AFTER Session 0 stabilizes.

📄 FILES TO PROVIDE
Docs
00A
00B
00C

01
02
04 context builder v1.3.md
Code
world\event_log.py
world\escalation_engine.py
world\context_builder.py
world\world_controller.py

Optional:

adjudication_engine.py
🧠 SESSION 1 PROMPT

We are continuing implementation stabilization.

Architecture and authority hierarchy remain unchanged.

We are now validating:

ContextBuilder integration
escalation application ordering
visibility derivation
salience filtering
knowledge gap construction
prevention of interpretation leakage across layers

Important constraints:

ContextBuilder is a consumer, not a rule engine
Escalation effects are overlays, not world mutations
visibility is computed exactly once per build cycle
ContextBuilder must not re-resolve entities
escalation may influence perception but not canonical entity identity

Tasks:

Compare docs and code
Verify deterministic pipeline ordering
Verify no re-entrant visibility mutation
Verify salience retrieval correctness
Verify escalation application timing
Identify:
must-fix contradictions
implementation gaps
future-safe deferrals

Avoid speculative redesign.
Prefer surgical fixes.

🧱 SESSION 2 — ENTITY RESOLUTION STABILIZATION
📄 FILES TO PROVIDE
Docs
00A
00B
00C

01
02
04
05 entity resolution v1.3.md
Code
world\entity_resolution.py
world\context_builder.py
world\event_log.py
world\escalation_engine.py
world\world_controller.py
🧠 SESSION 2 PROMPT

We are validating Entity Resolution integration against the stabilized lower layers.

Current focus:

canonical identity ownership
prevention of duplicate resolution logic
deterministic entity lookup
protection against escalation mutation of canonical identity

Important constraints:

EntityResolver is the sole authority on canonical identity
ContextBuilder consumes resolved entities and must not re-resolve names independently
EscalationEngine may influence relevance/perception only
EscalationEngine must not mutate:
indices
synonym tables
embeddings
canonical entity records

Tasks:

Compare docs and implementation
Identify duplicate identity logic
Identify authority leakage
Verify deterministic lookup ownership
Recommend only minimal required fixes

Do not redesign surrounding architecture.

🧱 SESSION 3 — GAMEPLAY SYSTEM INTEGRATION

Only after lower stack stabilizes.

📄 FILES
Docs
00A
00B
00C

01
02
04
05
06 dialog
08 quest
09 perception
Code

Only gameplay-related modules currently being implemented.

Do NOT dump full repo.

🧠 SESSION 3 PROMPT

We are now integrating gameplay systems on top of stabilized lower layers.

Lower-layer authority boundaries are already established and should not be redesigned.

Gameplay systems must consume:

Event Log
Escalation outputs
ContextBuilder snapshots
Entity Resolution

without duplicating:

identity logic
visibility derivation
escalation evaluation
canonical world mutation

Tasks:

Verify gameplay systems consume lower layers correctly
Detect duplicated deterministic logic
Detect hidden authority drift
Preserve event-driven architecture
Recommend minimal fixes only

Avoid introducing cross-layer shortcuts.

🧱 SESSION 4 — UI CONTRACT
📄 FILES
00A
00B
00C
10 UI contract.md

Plus ONLY interfaces actually exposed to UI.

🧠 SESSION 4 PROMPT

We are validating UI contract boundaries only.

The UI is a consumer of authoritative runtime outputs.

The UI must not:

construct identity
infer canonical truth
mutate simulation state directly
bypass Event Log or Adjudication flows

Tasks:

Verify transport boundaries
Verify presentation-layer isolation
Verify deterministic outputs remain lossless through presentation
Identify hidden UI authority leakage

Do not redesign gameplay systems.

🧱 SESSION 5 — COMBAT

ONLY LAST.

📄 FILES

Combat-related docs/code only plus required lower-layer contracts.

🧠 SESSION 5 PROMPT

We are integrating the combat system on top of already stabilized lower layers.

Combat is treated as a stress test of:

event integrity
escalation behavior
context derivation
entity identity
gameplay orchestration

Combat must consume lower layers without bypassing them.

Tasks:

Verify combat event emission paths
Verify escalation interactions
Verify ContextBuilder integration
Verify deterministic authority boundaries
Detect hidden mutation paths or duplicate simulation logic

Prefer minimal integration fixes over redesign.

🧷 FINAL OPERATIONAL RULE

Every future session should start by stating:

We are in implementation stabilization, not architecture invention.

That one sentence alone will prevent a huge amount of drift.