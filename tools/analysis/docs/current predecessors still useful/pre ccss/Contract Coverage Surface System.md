1. Core system name
Contract Coverage Surface System (CCSS)

Purpose:

A read-only analysis layer that maps existing tests onto predefined contract areas and reports coverage gaps.

2. Hard constraints (non-negotiable invariants)

These define the “shape of safety”:

C1 — No inference beyond observation

The system may:

read tests
extract signals
map to known contract areas

It may NOT:

invent behavior
propose new architecture
generate new tests
infer missing semantics beyond labels
C2 — Contract-first axis definition

All classification axes come from:

tool_system_contract.json
SemanticPipelineContract
explicitly defined runtime binding rules

NOT from tests.

C3 — Tests are immutable facts

Tests are:

not rewritten
not normalized
not “improved”
only parsed
C4 — Output is read-only

System outputs:

coverage maps
gap reports
overlap reports

No mutations.

3. Core objects (minimal ontology)
3.1 ContractAxis
ContractAxis = a named dimension of system behavior defined by contract specs

Examples:

runtime_binding
identity_resolution
classification
routing
persistence

Source:

contract files only
3.2 TestSignal
TestSignal = a single observation extracted from a test that touches a ContractAxis

Fields:

test_name
contract_axis
symbols_touched
assertion_type (optional lightweight label)
3.3 CoverageNode
CoverageNode = aggregation of TestSignals for a single ContractAxis

Fields:

axis
covered_symbols
test_count
signal_list
3.4 CoverageGap
CoverageGap = difference between contract-defined capability space and observed test coverage

Fields:

axis
missing_capabilities
severity (optional later)
3.5 CoverageGraph
CoverageGraph = full mapping of all ContractAxes → CoverageNodes → CoverageGaps

This is the final output structure.

4. Core processes (pipeline definition)
P1 — Contract Extraction
Input: contract definitions
Output: ContractAxes

Rules:

deterministic
no test knowledge
P2 — Test Scanning
Input: raw test files
Output: TestSignals

Rules:

extract assertions
extract referenced symbols
label only via known axes
P3 — Mapping
Input: TestSignals + ContractAxes
Output: CoverageNodes

Rules:

purely relational
no inference
P4 — Gap Detection
Input: CoverageNodes + ContractAxes
Output: CoverageGaps

Rules:

set difference only
no interpretation
P5 — Reporting
Input: CoverageGraph
Output: human-readable diagnostics

Rules:

descriptive only
no recommendations (important)
5. Data flow (full system picture)
Contracts ──► ContractAxes
                  │
Tests ───────────► TestSignals
                  │
                  ▼
           Coverage Mapping
                  │
                  ▼
           CoverageGraph
                  │
                  ▼
            Gap Report
6. What “good behavior” looks like

A correct system:

always knows what axes exist
always shows what tests cover
always shows what is missing
never tries to fix anything
7. What “bad behavior” looks like (anti-spec)

If any of these appear, system is broken:

“this test likely implies X”
“we should add test for Y”
“this architecture seems better”
“inferred missing behavior”
any mutation of contract space
8. Expansion rule (your growth constraint formalized)

This is your safety valve:

System expansion is allowed only if:
    new ContractAxis OR new TestSignal type
    is already observable in existing tests or contract specs

Meaning:

no speculative axes
no speculative signals
9. Minimal implementation boundary

If you strip everything down, CCSS is only:

contract parser
test parser
mapper
diff engine
reporter

That’s it.

No AI layer required for correctness.

10. Re-grounding shortcut (for future use)

If I drift later, you can just say:

“CCSS grounding spec”

and the model should snap back to:

axes come from contracts
signals come from tests
mapping is relational only
output is coverage + gaps only
no inference, no generation, no mutation