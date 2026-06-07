# tools/analysis/ccss/regression_check.py

from pathlib import Path
from tools.analysis.ccss.snapshot_compare import compare_snapshots


def run_check():
    base = Path("tools/analysis/ccss/snapshots/test_symbol_uniqueness.py_20260601T041836Z.json")
    curr = Path("tools/analysis/ccss/snapshots/test_symbol_uniqueness.py_20260601T051236Z.json")

    result = compare_snapshots(base, curr)

    print("\n=== CCSS REGRESSION CHECK ===\n")
    print(result)

    if not result["stable"]:
        print("\n❌ REGRESSION DETECTED")
    else:
        print("\n✅ STABLE")


if __name__ == "__main__":
    run_check()