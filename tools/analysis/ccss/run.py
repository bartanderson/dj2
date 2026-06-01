import argparse
import json
from pathlib import Path

from tools.analysis.ccss.pass1 import run_pass1 as exec_pass1, canonical_file_id
from tools.analysis.ccss.pass2 import run_pass2
from tools.analysis.ccss.pass3 import run_pass3


# -----------------------------
# SNAPSHOT LOCATION (FIXED)
# -----------------------------
SNAPSHOT_DIR = Path("tools/analysis/ccss/snapshots")


# -----------------------------
# PIPELINE CORE (PURE)
# -----------------------------
def run_pipeline(file_path: str):
    """
    Deterministic CCSS pipeline:
    PASS1 -> PASS2 -> PASS3
    """

    resolved_path = Path(file_path).resolve().as_posix()

    p1 = exec_pass1(file_path=file_path)
    p2 = run_pass2(p1)
    p3 = run_pass3(p2)

    # 🔒 INVARIANT CHECK
    if "file_id" in p3:
        assert (
            p3["file_id"] == p1["file_id"]
        ), f"file_id drift detected: {p1['file_id']} -> {p3['file_id']}"

    # optional strict alignment check (recommended)
    assert (
        p1["file_id"] == resolved_path
    ), f"pass1 file_id mismatch: {p1['file_id']} != {resolved_path}"

    return p3

# -----------------------------
# CLI ENTRYPOINT
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="CCSS PASS1-3 pipeline runner")
    parser.add_argument("file", help="Path to python source file")
    args = parser.parse_args()

    file_path = str(Path(args.file).resolve())

    result = run_pipeline(file_path=file_path)

    file_id = result["file_id"]

    out_path = write_snapshot(file_id, result)
    append_ledger(file_id, out_path)

    print(f"[CCSS COMPLETE] -> {out_path}")


if __name__ == "__main__":
    main()