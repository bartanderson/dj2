# dj2 TRACKER

Active game work items. Finished items get deleted immediately; history goes to HISTORY.md if one exists.

---

## Item 1 — Replace Ollama with llama-server in game code

**Why:** Ollama ethically exploited llama.cpp open source project. Replacing with
llama.cpp's built-in llama-server (OpenAI-compatible, localhost:8080) consistently
across the codebase. Same migration already done in Determined repo.

**Pattern (mirror exactly what Determined did):**

1. Create `dungeon_neo/llm_client.py` — same shape as
   `Determined/determined/agent/llm_client.py`:
   - `generate(prompt, timeout) -> str | None`  — POST `/v1/completions`, returns `choices[0]["text"]`
   - `chat(messages, timeout) -> str | None`    — POST `/v1/chat/completions`, returns `choices[0]["message"]["content"]`
   - `is_available(timeout) -> bool`            — GET `/health`
   - `LLM_BASE_URL = "http://localhost:8080"`

2. Replace Ollama call sites in active game files:

   - `dungeon_neo/ai_integration.py`
     - Uses `from ollama import Client` and `self.ollama = Client(host=...)` 
     - `.generate()` calls at lines 385, 438, 482 — Shape 1 (`/v1/completions` → `generate()`)
     - Remove the `ollama` pip dependency from calls; import from `llm_client` instead

   - `Scripts/context_manager.py`
     - `send_to_ollama()` method (~line 510), `from ollama_client import ...` import
     - Rename to `send_to_llm()`, replace body with `llm_client.generate()` or `chat()`
     - Update callers at lines 498, 503-504

   - `world/ai_integration.py`
     - Check call shapes and replace consistently

   - `world_app.py`
     - Check call shapes and replace consistently

   - `ai-first-success.py`
     - Has `api_key="ollama"` at line 7 — check if this is an OpenAI-compat shim
       call that already points at localhost; may just need the URL/key updated or
       can be replaced with `llm_client.generate()`

3. Skip (archive/dead code — do not touch):
   - `archive/` — everything under here
   - `tools.old/` — everything under here, including `tools.old/ollama_client.py`

4. After all call sites updated: remove `ollama` from `requirements.txt` if present.

5. Verify: run whatever tests exist; do a manual smoke test with llama-server running.

**Reference:** See `Determined/determined/agent/llm_client.py` for the canonical shim.
Two Ollama API shapes map to two llama-server shapes:
- Ollama Shape 1: `/api/generate`, `resp["response"]`  → llama-server: `/v1/completions`, `choices[0]["text"]`
- Ollama Shape 2: `/api/chat`, `resp["message"]["content"]` → llama-server: `/v1/chat/completions`, `choices[0]["message"]["content"]`
