📦 00C IMPLEMENTATION_SEQUENCE.md (GOOD ENOUGH VERSION)

⚠️ Status This document is non-authoritative execution order only.
It does not define system architecture or invariants.
It exists only to keep implementation order stable.
It may be updated or discarded at any time.

🧠 Minimal rule for using this file
Use it only to answer:
	“what do I build next?”
Not:
	why architecture works
	how systems interact
	what is authoritative

🧭 Build Order (current working sequence)

1. Core truth layer

Event Log (01)

Escalation Engine (02)

👉 Nothing else matters until these are working together.

2. World interpretation layer

ContextBuilder (04)

Entity Resolution (05)

👉 Defines what the world means and what exists

3. Gameplay logic layer

Dialog System (06)

Quest System (08)

Perception & Discovery (09)

👉 Consumes world + events + entities

4. Tooling (non-runtime)

FSM Generator (07)

👉 Helps build systems, not part of runtime execution

5. Interface layer

UI Contract (10)

👉 Defines engine → UI data shape only

6. Simulation stress layer

Combat System (11)

👉 Depends on full system stability

🧷 Skipped / deferred work

If anything is not being built yet, it is implicitly a todo or in system design docs

---

✔ Why this version will hold up

This avoids your future “why is this file messed up?” moment because:

no branching explanation layers
no dependency theory
no duplicate categorization
no hidden authority creep
no “future architecture hints”

It is just: ordered execution steps with no ambition

A useful mental check going forward:

If a document answers “what must always be true?” → it belongs in 0A / 0B
If it answers “what do I build next?” → it belongs in the sequence file
If it starts explaining why the system exists the way it does → it’s probably drifting into the wrong layer
