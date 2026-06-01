# tools/analysis/ccss/pass3.py

from typing import Dict, Any
from collections import defaultdict


def run_pass3(pass2: Dict[str, Any]) -> Dict[str, Any]:

    structural = set()
    semantic = set()
    runtime = set()

    redundancy = defaultdict(int)

    for test in pass2["tests"]:
        test_id = test["test_id"]

        # ------------------------
        # STRUCTURAL: test presence
        # ------------------------
        structural.add(test_id)

        for symbol in test["symbols"]:

            # ------------------------
            # SEMANTIC: surface identity
            # ------------------------
            semantic.add(symbol["surface"])

            # ------------------------
            # RUNTIME: full identity
            # ------------------------
            runtime.add(symbol["symbol_uid"])

            # ------------------------
            # REDUNDANCY (pure count)
            # ------------------------
            key = (symbol["surface"], test_id)
            redundancy[key] += 1

    return {
        "file_id": pass2["file_id"],
        "pass_3": {
            "coverage": {
                "axes": {
                    "structural": {
                        "covered": sorted(structural),
                        "missing": []
                    },
                    "semantic": {
                        "covered": sorted(semantic),
                        "missing": []
                    },
                    "runtime": {
                        "covered": sorted(runtime),
                        "missing": []
                    }
                },
                "redundancy": [
                    {
                        "symbol": k[0],
                        "test_id": k[1],
                        "occurrences": v
                    }
                    for k, v in sorted(redundancy.items())
                ],
                "gaps": []
            }
        }
    }