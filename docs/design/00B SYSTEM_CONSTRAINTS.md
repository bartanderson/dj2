This document defines system-wide invariants, architectural boundaries, and cross-layer execution contracts.

It contains constraints that apply across multiple subsystems and must remain globally consistent regardless of local implementation details.

Subsystem-specific behavior, algorithms, and internal implementation details belong in their respective design documents. This document defines only:
- cross-system responsibilities
- execution ordering guarantees
- authority boundaries
- non-negotiable architectural rules

Any future departure from these constraints must be explicitly documented and justified.
--
1. EventLog Injection Over Global Singleton (2026-04-30)
Decision:
EscalationEngine receives an explicit EventLog instance via its constructor, instead of calling get_event_log() internally. AdjudicationEngine creates the singleton once and passes it down.

Rationale:

Eliminates hidden global state, making dependencies explicit.

Enables deterministic testing (isolated event logs per test).

Prevents split‑brain issues where different components might use different log instances.

Impact:

All tests that instantiate EscalidationEngine must now pass an EventLog (usually obtained via get_event_log()).

The global reset_event_log() function is used only for test isolation.

2. Depth Propagation Rule (2026-04-30)
Decision:

Only events emitted by EscalationEngine.emit_event() increase depth (parent_event.depth + 1).

Events emitted by AdjudicationEngine (or any other system) use depth = 0 (new causal root).

process_event discards events with depth >= MAX_DEPTH (default 10).

Rationale:

Escalation is the only component that can cause infinite loops; depth is a guard against cascades.

Adjudication represents authoritative state changes and should start fresh causal chains.

Keeps reasoning simple: “depth > 0 means this event originated from an escalation rule.”

Impact:

Integration tests verify [0, 1, 0] event depth sequences.

Future combat or dialogue FSMs must not manually increase depth unless they are escalating.

3. Visibility Contract: WorldController.get_entities_in_location() (2026-04-30)
Decision:
WorldController must implement:

python
def get_entities_in_location(self, location) -> set[str]:
    """Return a set of entity IDs present in the given location."""
ContextBuilder uses this method to obtain the set of candidate entities for visibility. It does not receive full entity objects at this stage.

Rationale:

Separation of concerns: location membership is a spatial query, not perception.

Performance: sets of IDs are cheap to copy and manipulate.

Future changes (lighting, stealth) will require per‑entity attributes, which can be retrieved via a separate get_entity(entity_id) method when needed.

Impact:

WorldController must provide this method (currently stubbed in mocks).

ContextBuilder does not directly store entity objects; it uses IDs and later looks up details for the final visible_entities output.

4. Lighting and Darkvision (v1 Threshold) (2026-04-30)
Decision:

Each location has a lighting attribute (float 0.0 … 1.0).

lighting >= 0.3 → considered “lit”.

lighting < 0.3 → considered “dark”.

Characters have a boolean has_darkvision.

Visibility rule:

If lighting >= 0.3 or has_darkvision → all entities in the location are visible.

Otherwise (dark, no darkvision) → only the character themselves is visible.

Rationale:

Provides a simple, deterministic perception model that depends on environment and character traits.

Avoids premature complexity (distance, cone of vision, etc.) until stealth is added.

Impact:

`ContextBuilder._compute_visibility` now implements this conditional logic.

Unit tests for lighting scenarios (lit, dark, dark+darkvision) are required.

5. Entity Reference Convention for Event Salience (2026-04-30)
Decision:
Events that need to be considered “salient” by the ContextBuilder must include one or more of the following fields in their data dictionary:

entity_id – primary subject (e.g., killed creature, buying character)

target_id – secondary object (e.g., target of attack, item bought)

involved_entities – list of IDs when many are affected (e.g., area effect)

Rationale:

Allows ContextBuilder to determine if an event involves a currently visible entity without hard‑coding every possible event type.

Creates a uniform, extensible way to filter events for AI context.

Impact:

All event emissions in AdjudicationEngine (purchase, combat, etc.) must add these fields as appropriate.

Future FSM actions (dialogue, quests) must follow the same convention.

6. Removal of Global get_event_log() from EscalationEngine (2026-04-30)
Decision:
EscalationEngine no longer calls get_event_log() internally. It only uses the event_log instance passed to its constructor.

