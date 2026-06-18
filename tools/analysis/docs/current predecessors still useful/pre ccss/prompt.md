STATUS NOTE (added 2026-06-17, Pass 2 read-only audit): this spec was
actually implemented. `tools/analysis/ccss - redesign into tool over
analysis db/pass1.py`/`pass2.py`/`pass3.py` follow this file_id/test_id/
symbol_uid identity model and PASS1->PASS2->PASS3 contract almost
verbatim. But PASS2 and PASS3 only satisfy the structural contract, not
the substance: PASS2's `enrich_symbol()` never produces fqdn/role/
confidence (pure passthrough), and PASS3's `gaps` output is hardcoded
empty - the actual coverage-gap detection this spec exists to produce was
never built. See TRACKER.md item 15 for the full finding and the open
decision (finish / integrate / shelve).

CCSS 3-PASS TEST ANALYSIS SYSTEM (CANONICAL SPEC v1.0)
0. GLOBAL INVARIANTS
File Identity
file_id = full relative file path from repository root

Example:

tools/analysis/tests/core/test_graph_analytics.py

file_id is the only valid file identity.

Test Identity
test_id = file_id + "::" + test_name

Example:

tools/analysis/tests/core/test_graph_analytics.py::test_graph_top_callees_and_callers

test_id is the only valid test identity.

Symbol Identity

Within each test:

symbol_index = 0-based encounter order during PASS 1 extraction

Global symbol identity:

symbol_uid = test_id + "::" + symbol_index

Example:

tools/.../test_x.py::test_runtime_resolution::7

After PASS 1:

symbol_uid is the only valid symbol identity.
Cross-Pass Rules

All passes must preserve:

file_id
test_id
symbol_index
symbol_uid

unchanged.

No pass may:

renumber symbols
reorder symbols
create symbols
delete symbols
merge symbols
split symbols
Execution Rules

Each run is:

stateless
deterministic
single-file

No cross-file reasoning.

No reuse of outputs from previous runs unless explicitly provided as input.

1. PASS 1 — STRUCTURE EXTRACTION
Purpose

Extract deterministic structural representation from source code.

Inputs
Python source file
file_id
Allowed Information

PASS 1 may inspect:

source code
AST

PASS 1 must not perform:

semantic interpretation
symbol classification
runtime resolution
cross-test reasoning
cross-file reasoning
Rules
AST-only extraction
preserve encounter order
no symbol deduplication
no symbol normalization
no semantic inference
Output
{
  "file_id": "string",
  "tests": [
    {
      "test_name": "string",
      "test_id": "string",
      "start_line": 0,
      "end_line": 0,
      "symbols": [
        {
          "symbol_index": 0,
          "symbol_uid": "string",
          "surface": "string",
          "context": "import | call | attribute | assignment | builtin | unknown",
          "line": 0
        }
      ]
    }
  ]
}
PASS 1 Contract

PASS 1 establishes:

file_id
test_id
symbol_index
symbol_uid

These become immutable for the remainder of the pipeline.

2. PASS 2 — SEMANTIC ENRICHMENT
Purpose

Attach semantic metadata without altering structure.

Inputs

PASS 2 may consume:

PASS 1 output only

PASS 2 must not inspect:

source code
AST
external files
PASS 3 outputs
Rules
preserve structure exactly
preserve ordering exactly
preserve identities exactly
add semantic metadata only
Output
{
  "file_id": "string",
  "tests": [
    {
      "test_id": "string",
      "semantic_tags": [
        "string"
      ],
      "symbol_annotations": [
        {
          "symbol_index": 0,
          "symbol_uid": "string",
          "surface": "string",
          "fqdn": "string | null",
          "role": "project | builtin | stdlib | runtime | external | unknown",
          "confidence": 0.0,
          "line": 0
        }
      ]
    }
  ]
}
Confidence Contract
0.0 <= confidence <= 1.0

Forbidden:

null
NaN
values outside range
PASS 2 Contract

PASS 2 may:

annotate
classify
resolve
tag

PASS 2 may not:

modify structure
modify identity
modify ordering
create symbols
remove symbols
3. PASS 3 — COVERAGE SYNTHESIS
Purpose

Compute coverage view from semantic results.

Inputs

PASS 3 may consume:

PASS 2 output only

PASS 3 must not inspect:

source code
AST
PASS 1 output directly
external files
Rules

PASS 3 is aggregation only.

PASS 3 must not:

reinterpret symbols
modify structure
infer new entities
infer new symbols
reclassify roles
modify fqdn values
modify confidence values
modify symbol ordering
Output
{
  "file_id": "string",
  "coverage": {
    "axes": {
      "structural": {
        "covered": [],
        "missing": [],
        "definition": "test presence plus symbol extraction completeness per test_id"
      },
      "semantic": {
        "covered": [],
        "missing": [],
        "definition": "symbol role assignment completeness per symbol_uid"
      },
      "runtime": {
        "covered": [],
        "missing": [],
        "definition": "runtime binding resolution existence per symbol_uid"
      }
    },
    "redundancy": [
      {
        "test_id": "string",
        "symbol": "string",
        "occurrences": 0,
        "scope": "test | file"
      }
    ],
    "gaps": [
      {
        "gap_type": "structural | semantic | runtime",
        "test_id": "string",
        "symbol_uid": "string | null",
        "description": "string"
      }
    ]
  }
}
4. IDENTITY MODEL

Hierarchy:

file_id
    ↓
test_id
    ↓
symbol_uid

These are the only authoritative identities in the system.

5. JOIN CONTRACT

Valid joins:

file_id
test_id
symbol_uid

Forbidden joins:

surface
line number
fqdn
symbol_index alone
test name alone
file basename
6. EXECUTION MODEL

For a single file:

PASS 1
  ↓
PASS 2
  ↓
PASS 3
  ↓
FINAL OUTPUT

Passes may only consume outputs from the immediately preceding pass.

7. ERROR CONTRACT
{
  "error": "contract_violation",
  "stage": "PASS_1 | PASS_2 | PASS_3",
  "reason": "string"
}
8. SYSTEM GUARANTEE

PASS 1:

structural truth

PASS 2:

semantic enrichment only

PASS 3:

coverage synthesis only

System guarantees:

no cross-pass mutation
no identity mutation
no inference beyond pass inputs
no cross-file coupling
deterministic execution
stateless execution