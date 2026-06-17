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
  files and on a small `Edit` to an existing file) with no error surfaced —
  the in-context view of the file looked correct while the on-disk bytes were
  cut short. If a `SyntaxError` shows up that the Read tool doesn't corroborate,
  verify with `wc -c` / `python3 -c "import ast; ast.parse(open(path).read())"`
  in the sandbox before trusting either side blindly, and rewrite via a direct
  bash heredoc/script if truncation is confirmed.

All 6 docs in `tools/analysis/docs/` (REFACTOR OPS BOARD.md, Truth.md,
Truth Kernel Board.md, TRUTH KERNEL v1.md, todo-done.md) were updated in place
to reflect the above — see those files for full detail, this is just the index.
Next-up item per REFACTOR OPS BOARD.md: DB-backed symbol discovery API as
unified bootstrap (Phase 2), and oracle_router expansion budget/weighting
tuning (Phase 1 remainder).
