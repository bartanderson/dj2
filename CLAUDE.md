# Project Context (read this first, every session)

## Environment

- **OS**: Windows 11 - use **PowerShell** tool for all server starts, Python runs, and any command with a `C:\` path. Bash tool uses Git Bash and fails on Windows paths.
- **`&&` chaining**: Not valid in PowerShell 5.1. Use `; if ($?) { cmd2 }` or just `;`.
- **Python**: No `python3` on Windows. Use `python` or the full venv path (e.g. `.venv\Scripts\python.exe`). Full path is safest.
- **`python -c`**: Only works cleanly for single-line one-liners. Quoting across multiple lines on Windows is a pain. For anything beyond a trivial expression, write a `.py` script to the scratchpad and run that instead.
- **`/dev/null`**: Use `$null` in PowerShell (`2>$null` to suppress stderr).
- **Env vars**: `$env:VAR` not `$VAR` in PowerShell.
- **Paths with `~`**: Use `$env:USERPROFILE` or full path when passing to scripts.
- **Git and PowerShell** work normally; `ls`/`cat`/`rm` are aliased in PS but take different flags than Linux.



## SESSION START CHECKLIST — do this before anything else, every session

**Step 1 — Read SESSION_STATE.md**
Read `SESSION_STATE.md` at the repo root. This is the handoff artifact from the
prior session. It tells you what was done, what is next, and what is pinned.
Do not answer "what's next" or make any plan until you have read it.

**Step 2 — Verify recall is running**
Check the system-reminder at the top of the conversation for:
`SessionStart:startup hook success: Recall is active for this project.`
If it says recall is active, logging is running - no action needed.
If it does NOT say that, tell Bart immediately: "Recall is not running this session."
Do not proceed silently with recall inactive.

**Step 3 — Confirm memory is loaded**
The auto-memory index (`MEMORY.md`) is loaded automatically via the system context.
If Bart asks about prior decisions, preferences, or constraints, check memory entries
before answering - do not re-derive from conversation or guess.

These three steps are non-negotiable. Do not skip them. Do not reorder them.
Do not substitute TRACKER.md for SESSION_STATE.md.

---

## Identity
- Repo: https://github.com/bartanderson/dj2
- Local working copy (Bart's machine): `C:\Users\bartl\dev\dj2`
- This is a DM/AI dungeon-game project. The static-analysis / code-graph engine
  has been migrated to the Determined repo (`C:\Users\bartl\dev\Determined`).
  Active tool work happens there. This repo is now game code only.

## Resuming a session
If `SESSION_STATE.md` exists at the repo root, read it first - it's a high-density
chat-resume snapshot (objective / constraints & stack / current status / next
steps) meant to let a brand-new chat pick up without replaying history. It is
**not authoritative**: it's a derived convenience layer, overwritten in full on
each update (never appended to), and gitignored as local scratch rather than a
reviewed deliverable. If it ever conflicts with TRACKER.md/DESIGN.md/HISTORY.md
below, those win - update SESSION_STATE.md to match them, not the reverse.

If you suspect this file might be behind the most recent prior session - e.g. it
describes a decision as pending that context elsewhere suggests was already
made - cross-check before trusting it: use `mcp__session_info__list_sessions`
and `read_transcript` to read the latest prior session's actual outcome, rather
than guessing from this file's claims alone.

## Where to look for tool status
The analysis engine docs (DESIGN.md, TRACKER.md, HISTORY.md) now live in
`C:\Users\bartl\dev\Determined\docs\`. Read them there for tool status,
open items, and architecture decisions. Do not look for them here.

## DB management (standing rule)
The only DB that is never auto-deleted is `ai_context/knowledge.db` (unrelated
to the analysis tool). Corpus DBs for the analysis engine now live in
`C:\Users\bartl\dev\Determined\` - see that repo's CLAUDE.md for DB rules.

## Working agreement
- I (Claude) have direct read/write access to this folder when it's connected to a
  Cowork session — edit files in place, no patch files needed.
- I can run `git add` and `git commit` to commit completed work. I do NOT push -
  Bart runs `git push` when ready. Commit after each meaningful piece of work lands
  and tests pass. Ask if anything is unclear before committing. Never force-push or
  amend published commits.
- Before any multi-step sequence of tool calls, state in one short line what I am
  about to do so Bart can abort before I go sideways. Example: "Reading X, then
  editing Y." Skip this only for single-step actions.
- I can run things in my own sandbox to verify (syntax checks, regression tests), but
  final confirmation on his actual Windows hardware is his to do, since some bugs
  (e.g. sqlite3 file-handle behavior) only reproduce there.
- Regression tests for the analysis engine live under `Determined/tests/regression/`.
- Before ending any session that did substantive work, the last action is rewriting
  `SESSION_STATE.md` in full with current status and next steps - mandatory, not
  just a convention. A session that does real work and skips this leaves the next
  session relying on a stale snapshot it has no way to detect from the file alone.
  This is a standing instruction, not something to ask permission for each time -
  just do it as part of finishing the work.

## Design reference: The Shape of the System

The authoritative engineering philosophy for this project lives in Determined:
`C:\Users\bartl\dev\Determined\docs\sots.md` (source: https://shapeofthesystem.com/)

The 25 tenets are ingested into Determined's `knowledge.db` and surface automatically
via frame comparison when analyzing code. Consult them for architectural decisions:
new boundaries, resource management, irreversible operations, module interfaces.
Not for routine changes.

Resolution rule when tenets conflict: minimize cognitive load vs. bound blast radius,
weighted by who controls the input. Caller-controlled + wide blast radius: pay now.
Self-controlled + contained: defer, but write down why.

## Coding guidelines
General behavioral defaults, merged in 2026-06-18. These bias toward caution over
speed - for trivial tasks, use judgment rather than applying all of this ceremony.

1. **Think before coding.** State assumptions explicitly rather than guessing
   silently. If multiple interpretations exist, present them instead of picking
   one unannounced. If a simpler approach exists, say so and push back when
   warranted. If something is genuinely unclear, stop and ask rather than
   guessing.
2. **Simplicity first.** Minimum code that solves the problem - no speculative
   features, no abstractions for single-use code, no unrequested configurability,
   no error handling for impossible scenarios. If it could be a quarter the size,
   rewrite it.
3. **Surgical changes.** Touch only what the task requires. Don't "improve"
   adjacent code, comments, or formatting; don't refactor things that aren't
   broken; match existing style even when you'd do it differently. Remove
   imports/variables/functions that your own change made unused, but leave
   pre-existing dead code alone (mention it, don't delete it). Every changed
   line should trace directly to the request.
4. **Goal-driven execution.** Turn tasks into verifiable goals ("fix the bug" →
   write a test that reproduces it, then make it pass) and state a brief plan
   with a verify step per stage for multi-step work. Strong success criteria
   let work proceed without constant check-ins; weak ones ("make it work")
   force them.

## Encoding — em dash corruption
Bart has seen em dashes (—) come out as `ΓÇö` in these docs. That's the classic
mojibake of UTF-8 em-dash bytes (E2 80 94) being written or re-read through a
non-UTF-8 codepage (Windows OEM/CP437) somewhere in the write path. Avoid this:
- When writing/editing files in this repo (especially via bash heredocs or
  scripted rewrites), always encode explicitly as UTF-8 — never let a tool fall
  back to a system/OEM default encoding.
- After any bash-based rewrite of a doc that contains an em dash, verify the
  bytes round-tripped: `python3 -c "print('—'.encode('utf-8') in open(path,'rb').read())"`
  should print `True`. If it doesn't, the write path mangled it — fix before
  moving on, don't leave `ΓÇö` in committed-looking docs.
- When in doubt, prefer a plain hyphen (`-`) or rewording over an em dash in
  these docs — it's not worth the encoding risk for punctuation.

## Status history
Session-by-session history for the analysis engine lives in
`Determined/docs/HISTORY.md`. Next steps for the tool: see
`Determined/docs/TRACKER.md` Dashboard section.
