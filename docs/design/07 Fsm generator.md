Specification-Driven FSM Generator
Original Plan (coalesced)
We will build a standalone tool:
	scripts/generate_fsm.py

It reads a YAML specification (e.g., buy.yaml) and produces:
- config/fsms/{name}.json → ready for GenericFSM
- tests/integration/test_{name}.py → pytest test file
Test files follow the pattern of test_economy.py using parameterized transitions.


Viability
- Scope: narrow, well-defined transformation pipeline
- Works against existing FSMs: buy, sell
- Low complexity:
	- no templating engine
	- simple string + JSON generation
Deterministic output guaranteed


Capability
- Implementation time: ~2–3 hours
- Risks:
	- edge cases (list-from states, multi-actions)
- Mitigation:
	- explicit handling + test coverage
- Runtime separation:
	- tool is external to game system
	- must be updated if JSON schema changes

Implementation Steps
1. Define YAML schema:
	- states
	- events
	- transitions
	- guards
	- actions
	- prompts
2. Implement generate_fsm.py:
	- parse YAML
	- emit JSON (json.dump(indent=2))
	- generate pytest file per FSM
3. Validation loop:
	- run on buy.yaml
	- compare to existing buy.json
	- convert sell.yaml similarly
	- ensure parity with existing FSMs
4. Documentation:
	- write docs/generator.md


After Generator Validation
Once validated:
- convert all FSMs to YAML:
	- barter
	- encounter
- future FSMs:
	- combat
	- dialogue
	- quests

become YAML-first
- JSON becomes generated artifact only
- manual FSM test writing is eliminated


Scope Note (binding)
This system is a tooling layer, not runtime architecture.

It is implemented AFTER core systems:

- Event Log
- Escalation Engine
- ContextBuilder
- Entity Resolution
- Dialogue
- Quests
- Combat- 