Gave deepseek search from text Determined

for context and then gave it GETTING_STARTED.md README.md and DESIGN.md
I ran
python -m determined.ui.ui_server

we started with where to start, it had me click open spec in top item FSM-SPEC EncounterFSM and click Open spec

It helped me create a tool, because seeing the text isn't enough to tell me what to do.
python -m structural.check_fsms

-- second run after ghost fix
C:\Users\bartl\dev\dj2>python -m structural.check_fsms
dj2 Structural FSM Checker
==================================================

❌ Barter: Class BarterFSM not found in C:\Users\bartl\dev\dj2\world\fsm

❌ Buy: Class BuyFSM not found in C:\Users\bartl\dev\dj2\world\fsm

❌ Encounter: Spec issues
   • Transition 'fight' from 'awaiting_choice' to 'resolving_fight' has action(s) ['start_combat'] but NO guard (cond).
   • Transition 'parley' from 'awaiting_choice' to 'completed' has action(s) ['resolve_parley'] but NO guard (cond).

❌ Sell: Class SellFSM not found in C:\Users\bartl\dev\dj2\world\fsm

❌ Trade: Class TradeFSM not found in C:\Users\bartl\dev\dj2\world\fsm

Ghost Detection (Context getters without specs):
   🚫 GHOST: `_get_combat_context references` 'combat' but no spec exists at C:\Users\bartl\dev\dj2\config\fsms\combat.json

==================================================
❌ Some structural issues found. See above for details.
💡 Tip: Fix missing context getters, add guards to transitions, or scaffold missing classes.