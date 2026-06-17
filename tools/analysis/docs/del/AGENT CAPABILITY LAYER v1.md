AGENT CAPABILITY LAYER v1
==========================

STATUS: design proposal, not yet an execution checklist. Written 2026-06-17
to close out the design conversation that started from the determinism-test
fix and Bart's "the boundary is my memory" reframe. Once pieces of this are
accepted, they get tracked as normal line items in REFACTOR OPS BOARD.md /
Truth Kernel Board.md - this file should NOT become a 6th competing source
of status truth. Treat it like TRUTH KERNEL v1.md was treated: a spec that
gets implemented and then mostly stops changing.

WHY THIS DOC EXISTS
-------------------
Bart's framing, in his own words: "I don't want an incapable ai, I want a
capable software base enhanced with ai to make my life easier in using the
tool as an agent with all the things an agent can do." That is already the
Truth Kernel's stated principle ("the Truth Kernel is not allowed to invent
information" - Truth Kernel Board.md, PURPOSE) - this doc is about extending
that same deterministic-core-plus-AI-narration shape outward, not replacing
it with something fuzzier.

The concrete trigger: Bart half-remembered a design decision ("potentials
that collapse at trigger time") and asked me to check rather than trust his
memory. I found it (world_controller.py's potential_locations +
generate_location_from_potential, world_map.py's on-demand-generation
comment, travel_system.py's EncounterPoint.activate() + generate_encounter())
and also found a live gap (region_id is hardcoded None at creation, so
generate_location_from_potential always returns None right now - wired but
dead). That lookup-and-verify cycle IS the capability he's asking for. The
question is how to make it repeatable without me re-grepping from scratch
every time, and how to extend the same idea to ripple/impact analysis.

FOUR LAYERS - STATUS TODAY VS GAP VS PROPOSED
----------------------------------------------

1. KNOWLEDGE LAYER (what facts exist about the codebase)
   Today: graph_edges / symbol_references tables, populated by ingestion,
   scoped ONLY to tools/analysis itself. world/, engine/, resolver/,
   dungeon_neo/ etc. - the actual game code - have never been ingested.
   Gap: every question about the real game (like the potentials lookup
   above) currently has to be answered by ad-hoc grep, not by query,
   because the knowledge layer doesn't cover that code yet.
   Proposed: point ingestion at world/ + engine/ + resolver/ + dungeon_neo/
   (core/, og_system/, routes/, ai/ as a second pass). Same DB, same
   schema, just wider scope. No new design needed here - this is "run the
   thing we already have over more files."

2. REASONING LAYER (how facts get turned into answers)
   Today: the Truth Kernel query algebra (Select/Combine), 6 views
   (STRUCTURE/STABILITY/INTEGRITY/SUMMARY/SUBSYSTEM/ROLE), Assessor.ask()
   as the NL front door. Real, tested, 47 (now Bart reports 57 on his
   machine - see note below) regression tests passing.
   Gap: none structural. This layer is solid and the right foundation -
   nothing here needs to change to support what follows, it needs to be
   fed more (layer 1) and asked more (layer 4).

3. TRACKING LAYER (durable record of in-progress work across sessions)
   Today: doesn't exist yet in DB-backed form. REFACTOR OPS BOARD.md /
   todo-done.md are the closest analogue, but they're meta-tool notes, not
   a per-ripple work surface.
   Proposed: the task.md mechanism below.

4. CAPABILITY LAYER (the actual analyses on top of 1-3)
   Today: impact_query intent exists in api/oracle_router.py but its full
   semantics are UNVERIFIED - it's not yet confirmed whether it returns the
   complete transitive reverse-dependency closure of a target symbol, or
   only what the expansion-depth budget for the explainability trace
   happens to surface. This needs to be checked before anything below is
   built on top of it.
   Proposed: ripple/blast-radius analysis (true transitive closure, both
   directions - what calls this, and what this calls through to) as the
   first new capability, because it's the direct prerequisite for the
   task.md workflow Bart described.

THE TASK.MD PROPOSAL
---------------------
Bart's own workflow, stated directly: for a SIMPLE ripple (a rename, a
literal string that appears in a known-small set of places) he already has
the right tool - Sublime Text global search, navigate, edit. The tool
should not try to insert itself into that case; it would just be friction.

For a NON-simple ripple - where the chain includes pass-through logic,
indirect callers, or effects that a literal string search can't see (an
interface contract, a data shape, a behavior that changes meaning two
calls downstream) - that's where this is supposed to help. Not by guessing,
by enumerating the real chain from the graph and then giving Bart a
structured place to work through it "one at a time in order till we get it
fixed" - his words, including "hate to leave something broken."

