FUTURE SYSTEM INTERFACE – NOT ACTIVE YET
When we get ready for it, PyWry might be useful for ui contract as a display/interface option. There are undoubtedly others and it is a fairly narrow case but looked interesting

Timing (still important)

You’re early, and you said it yourself.

So the practical answer is:

Don’t integrate it yet

But do this instead:

Define your “UI contract” now

Even before PyWry, define:

Engine → UI:
    - narrative_output
    - world_state_snapshot
    - player_state
    - visible_entities

UI → Engine:
    - raw_input_text
    - meta_commands

If you get this right:

PyWry becomes a plug-in later
or you can swap it entirely if needed
My Take (direct)

You were right to hesitate.

It doesn’t unlock your core problem
It doesn’t help you design your engine
It doesn’t replace any subsystem

But:

It will make your system usable and inspectable once the core works.

If You Want Next Step

The most valuable thing we can do right now is:

design your UI contract + event schema

That’s the piece that determines whether:

PyWry integrates cleanly later
or becomes a refactor nightmare

If you want, I’ll draft that in a way that plugs directly into your current engine structure.