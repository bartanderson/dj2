# SESSION STATE - session 37 handoff
_Overwrite completely each session. Not authoritative - see Determined/docs/TRACKER.md for truth._

## Determined status

All numbered items closed as of session 36. No open action items in TRACKER.md.

For Determined status, open items, and history, read these files directly:
- `C:\Users\bartl\dev\Determined\docs\TRACKER.md` - canonical open items + dashboard
- `C:\Users\bartl\dev\Determined\docs\HISTORY.md` - session-by-session history
- `C:\Users\bartl\dev\Determined\SESSION_STATE.md` - last session handoff

## What happened this session (session 37)

- dj2 TRACKER item 1 done: Ollama replaced with llama-server across all active game code
  - Created `dungeon_neo/llm_client.py` and `world/llm_client.py` (mirrors Determined shim)
  - Created `world/embedding_model.py` (module-level lazy singleton, mirrors Determined pattern)
  - Replaced all `self.ollama.generate()` call sites in `dungeon_neo/ai_integration.py`,
    `world/ai_integration.py`, `Scripts/context_manager.py`, `world_app.py`, `ai-first-success.py`
  - Removed `ollama` and `opentelemetry-instrumentation-ollama` from `requirements.txt`
  - `send_to_ollama` renamed to `send_to_llm` in context_manager
  - `opentelemetry-instrumentation-openai` already present -- covers llama-server (OpenAI-compat)
  - Smoke test passed: llama-server service running, `llm_client.chat()` returns responses
- Improvement methodology written to `Determined/docs/PRACTICES.md`
  - Documents run-observe-classify-fix loop
  - Deterministic -> semantic -> narrative layer order
  - Gaps surface to Bart before building

## dj2 current state

TRACKER.md is now empty -- no open game work items.
Bart has something new from other contributors to discuss next session.

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, packages installed directly (no venv), use `python`
llama-server: runs as a Windows service named "llama-server", health at http://localhost:8080/health
Use PowerShell tool (not Bash) for all server/Python commands.
