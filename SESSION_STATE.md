# SESSION STATE - session 38 handoff
_Overwrite completely each session. Not authoritative - see Determined/docs/TRACKER.md for truth._

## Active branch: feature-epistemic (Determined repo)
Do NOT merge to main yet. Work below must be done first.

## What happened this session (session 38)

- Epistemic policy layer built and tested on feature-epistemic branch
- 21 new tests pass (epistemic math, decision boundary, hard-block regression)
- Ran against real dj2 corpus -- found 5 gaps, 3 are pre-merge blockers

## Gap findings from dj2 corpus run

Every query returns severity=0.55 regardless of question asked. Root cause:
EpistemicPolicy.analyze() only reads corpus-level views (whole codebase health),
so the LLM gate is permanently on/off for a given corpus -- not responding to
whether this specific query needs synthesis.

Raw dj2 view data:
- STRUCTURE: 7777 edges, top hotspot=('<module>', 372) -- noise symbol
- STABILITY: 143 stable, 0 unstable (clean corpus)
- INTEGRITY: 0 errors (clean corpus)
- SUMMARY: 7777 edges, 143 files
- ROLE: 143 files

Risk vector always: structure=0.35, scale=0.10, complexity=0.10, rest=0.0

## Next session: fix gap 1 (query-level signal) in epistemic_policy.py

Add three query-level dimensions to EpistemicPolicy.analyze() via an optional
`query_context` dict parameter (default None so existing tests keep passing):

```python
# New constants to add in the TUNABLE CONSTANTS section:
SEED_ZERO_RISK       = 0.25  # no seeds found = router blind = high uncertainty
SEED_SPARSE_RISK     = 0.10  # 1-3 seeds = weak grounding
SEED_SPARSE_MAX      = 3     # threshold between sparse and adequate
EXPANSION_SPARSE_RISK = 0.10 # expanded/seed_count < EXPANSION_RATIO_MIN = sparse graph
EXPANSION_RATIO_MIN  = 2.0   # minimum expansion ratio for adequate coverage
INTENT_INTERPRETIVE_RISK = 0.10  # debug_query/general_query = needs synthesis
INTERPRETIVE_INTENTS = {"debug_query", "general_query"}
```

query_context dict shape (built in Assessor.ask() from RouteResult):
```python
query_context = {
    "seed_count": len(route_result.seed_symbols),
    "expanded_count": len(route_result.expanded_symbols),
    "intent": route_result.intent,
}
```

Add to risk_vector in analyze():
```python
# Query-level signals (None if no query_context passed)
if query_context:
    seed_count     = query_context.get("seed_count", 0)
    expanded_count = query_context.get("expanded_count", 0)
    intent         = query_context.get("intent", "general_query")
    expansion_ratio = expanded_count / max(seed_count, 1)

    risk_vector["query_grounding"] = (
        SEED_ZERO_RISK   if seed_count == 0
        else SEED_SPARSE_RISK if seed_count <= SEED_SPARSE_MAX
        else 0.0
    )
    risk_vector["query_coverage"]  = (
        EXPANSION_SPARSE_RISK if expansion_ratio < EXPANSION_RATIO_MIN else 0.0
    )
    risk_vector["query_intent"]    = (
        INTENT_INTERPRETIVE_RISK if intent in INTERPRETIVE_INTENTS else 0.0
    )
```

In Assessor.ask(), pass query_context to policy.analyze():
- route_result comes from session().run_algebra() -> internally calls route_query()
- BUT run_algebra() doesn't return the RouteResult directly, it returns a dict
- The oracle result is at result["oracle"] (a QuerySessionResult)
- intent is at result["intent"], seeds at result["oracle"].seeds,
  expanded at result["oracle"].expanded
- So build query_context AFTER run_algebra() returns:

```python
query_context = {
    "seed_count":     len(result["oracle"].seeds),
    "expanded_count": len(result["oracle"].expanded),
    "intent":         result["intent"],
}
directive = policy.analyze(
    structure_view=views["STRUCTURE"],
    integrity_view=views["INTEGRITY"],
    stability_view=views["STABILITY"],
    summary_view=views["SUMMARY"],
    role_view=views["ROLE"],
    query_context=query_context,
)
```

## After implementing: validate like this

```python
cd C:\Users\bartl\dev\Determined
.venv\Scripts\python.exe -c "
from determined.oracle.db_oracle import DBOracle
from determined.assessor.assessor import Assessor
import json

oracle = DBOracle('C_Users_bartl_dev_dj2.db')
assessor = Assessor(oracle)

for q in [
    'what depends on DungeonAI',
    'what does process_command do',
    'what role does world_app play',
    'why is the game broken',
    'what does __init__ do',
]:
    result = assessor.ask(q)
    ep = result['epistemic']
    print(q)
    print('  intent:', result['intent'])
    print('  severity:', round(ep['severity'], 2))
    print('  grounding:', ep['risk_vector'].get('query_grounding'))
    print('  coverage:', ep['risk_vector'].get('query_coverage'))
    print('  intent_risk:', ep['risk_vector'].get('query_intent'))
    print()
" 2>&1 | findstr /V "Warning HF_TOKEN Loading it/s"
```

Severity should now differ across queries. A debug query with few seeds
should score higher than a surface query with many seeds.

## Also add tests for the new dimensions

Add to tests/test_epistemic_policy.py -- test that:
- query_context=None leaves risk_vector without query keys (backward compat)
- seed_count=0 adds SEED_ZERO_RISK to query_grounding
- seed_count=2 adds SEED_SPARSE_RISK
- seed_count=10 adds 0.0
- expansion_ratio < 2.0 adds EXPANSION_SPARSE_RISK
- debug_query intent adds INTENT_INTERPRETIVE_RISK
- role_query intent adds 0.0

## Other gaps (post-merge or after gap 1 validated)

Gap 2: noise symbols inflating structure/complexity risk
  - Fix: filter builtin_symbols from cycle detection and hotspot check
  - Structure view already receives builtin_symbols -- pass same set to policy

Gap 3: SCALE_THRESHOLD=10 fires for any real project
  - Fix: change to edge_count / file_count > 20 (avg edges per file)

Gap 4: confirm integrity view builds correctly (INTEGRITY line missing from output)
  - Quick: run assessor.integrity_view() directly and print

Gap 5: narrative prompt is generic
  - Fix: pass result["oracle"].expanded[:15] into prompt as real symbol nouns

## Two-terminal reminder
Determined: C:\Users\bartl\dev\Determined, venv at .venv\Scripts\python.exe
dj2: C:\Users\bartl\dev\dj2, packages installed directly, use `python`
llama-server: Windows service named "llama-server", health at http://localhost:8080/health
Active branch in Determined: feature-epistemic
Use PowerShell tool (not Bash) for all server/Python commands.
