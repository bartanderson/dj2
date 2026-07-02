# SESSION STATE - session 54 handoff
_Overwrite completely each session. Not authoritative - see Determined/docs/TRACKER.md for truth._

## Active branch: main (both repos)
Clean state. Committed.

## What happened this session (session 54)

### LLM services — both now NSSM services
- Renamed old `llama-server` service to `llama-server-3b` (delete+recreate; NSSM has no rename)
- Created `llama-server-8b` as new NSSM service (demand start, not auto)
- Both verified running simultaneously: port 8080 (3B) and 8081 (8B)
- Key lesson: use `""` not backticks for quoting in NSSM AppParameters from PowerShell
- Saved to memory: project_llm_services.md

### Evaluate kernel — built, tested, committed (Determined)
- New file: `determined/agent/evaluator.py`
  - `evaluate(claim, evidence_items, question, llm_fn) -> Judgment`
  - `retrieve_evidence(query, conn, surfaces, top_n, threshold) -> list[str]`
  - `Judgment` dataclass: verdict, reasoning, confidence, evidence_used
  - Verdicts: VIOLATES / CONFIRMS / EXPLAINS / MATCHES_PATTERN / UNRELATED / UNCERTAIN
  - Uses `chat()` not `generate()` — completion endpoint sees closing `}` as done
  - LLM unavailability raises RuntimeError (hard fail, not silent None)
  - Regex fallback parser for partial/malformed JSON from 3B
- Tests: 20 unit tests (no LLM), 3 live tests in tests/integration/
- All passing. Committed: cfcdd58

### evaluate_claim tool + corpus_synthesis gap filtering (Determined)
- `evaluate_claim(assessor, args)` in agent_tools.py
  - Args: claim, question (both required), surfaces (default: design_note), top_n (default: 5)
  - Wired into TOOLS and REGISTRY
- `_filter_gaps_by_design_intent(assessor, analysis_text)` helper
  - Splits 27B gap output on `---` separator into individual gap blocks
  - Evaluates each block title as a claim against design_notes
  - CONFIRMS/EXPLAINS -> filtered to noise section
  - VIOLATES/UNCERTAIN/UNRELATED -> kept as real gaps with verdict annotation
- Live test: Gap 1 (AI->Navigation) correctly filtered as EXPLAINS (90%)
- 353 regression tests passing. Committed: 06a3422

### MCTS reasoning architecture — saved to memory
- Future direction for unfamiliar domains (audio, images, etc.)
- evaluate() kernel is already the evaluator node — no retrofitting needed
- Rust/C++ search kernel + Python LLM calls design
- Memory file: project_mcts_reasoning.md

## Hardware facts (unchanged)
- GPU: NVIDIA RTX 3070 Ti, 8192MB VRAM
- llama-server-3b: NSSM auto service, port 8080, -ngl 0 (CPU only)
- llama-server-8b: NSSM manual service, port 8081, -ngl 99, ctx 4096
- Start 8B: `nssm start llama-server-8b` (admin PowerShell)
- Health: `(Invoke-WebRequest http://localhost:808X/health).Content`

## Corpus state (dj2)
- 154 files distilled, 268 design_notes ingested
- DB: C:\Users\bartl\dev\Determined\C_Users_bartl_dev_dj2.db

## Next session plan

### Phase 3: infer_behavior tool for undocumented symbols
Add `infer_behavior(assessor, args)` to agent_tools.py:
1. First: add role pattern library to corpus DB as kind='pattern' artifacts
   Roles: coordinator, boundary, pipeline-stage, adjudicator, factory, observer
   Use ingest_design_docs pattern or a small seed script
2. Assemble calling context for symbol: callers, callees, param names, file stem
3. retrieve_evidence(context_query, conn, surfaces=["pattern"], top_n=3)
4. evaluate(context_summary, evidence, "What role does this calling profile suggest?")
5. Returns role label + confidence + evidence
6. Wire into TOOLS, REGISTRY, test against known undocumented symbol in dj2

### Phase 4 (later): data flow tracing
Linear walk of call graph accumulating mutation state, evaluate at each step.
MCTS wrapper goes here when single-pass proves insufficient.

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, packages installed directly, use `python`
3B: NSSM service llama-server-3b, port 8080 (auto-starts)
8B: NSSM service llama-server-8b, port 8081 (manual: nssm start llama-server-8b)
Determined agent: .venv\Scripts\python.exe -m determined.agent.local_agent C_Users_bartl_dev_dj2.db
Active branch in both repos: main
Use PowerShell tool (not Bash). NEVER use python -c with inner quotes - always write a .py script.
