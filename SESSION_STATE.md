# SESSION STATE - session 52 handoff
_Overwrite completely each session. Not authoritative - see Determined/docs/TRACKER.md for truth._

## Active branch: main (both repos)
Clean state. Committed.

## What happened this session (session 52)

### Model swap: 27B -> 8B for quality tier
- 27B (Qwen3.6-27B-Q4_K_M, ~15GB) could not generate in <120s on RTX 3070 Ti (8GB VRAM)
- Replaced with Qwen3-8B-Q4_K_M (~5GB, fits in VRAM entirely)
- File: C:\Users\bartl\models\gguf\Qwen_Qwen3-8B-Q4_K_M.gguf
- Bat file updated: C:\Users\bartl\models\start-quality-llm.bat
- Response time: ~5-9s for typical prompts

### Fixed: Qwen3 thinking mode emptying content field
- Qwen3 runs chain-of-thought by default: puts reasoning in reasoning_content, leaves content empty
- chat_quality() in llm_client.py now prepends /no_think to system message
- Fallback: reads reasoning_content if content is empty
- File: determined/agent/llm_client.py

### Fixed: distill_corpus producing garbage summaries
- Root cause 1: example in prompt was echoed verbatim for unrelated files
- Root cause 2: content[:800] input was already-bad chatbot output from summarizer
- Root cause 3: 3B ignoring "Output ONLY" instruction; going into chatbot/LaTeX mode
- Fix: new # {subject}\n{skeleton}\n\n# Purpose: prompt (code-comment framing)
- Fix: _source_skeleton() extracts import + class/def signatures only
- Fix: distill_corpus now reads source from disk instead of using stored content
- Fix: distill_corpus re-distills ALL rows to overwrite stale cache
- Re-ran distill_corpus: 154 files distilled, ~1-2s each
- File: determined/agent/agent_tools.py

### corpus_synthesis now works end-to-end
- Pass 1 (3B): 154 files -> 10 subsystems (AI, Database, Game State, Engine, I/O,
  Language Processing, Navigation, Narrative, Pathfinding, Questing)
- Pass 2 (8B): 7 architectural gaps found, stored as backlog item in corpus DB
- Result stored in workflow_items table, subject=corpus_synthesis::gaps (latest row)

## Hardware facts (unchanged)
- GPU: NVIDIA RTX 3070 Ti, 8192MB VRAM
- nvidia-smi path: C:\Windows\System32\nvidia-smi.exe
- 3B NSSM service: -ngl 0 (CPU only), port 8080
- 8B bat file: C:\Users\bartl\models\start-quality-llm.bat, port 8081, -ngl 99, ctx 4096

## Corpus state (dj2)
- 154 files distilled (fresh, good quality)
- DB: C:\Users\bartl\dev\Determined\C_Users_bartl_dev_dj2.db
- determined.cfg: fast_ctx=16384, quality_ctx=4096

## Next session plan

### Step 1: Read the stored corpus_synthesis gaps result
Write and run a .py script in scratchpad:
  import sqlite3
  conn = sqlite3.connect(r'C:\Users\bartl\dev\Determined\C_Users_bartl_dev_dj2.db')
  row = conn.execute("SELECT content FROM workflow_items WHERE subject='corpus_synthesis::gaps' ORDER BY created_at DESC LIMIT 1").fetchone()
  print(row[0])

### Step 2: Triage the 7 gaps
Decide which are real work items for dj2 vs noise (gap 6 AI->zoom is likely noise).
File real ones as TRACKER items in Determined/docs/TRACKER.md.

### Step 3: Wire corpus_synthesis into the UI (optional)
corpus_synthesis is CLI-only. Could expose via the dj2 tools panel.

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, packages installed directly, use `python`
3B: Windows NSSM service, port 8080, -ngl 0 (CPU)
8B: start C:\Users\bartl\models\start-quality-llm.bat, port 8081
Determined agent: .venv\Scripts\python.exe -m determined.agent.local_agent C_Users_bartl_dev_dj2.db
Active branch in both repos: main
Use PowerShell tool (not Bash). NEVER use python -c with inner quotes - always write a .py script.
