# SESSION STATE - session 31 handoff
_Overwrite completely each session. Not authoritative - see Determined/docs/TRACKER.md for truth._

## What happened this session (session 31)

**Planning and grounding session -- no code written.**

Reviewed full open-item landscape for Determined. Decided to build items 9, 10, 19
in order, with a self-audit step as the validation gate for item 19.

Identified that SOTS tenets were wired into Determined's analysis tools but not
into the planning/coding workflow for building Determined itself. Closed that gap
by strengthening Determined's CLAUDE.md: sots.md is now a mandatory read before
any plan or design, same weight as the session checklist.

## FIRST THING NEXT SESSION

Work is in Determined repo. Start there.
Read Determined/SESSION_STATE.md for the full handoff.
Read docs/sots.md before planning (now mandatory per CLAUDE.md).
Then build item 9 (distillation pass).

## Current state

dj2: game code only, no active work this session
Determined: main branch, all committed and pushed, items 9/10/19 queued

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, separate venv
UI: python -m determined.agent.local_agent --ui then http://127.0.0.1:5050
Use PowerShell tool (not Bash) for all server/Python commands.
