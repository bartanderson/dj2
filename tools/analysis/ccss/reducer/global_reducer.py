from typing import List, Dict, Any
from collections import defaultdict, Counter
import json


def load_pass3_files(paths: List[str]) -> List[Dict[str, Any]]:
    """Load PASS 3 JSON outputs."""
    outputs = []
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            outputs.append(json.load(f))
    return outputs


def build_file_registry(pass3_outputs: List[Dict[str, Any]]) -> Dict[str, Dict]:
    return {
        f["file_id"]: f
        for f in pass3_outputs
    }


from typing import List, Dict, Any
from collections import defaultdict
import json

def normalize_set(items):
    return {str(x).strip() for x in items if x is not None}

NOISE_PATTERNS = {
    "single test discovered",
    "single_test_detected",
    "single integration test discovered",
    "symbol extraction completed",
    "symbol extraction performed",
    "symbols_extracted",
    "identity chain preserved",
    "symbol ordering preserved"
}

def filter_structural(items):
    return {
        x for x in items
        if x not in NOISE_PATTERNS
    }

def reduce_system(pass3_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:

    structural_covered = set()
    structural_missing = set()

    semantic_covered = set()
    semantic_missing = set()

    runtime_covered = set()
    runtime_missing = set()

    redundancy_map = defaultdict(int)
    gap_list = []

    for blob in pass3_outputs:

        pass3 = blob.get("pass_3")

        if not pass3:
            continue

        coverage = pass3.get("coverage", {})

        # --------------------
        # AXES SAFE EXTRACTION
        # --------------------

        axes = coverage.get("axes") or {}

        structural = axes.get("structural") or {}
        semantic = axes.get("semantic") or {}
        runtime = axes.get("runtime") or {}

        # --------------------
        # STRUCTURAL
        # --------------------
        structural_covered.update(filter_structural(normalize_set(structural.get("covered", []))))
        structural_missing.update(filter_structural(normalize_set(structural.get("missing", []))))

        # --------------------
        # SEMANTIC
        # --------------------
        semantic_covered.update(normalize_set(semantic.get("covered", [])))
        semantic_missing.update(normalize_set(semantic.get("missing", [])))

        # --------------------
        # RUNTIME
        # --------------------
        runtime_covered.update(normalize_set(runtime.get("covered", [])))
        runtime_missing.update(normalize_set(runtime.get("missing", [])))

        # --------------------
        # REDUNDANCY (flat merge)
        # --------------------
        for r in coverage.get("redundancy", []):
            key = (r.get("symbol"), r.get("test_id"))
            redundancy_map[key] += r.get("occurrences", 1)

        # --------------------
        # GAPS (direct concat)
        # --------------------
        gap_list.extend(coverage.get("gaps", []))

    redundancy = [
        {
            "symbol": k[0],
            "test_id": k[1],
            "occurrences": v
        }
        for k, v in redundancy_map.items()
    ]

    return {
        "system_coverage": {
            "structural": {
                "covered_tests": sorted(structural_covered),
                "missing_tests": sorted(structural_missing),
            },
            "semantic": {
                "covered_symbols": sorted(semantic_covered),
                "missing_symbols": sorted(semantic_missing),
            },
            "runtime": {
                "covered": sorted(runtime_covered),
                "missing": sorted(runtime_missing),
            }
        },
        "redundancy": redundancy,
        "gaps": gap_list
    }


if __name__ == "__main__":
    import glob

    files = glob.glob("tools/analysis/ccss/output/pass3/*.json")

    data = load_pass3_files(files)

    print("PASS3 INPUT COUNT:", len(data))
    print("PASS3 SAMPLE FILE:", data[0]["file_id"] if data else None)

    result = reduce_system(data)

    print(json.dumps(result, indent=2))