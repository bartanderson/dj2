Perception & Discovery System (v1 – backlog design)
Purpose
Define how hidden information becomes discoverable through player interaction and system resolution.

Hidden Entity Model
Hidden entities may originate from:
- location definitions
- encounter data
- dynamic EscalationEngine effects

Entities exist in states:
- visible
- hidden
- partially known


Player Actions
Player may trigger perception-related actions:
- look
- listen
- search
- investigate

Each maps to a resolution attempt.


Skill Resolution Layer
Resolution uses core system skills:
- Perception
- Investigation
- (future: stealth interaction modifiers)

Checks determine:
- success / failure
- partial success
- no result


DM / AI Override Layer
Narrative expansion layer may:
- surface latent details
- bias reveal timing
- enrich perception output
This does NOT alter canonical state.


Event Emission Contract
Perception results emit structured events:
- perception.check.resolved
- perception.entity.revealed
These feed into:
- Event Log (authoritative history)


Integration Points
Event Log
- records perception outcomes
ContextBuilder
- consumes perception signals
- updates:
	- unknown_threat_signals
	- hidden → visible transitions

Escalation Engine
- may influence perception difficulty or outcomes via effects


Scope Note (binding)
This system is:
- NOT FSM-related
- NOT generator-related
- NOT combat-related
It is a separate gameplay layer feeding ContextBuilder- 