# SESSION STATE - session 65 handoff
_Overwrite completely each session. Not authoritative - see dj2/TRACKER.md for truth._

## Active branch: main
Clean state. No code changes this session.

## What happened this session (session 65)

### Housekeeping
- CLAUDE.md fixed: removed stale redirect to Determined's TRACKER for dj2 work
- SESSION_STATE.md fixed: updated "source of truth" pointer from Determined to dj2/TRACKER.md
- dj2/TRACKER.md populated with 7 backlog items (G1-G7) from Bart's desktop idea files

### Ideas ingested from desktop files
Six files reviewed and distilled into TRACKER items:
- enhancements to add to world-dungeon project.txt → G3, G4, G6, G7
- Gaia RAG and Narration.txt → G3
- Game NPC Voice AI - Kimi.txt → G6
- kitten TTS github or Owhisper in Hyprnote.txt → G6 (KittenTTS + FastRTC noted)
- dungeon and world decoration and overlays.txt → G2
- DnD addition.md → G5 (Semantic Genome)

### Items evaluated and dropped
- copapy: overkill for dice math, skip
- Google ADK: cloud-oriented, duplicates existing 7-phase architecture
- Critic quality loop for runtime narration: too slow at runtime, fine for offline batch
- dnd-character library: pending compatibility check before adopting

### Dependency chain confirmed
World (events wired) → Character Creation → World Exploration → Dungeon

## Next session priorities
1. G1: Analyze world event chain — find what's wired vs stub vs disconnected
2. G2: World decoration/overlay system (design is complete, ready to implement)
3. G3: NarrativeService (CONSEQUENCE phase narration, single-shot LLM)
4. G4: Conversational character creation (text-first, voice deferred)

G5 (Semantic Genome) and G6 (Voice) are designed but deferred until G1-G4 stable.

## Hardware facts (unchanged)
- llama-server-3b: NSSM auto service, port 8080
- llama-server-8b: NSSM manual service, port 8081
- Start 8B: `nssm start llama-server-8b` (admin PowerShell)

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, use `python`
Use PowerShell tool (not Bash). NEVER use python -c with inner quotes - write .py scripts.
