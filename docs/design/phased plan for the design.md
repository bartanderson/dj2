Revised Implementation Sequence (with Generator)
Phase 0 – Core Infrastructure (No FSMs yet)
Event Log (code already provided).

Escalation Engine (design done, code to write).

ContextBuilder (design done, code to write).

Entity Resolution (design done, code to write).

FSM Stack in AdjudicationEngine (small change).

These are independent of the generator. We can implement and test them manually. They are needed for any FSM to run.

Phase 1 – Prepare a Test FSM (Buy)
Convert the existing buy.json to a YAML specification (hand‑written by me, using the generator's YAML schema).

We already have working buy – we will use it as the golden reference.

Phase 2 – Build the Generator (v1)
Implement the generator (as described in the design) with the following minimum viable features:

Read YAML, output JSON (must be identical to existing buy.json except formatting).

Output a test file that passes.

No pathfinding yet – only create tests for transitions from the initial state (the simple case).

Validate the generator by regenerating buy and comparing. Manually examine the generated JSON and test file. Run the generated test; it must pass.

Phase 3 – Expand Generator Test Suite
Convert sell, barter, and encounter to YAML (using the same schema).

For each, run the generator and verify that the generated JSON matches the existing one (or adjust the JSON to match – but we want the generator to become the source of truth).

If differences occur, adjust the generator (or the YAML) until all existing FSMs can be regenerated correctly.

At this point, the generator is proven on four different FSMs.

Phase 4 – Generate Encounter FSM
The encounter FSM already exists (working in manual tests).

We will write its YAML specification, then use the generator to produce a fresh JSON and test file.

We will run the generated tests and manually verify the encounter still works.

This is a trial run for a non‑trivial FSM (multiple choices, guards, etc.).

Phase 5 – Generate Combat FSM
Write the combat YAML specification (based on our final combat design).

Use the generator to produce the JSON and test file.

Implement only the guard/action functions for combat (these are manual, but the FSM structure and tests are generated).

Run the generated tests; they should fail until we implement the guards/actions, then pass.

Because the generator was validated on simpler FSMs, we can trust the combat FSM structure.

Why This Works
Generator is built early but only on a simple test case (buy) to prove the basic translation works.

Generator is stress‑tested on multiple existing FSMs before being used for combat.

Combat benefits because its FSM and tests are generated, reducing the chance of errors.

You retain control by reviewing the YAML specifications (which are much smaller and easier to verify than code).

The only risk is that the generator might need enhancements to handle combat (e.g., guards, multiple source states). But because we built it on encounter (which already has guards and multiple transitions), we will have already addressed those capabilities.