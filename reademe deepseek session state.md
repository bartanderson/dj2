📦 COMPREHENSIVE SYSTEM STATE – dj2 + Determined
1. Architecture Overview
You have three integrated layers:

Design Source: C:\Users\bartl\dev\dj2\og_system\ – contains 19 JSON files (01_core.json, 04_magic.json, 07_encounter.json, etc.). This is the master design authority for the OG (Old Gamer) RPG system.

Game Runtime: A Flask + SocketIO application (world_app.py) backed by a PostgreSQL database (dungeon_worlds). Key directories:

world/ – Controllers, Managers, AI, and systems.

config/fsms/ – JSON finite state machine specs (encounter, trade, barter, buy, sell).

world/fsm/ – Python implementations of those FSMs (currently missing most).

world/context_builder.py – Provides context to FSMs; contains get_spell_from_db() (added by us) and _get_encounter_context (exists, but others missing).

Structural Analysis Tool: C:\Users\bartl\dev\Determined\ – the Determined project. It ingests dj2 into a .db corpus file and provides static analysis (call graphs, stubs, orphans). It has an Ask bar powered by a local LLM.

2. The Database (PostgreSQL – dungeon_worlds)
Schema: Extended with new reference tables.

spells – seeded from 04_magic.json (55 spells).

skills – seeded from 01_core.json (6 skills).

races, classes – tables exist but are not yet seeded (waiting for 02_classes.json, 03_races.json parsing).

Seeding Script: dj2\generate_og_db.py – connects via .env and populates these tables.

Connection: Uses world/db.py (a psycopg2 connection pool) for all DB access.

3. The LLM Server (llama-server)
Version: 0.1.2-dev (build 10549, commit b2e5e9b28). Built for CUDA 12.4.

Path: C:\Users\bartl\models\llama-server\llama-server.exe

Model: C:\hf_cache\hub\models--Qwen--Qwen3-VL-8B-Thinking-GGUF\...\Qwen3VL-8B-Thinking-Q4_K_M.gguf

Port: 8081

Known Issue: /v1/chat/completions returns 503. The working endpoint is /v1/completions.

Auto-launch: The Determined UI tries to launch it, but on Windows it fails unless cwd is set to the exe directory (we patched that in llm_client.py, but it's optional).

4. Determined UI Status
UI Path: C:\Users\bartl\dev\Determined\determined\ui\ui_server.py

Corpus Loaded: C_Users_bartl_dev_dj2.db – 158 files, 56 hot, 25 stubs, 105 duplicate names.

Ask bar: Currently unreliable because llm_client.py tries to use /v1/chat/completions. The fix is to change the chat function to use /v1/completions (this was tested and works).

5. dj2 Structural Checker (Python Tool)
We created a custom script:

Path: dj2\structural\check_fsms.py

Function: Validates structural symmetry between JSON specs (config/fsms/*.json) and Python classes (world/fsm/*.py), and checks for context getters in world/context_builder.py.

Last Output: Confirmed missing classes for EncounterFSM, TradeFSM, BarterFSM, BuyFSM, SellFSM, and missing getters for Trade, Barter, Buy, Sell.

6. What Is DONE (Checked Off)
☑ PostgreSQL tables created (spells, skills, races, classes).
☑ Seed script (generate_og_db.py) run – 55 spells and 6 skills inserted.
☑ get_spell_from_db() added to world/context_builder.py.
☑ FSM structural checker (check_fsms.py) created and tested.
☑ encounter.json fixed (added cond guards for fight and parley).
7. What Is PENDING (Action Items)
□ Scaffold missing FSMs: Use Determined UI's Shape tab → click Scaffold for Trade, Barter, Buy, Sell (Encounter too if missing).
□ Add context getters to world/context_builder.py:
_get_trade_context

_get_barter_context

_get_buy_context

_get_sell_context
(Follow the pattern of _get_encounter_context.)

□ Handle Combat ghost: Either create config/fsms/combat.json + Scaffold, or comment out _get_combat_context.
□ Optional: Patch Determined's llm_client.py to use /v1/completions if you want the Ask bar to work.
□ Optional: Seed races and classes from 02_classes.json and 03_races.json.
8. Known File Paths & Edits
File    Status  Notes
dj2/world/context_builder.py    Modified    Contains new get_spell_from_db() at the top.
dj2/generate_og_db.py   Created Seeds the DB from og_system/.
dj2/structural/check_fsms.py    Created FSM structural checker.
dj2/create_tables.py    Modified    Added spells, skills, races, classes tables + GIN indexes.
Determined/determined/agent/llm_client.py   Optional patch  To fix Ask bar, change chat() to use /v1/completions.
9. How to Pick Up Next Session
When we start again, I will need:

The output of python -m structural.check_fsms (so I know which FSMs are still missing).

Confirmation on whether you want to fix the Ask bar this session (requires the one-line patch) or ignore it.

Your goal for the session (e.g., "Scaffold all FSMs and add context getters" or "Write the CombatFSM spec").