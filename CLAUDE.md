# Project Context (read this first, every session)

## Identity
- Repo: https://github.com/bartanderson/dj2
- Local working copy (Bart's machine): `C:\Users\bartl\dev\dj2`
- This is a DM/AI dungeon-game project. The active work area is `tools/analysis/` —
  a static-analysis / code-graph engine intended to eventually power a real AI agent.

## Where to look for status, every session
Before doing anything else in `tools/analysis/`, read the docs in
`tools/analysis/docs/`:
- `REFACTOR OPS BOARD.md` — the live execution checklist / phase plan. Source of truth
  for what's done vs open. Updated in place (checkboxes, dated notes) as work lands —
  do not just re-derive status from conversation memory, read this file.
- `Truth Kernel Board.md` — Tier 0-4 status for the Truth Kernel / query algebra track.
- `Truth.md` — Phase 0-6 verification plan for proving the Truth Layer is real.
- `TRUTH KERNEL v1.md` — design spec for the query algebra (AST/Validator/Executor/Compiler).
- `todo-done.md` — informal running notes, resolved items marked `[x]` with date.

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

## File write verification (mandatory)
This session (2026-06-16/17) found that writes/edits to files in this repo can
silently fail to land on disk while every available signal still looks correct
- including the Read tool itself, which on at least one occasion (Truth.md,
2026-06-17) displayed ~130 lines of fully-formed, plausible content that had
never actually been written to disk at all. Both the Edit tool and full-file
Write tool calls have produced silent truncation (confirmed: a Write-tool
retry reproduced the exact same truncated byte count as a prior failed Edit) -
switching tools is not a fix, and trusting Read's in-context view is not a
safe verification step on its own.

Mandatory procedure after every write/edit to a file in this repo, before
doing anything else (no other tool calls in between):
1. Have the exact intended final content available as a string, separate from
   whatever the Read tool currently shows.
2. Verify on the actual filesystem via the sandbox shell (`bash`), not via the
   Read/Edit/Write tools: write the intended content to a temp file and `diff`
   it against the real target file. Zero diff output = confirmed landed. This
   is the authoritative check - line/byte counts and tail snippets are a
   useful quick first pass but are not sufficient on their own, since a
   truncation can land at a plausible-looking boundary partway through.
3. For Python files, `ast.parse` is a cheap sanity check but catches only
   syntax-breaking truncation, not the dangerous variant that lands cleanly.
   Always pair it with the full diff in step 2.
4. If the diff shows any mismatch, do not retry via Edit or Write - go
   straight to a direct bash heredoc rewrite (`cat > path << 'EOF' ... EOF`,
   or `cat >>` for an append onto an already-confirmed-correct prefix), then
   re-run the diff to confirm.
5. Keep the em-dash UTF-8 round-trip check (above) as a supplement for docs
   that use em dashes, not a substitute for the full diff.

## Last known state (2026-06-16)
Morning: noise-filter unification (oracle/symbol_noise.py, used at both discovery
and expansion time), removal of dead `_apply_intent_weights` stub, QuerySession
history now persisted to a `query_sessions` DB table. Regression suite added:
`tests/regression/test_oracle_router_persistence_lock.py`.

Later same day — agent-readiness gaps closed (per Bart's "fix it once the right
way and make sure it stays fixed" mandate):
- SUMMARY and SUBSYSTEM Truth Layer views (previously orphaned, zero real callers)
  wired up via `Assessor.summary_view()`/`subsystem_view()`/`all_views()`
  (`assessor/assessor.py`). All 5 views now run on real DB-backed data.
- `QuerySession.run_algebra()` (previously zero callers anywhere) now has a real
  front door: `Assessor.ask(text)`, called from the new CLI entrypoint
  `tools/analysis/ask.py` — `python tools/analysis/ask.py <db_path> "<question>"`.
  Run successfully end-to-end against the real project DB.
- Deleted the legacy dead-end agents (`oracle/agent.py`, `oracle/nl_agent.py`) and
  their only consumers (`tests/debug/oracle_compare_harness.py`,
  `truth/test_harness.py` — a non-asserting print-only runner). `ask.py` /
  `Assessor.ask()` is the "something better" that replaced them, per Bart's
  explicit conditional approval.
- New permanent regression test:
  `tests/regression/test_run_algebra_end_to_end.py` (4 assert-based tests against
  a real seeded sqlite DB — all 5 views, the algebra executing against
  SUMMARY/SUBSYSTEM specifically, `ask()` running end-to-end, `ask()` being
  deterministic). Full sweep confirmed passing together: this new suite (4) +
  `test_oracle_router_persistence_lock.py` (6) + `truth/tests/test_query_algebra.py`
  (32) = 42/42.
- Caught and fixed an environment bug along the way: this session's tooling
  silently truncated a file mid-write more than once (both on brand-new large
  files and on a small `Edit` to an existing file) with no error surfaced -
  the in-context view of the file looked correct while the on-disk bytes were
  cut short. See "File write verification (mandatory)" above for the
  procedure this grew into.

## 2026-06-17 — ROLE view added, doc-write verification protocol hardened
- Closed Truth.md Phase 3 Row 1/Row 2 (the "what is the purpose of this
  file" gap): added ROLE as a 6th Truth Layer view
  (`truth/views.py:build_role_view()`, wraps the already-real
  `Assessor.responsibility_map()`), wired into `Assessor.all_views()`,
  routed via a new `role_query` intent in `api/oracle_router.py`. New
  regression suite `tests/regression/test_role_view_routing.py` (5 tests).
  Full sweep: 47/47 passing. Full detail: REFACTOR OPS BOARD.md
  2026-06-17 entry, Truth Kernel Board.md Tier 1 "Role View" entry,
  Truth.md Phase 4 entry, todo-done.md 2026-06-17 entry.
- Hit silent truncation twice more while landing the above (in
  `api/oracle_router.py` and `tests/regression/test_run_algebra_end_to_end.py`),
  plus a separate stale/locked `.pyc` cache bug that made `_detect_intent`
  silently run old bytecode after the source was already fixed. Both are
  written up in REFACTOR OPS BOARD.md's 2026-06-17 entry.
- While updating the docs themselves, found a third and more concerning
  case: the Read tool displayed a fully-formed "Phase 3 findings" section
  in Truth.md that had never actually been written to disk (confirmed via
  `wc -l` against the real file). Recovered the content and wrote it for
  real via bash heredoc, verified by direct diff against disk. This is
  the incident that prompted the "File write verification (mandatory)"
  section above - the short version is: Read-tool-shows-it is not
  evidence it's on disk, only a bash-side diff against intended content is.

Next steps: see the "NEXT STEPS" section at the bottom of
REFACTOR OPS BOARD.md (consolidates both the original Phase 1/2 critical
path and the new Truth Kernel candidates) and Truth Kernel Board.md's
Tier 1/Tier 2 2026-06-17 notes. Don't restate specifics here - those two
files are the source of truth and this index will drift if it tries to
duplicate them.
