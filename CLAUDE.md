# Project Context (read this first, every session)

## Identity
- Repo: https://github.com/bartanderson/dj2
- Local working copy (Bart's machine): `C:\Users\bartl\dev\dj2`
- This is a DM/AI dungeon-game project. The active work area is `tools/analysis/` —
  a static-analysis / code-graph engine intended to eventually power a real AI agent.

## Resuming a session
If `SESSION_STATE.md` exists at the repo root, read it first - it's a high-density
chat-resume snapshot (objective / constraints & stack / current status / next
steps) meant to let a brand-new chat pick up without replaying history. It is
**not authoritative**: it's a derived convenience layer, overwritten in full on
each update (never appended to), and gitignored as local scratch rather than a
reviewed deliverable. If it ever conflicts with TRACKER.md/DESIGN.md/HISTORY.md
below, those win - update SESSION_STATE.md to match them, not the reverse.

## Where to look for status, every session
Before doing anything else in `tools/analysis/`, read the docs in
`tools/analysis/docs/`:
- `DESIGN.md` - architecture and design: Truth Kernel / query algebra layers,
  the Authority Model, the shadow/observability layer, and the conceptual
  framing worth keeping from earlier exploratory drafts.
- `TRACKER.md` - the single source of truth for status, kept deliberately
  lean. A `## Dashboard` section at the very top gives an at-a-glance
  recently-done / now-next list - read this first. Below that: section 1
  holds the phase/tier status tables (engine refactor, Truth Kernel tiers,
  Truth verification phases); section 2 is a short operational summary of
  standing environment bugs (silent file truncation, stale `.pyc` caches -
  read this before debugging anything that "looks impossible"); section 3
  is open items / next steps, numbered in rough priority order - closed
  items are trimmed to "what shipped + proof," not re-argued in prose,
  since the fix is the embodiment of the design once it's in code and
  DESIGN.md reflects it. Updated in place (checkboxes, dated entries) as
  work lands - do not just re-derive status from conversation memory, read
  this file.
- `HISTORY.md` - the full historical record split out of TRACKER.md
  2026-06-18: the complete incident-by-incident write-tooling defect log,
  and the complete dated chronological session log (what actually
  happened, session by session). Nothing was deleted in the split, only
  relocated - read this when you need the full story behind a closed
  TRACKER item, not for current status.

These replaced five older per-topic docs (REFACTOR OPS BOARD.md, Truth
Kernel Board.md, Truth.md, TRUTH KERNEL v1.md, todo-done.md) plus a handful
of older exploratory/proposal docs. The consolidation was cross-checked
(2026-06-17, three independent passes) for anything factual that didn't make
it across before the old docs were removed - nothing was found missing.
If a stray reference to one of those old filenames turns up anywhere
(including elsewhere in this file), it's stale - DESIGN.md/TRACKER.md/
HISTORY.md is the current pointer.

These are git-versioned and human-reviewable on purpose: update them as part of
finishing work, so Bart can see what changed via `git diff`, and so a future session
(mine) doesn't need conversation history to know where things stand.

## Working agreement
- I (Claude) have direct read/write access to this folder when it's connected to a
  Cowork session — edit files in place, no patch files needed.
- I do NOT have git push/commit credentials and will not attempt to commit or push.
  Bart reviews changes (via git diff) and commits/pushes himself.
- I can run things in my own sandbox to verify (syntax checks, regression tests), but
  final confirmation on his actual Windows hardware is his to do, since some bugs
  (e.g. sqlite3 file-handle behavior) only reproduce there.
- Regression tests live under `tools/analysis/tests/regression/` — plain Python,
  `assert`-based `test_*` functions, runnable directly via `python3 file.py` or pytest.

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

## File writes (mandatory)
This session (2026-06-16/17) found that writes/edits to files in this repo can
silently fail to land on disk while every available signal still looks correct
- including the Read tool itself, which on at least one occasion (Truth.md,
2026-06-17) displayed ~130 lines of fully-formed, plausible content that had
never actually been written to disk at all. Both the Edit tool and full-file
Write tool calls have produced silent truncation (confirmed: a Write-tool
retry reproduced the exact same truncated byte count as a prior failed Edit) -
switching tools is not a fix, and trusting Read's in-context view is not a
safe verification step on its own.

**Current procedure (2026-06-18): use `tools/dev/safe_write.py` for every
write/edit to a file in this repo, instead of the Edit/Write file tools.**
It writes via temp-file + atomic rename, then reads the result back and
byte-compares it against what was sent in - all in one call, with no content
ever touching the historically-unreliable Edit/Write tool path:

    python3 tools/dev/safe_write.py <target_path> << 'EOF'
    <exact full file content, UTF-8>
    EOF

A printed `OK ... sha256=...` line means the write is confirmed landed; a
`MISMATCH` line (with the first differing byte offset) means don't trust the
file and re-run. Known tradeoff: this means whole-file rewrites rather than
small in-place patches, even for minor edits to large files - accepted
deliberately, since targeted in-place edits are exactly what the Edit tool's
truncation history affected.

If `tools/dev/safe_write.py` itself is ever unavailable or inapplicable, fall
back to the previously-documented manual procedure: write the intended content
to a temp file via bash heredoc and `diff` it against the real target file
(zero diff output = confirmed landed); for Python files pair this with
`ast.parse` as a cheap (but not sufficient on its own) sanity check.

## Status history
Session-by-session history (what changed, when, why, including the
silent-truncation incidents and the doc-consolidation/cleanup work) lives in
HISTORY.md (split out of TRACKER.md section 4, 2026-06-18) - read it there,
don't re-derive it from conversation memory, and don't duplicate it here: an
inline copy in this file will drift the moment HISTORY.md is updated and
this file isn't.

Next steps: see TRACKER.md's `## Dashboard` section for the at-a-glance
view, or section 3 ("Open items / next steps") for the full numbered,
priority-ordered list across the whole project.