Rationale:

Enforces dependency injection and prevents accidental use of the wrong log instance.

Makes the component fully testable in isolation.

Impact:

All references to get_event_log() inside escalation_engine.py have been replaced with self.event_log.

The static helper EscalationEngine.emit_event was converted to an instance method that uses the injected log.

Next Steps
Any future departure from these decisions must be justified and added to this log. Before implementing stealth, combat targeting, or additional perception features, review the relevant entries to ensure consistency.


7. Session & Identity Management (2026-05-02)

**Context:** Bugs occurred where some endpoints worked while others failed due to inconsistent session resolution (e.g., party creation using URL session vs cookie session).

**Decisions:**

1. **Single source of session truth** – Only the HTTP cookie `session_id` determines identity. No query parameters, no request body injection, no fallback chains in production paths.

2. **Server‑side session map as authoritative runtime state** – `world_controller.session_players[session_id] → player_id → active_character` is the sole binding. Mutated only by authenticated flows (e.g., `/api/select-player`), never inferred from payload.

3. **UI must never construct identity state** – Frontend sends only `player_id`, `party_name`, and commands. It does **not** send `session_id` or binding info.

4. **Endpoint consistency** – All world mutation endpoints assume identity is already resolved before handler logic runs, using a central resolver (e.g., `session_id = request.cookies.get("session_id")`), not scattered per‑endpoint.

5. **Debugging principle** – When multiple systems “sometimes work” depending on entry point, the cause is duplicated identity resolution paths. The fix is to remove parallel identity systems, not patch symptoms.

**Current risk:** `session_players` is in‑memory only; server restart or multi‑worker deployment will lose identity. This is acceptable for v1 but must be flagged.

8. Decision: Adjudication Output Is Lossless Through Presentation Layer
Statement

All outputs produced by the deterministic adjudication layer must pass through the presentation/narration layer without modification or omission.

Required fields (minimum)
map_data
action
salient_events
Rules
The AI layer may augment text only
The AI layer may not alter, filter, or reinterpret structured outputs
Transport objects must remain bit-for-bit intact

9. EscalationEngine Authority Boundary (2026-05-08)
Decision:
EscalationEngine may influence interpretation, salience, and perception context, but must not mutate canonical entity resolution structures or core WorldState directly.

Escalation effects may:
- influence ContextBuilder visibility interpretation
- mark events as salient
- inject contextual overlays
- emit additional events

EscalationEngine must not:
- modify EntityResolver indices
- alter synonym mappings
- override embedding similarity
- rewrite canonical entity data
- mutate WorldState outside approved adjudication flows

Rationale:
Escalation represents deterministic rule-driven interpretation layered over authoritative simulation state. Allowing escalation to directly mutate canonical lookup systems would collapse separation between simulation truth and contextual interpretation.

Impact:
- EntityResolver remains deterministic and index-driven
- ContextBuilder becomes the integration layer between escalation and perception
- Escalation effects function as overlays rather than source-of-truth mutations

10. ContextBuilder Escalation Ordering Contract (2026-05-08)
Decision:
EscalationEngine perception-related effects must be applied before ContextBuilder visibility and awareness derivation steps.

Once visibility computation begins, no additional escalation effects may alter visibility results during the same build cycle.

Escalation effects injected later in the pipeline are informational only and must not retroactively modify derived perception outputs.

Rationale:
This preserves deterministic context construction and prevents timing-dependent visibility inconsistencies.

Impact:
- Visibility is computed exactly once per build cycle
- Escalation cannot produce post-derivation visibility mutation
- ContextBuilder remains a deterministic single-pass pipeline

11. Escalation → ContextBuilder Execution Model (2026-05-08)

EscalationEngine does not directly modify computed perception outputs.

Instead, it produces deterministic EscalationEffects that are consumed by ContextBuilder as input data during a single ordered evaluation phase.

ContextBuilder is the only system that computes:

visibility
awareness
knowledge gaps
salience filtering

EscalationEngine may only:

provide modifiers
flag entities/events
inject contextual signals

It may NOT:

directly override computed visibility results
directly alter salience inclusion results
directly mutate derived ContextBuilder outputs

All perception outputs are computed once per build cycle in ContextBuilder.