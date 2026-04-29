TODO: Specification‑Driven FSM Generator
Original Plan (coalesced)
We will build a standalone tool scripts/generate_fsm.py that reads a YAML specification (e.g., buy.yaml) and produces two files:

config/fsms/{name}.json – ready for GenericFSM.

tests/integration/test_{name}.py – a pytest test file following the same pattern as test_economy.py, using parameterization for transitions.

Viability (9/10)
Narrow scope, well‑understood mapping.

Testable against existing FSMs (buy, sell).

Low complexity: no Jinja, simple string operations and json.dump.

Deterministic output.

Capability (8/10)
I can implement it within 2–3 hours.

Risk of edge cases (list from, multiple actions) – manageable via explicit handling and testing.

Tool is separate from game runtime; must be maintained if JSON schema changes.

Implementation Steps (after all designs approved)
Define YAML schema (states, events, transitions, guards, actions, prompts).

Write generate_fsm.py that:

Parses YAML.

Outputs JSON (using json.dump with indent 2).

Outputs test file with parameterized test methods for each transition.

Validate by running on buy.yaml and sell.yaml (convert existing JSON to YAML first) and ensuring the generated JSON matches the original and tests pass.

Document usage in docs/generator.md.

After Generator is Validated
We will convert all existing FSMs (barter, encounter) to YAML specifications.

For new FSMs (combat, dialogue, quests), we will write YAML first, then generate JSON and tests.

Manual test writing will be eliminated for FSMs.

This TODO will be addressed after the core designs (Event Log, Escalation Engine, ContextBuilder, Entity Resolution, Dialogue, Quests, Combat) are completed and implemented. The generator is a productivity tool, not a core runtime component, so it can be built later.

todo
Create a new design document for Perception & Discovery (v1) that specifies:

How hidden entities are defined (in location definitions, encounter data, or dynamically via escalation).

Player actions (look, listen, search, investigate) and their mapping to skill checks.

Resolutions using OG System skills (Perception, Investigation, etc.).

DM AI override (latent expansion) for narrative reveals.

Integration with Event Log (emitting perception.check.resolved, perception.entity.revealed).

Feeding into ContextBuilder (adding signals to unknown_threat_signals or moving entities from hidden to visible).

I will produce the Perception & Discovery design document after confirming with you. Once all designs are approved, we will implement in the agreed order (Event Log → Escalation → ContextBuilder → Entity Resolution → Perception & Discovery → Dialogue → Quests → Combat). The generator TODO remains after all designs are done.