So a task.md, generated from a ripple/impact query, should contain:
  - the target symbol/file and the query that produced this file (so it
    can be regenerated, not just read)
  - the full discovered chain: direct callers, direct callees, and
    transitive reach in both directions, distinguishing "local effect at
    this site" from "pass-through logic that itself needs to change"
  - one checklist line per affected site, each in a state: OPEN /
    IN PROGRESS / DONE / ABANDONED (with reason) - same state machine
    proposed earlier this session for durable backlog items, reused here
    rather than inventing a second one
  - nothing marked DONE on the file as a whole until every line is DONE or
    explicitly ABANDONED with a reason - no silent partial completion

The "when I reference them with the tool" requirement means re-opening a
task.md later has to do more than display the file: the tool should re-run
the query that generated it against current DB state and report drift -
sites that no longer exist, new sites that now match, anything that
changed shape since the file was written. Otherwise a task.md generated
last week silently goes stale exactly the way conversation memory does,
which defeats the point.

Open design question this doc does NOT resolve (see below): where these
files live and whether they're git-tracked.

BUILD ORDER (smallest safe slices, in dependency order)
---------------------------------------------------------
[ ] 1. Widen ingestion scope to world/ + engine/ + resolver/ + dungeon_neo/.
       No new code, just running existing ingestion over more files plus
       whatever path-config change that requires. Verify with a regression
       test that asserts a known real symbol (e.g. generate_location_from_
       potential) shows up in graph_edges after ingestion.
[ ] 2. Audit impact_query's actual semantics against real data: does it
       return the full transitive closure or only what the explainability
       trace's depth budget surfaces? Write this down as a fact either way
       before building on it - this is exactly the kind of "verify, don't
       assume" step this whole doc is about.
[ ] 3. If gap found in #2, fix or add a separate full-closure ripple query
       (both directions) as a new, explicit capability - not silently
       repurposing the explainability trace for a job it wasn't built for.
[ ] 4. Build the task.md generator off the ripple query from #2/#3.
       Markdown, plain checklist format, matching the existing doc voice
       (see REFACTOR OPS BOARD.md for the style to match).
[ ] 5. Build the "re-reference a task.md" path: read file -> extract the
       originating query -> re-run against current DB -> diff -> report.

OPEN QUESTIONS FOR BART
------------------------
1. Where should task.md files live - a new tools/analysis/tasks/ directory,
   git-tracked like the other docs? Or something more disposable/local that
   isn't meant to survive a `git status` check? (Affects whether stale,
   abandoned ones need cleanup tooling or just manual deletion.)

A: I'm good with putting them in our docs folder (same folder as this file)

2. Should ABANDONED require a reason every time, or is that overkill for a
   one-person backlog? (The persistence-design conversation proposed it for
   the durable-backlog case generally - confirming it should carry over
   here specifically.)

A: I'm not sure but if the AI isn't sure of the reason, it should ask the 
   user for one or if he says he doesn't care then whatever default you 
   like such as user ok'd or something like that.

3. For "pass-through logic" - is structural call-chain enumeration enough
   for v1, or do you want the existing contract/classification systems
   (see contracts + visibility.md) pulled in too, to flag behavioral/type
   risk along the chain and not just "this function is called from here"?
   Leaning toward structural-only for v1 per your own "don't let really
   really good be the enemy of this should work well" rule - flagging in
   case you disagree.

A: Since we are talking v1, we can make it simple and if more is needed we 
   add.
