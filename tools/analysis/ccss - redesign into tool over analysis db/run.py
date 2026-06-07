import argparse
import json
import hashlib
from pathlib import Path

from tools.analysis.ccss.pass1 import run_pass1 as exec_pass1, canonical_file_id
from tools.analysis.ccss.pass2 import run_pass2
from tools.analysis.ccss.pass3 import run_pass3

def compute_fingerprint(data: dict) -> str:
    normalized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode()).hexdigest()
    
# -----------------------------
# SNAPSHOT LOCATION (FIXED)
# -----------------------------
SNAPSHOT_DIR = Path("tools/analysis/ccss/snapshots")

# -----------------------------
# PIPELINE CORE (PURE)
# -----------------------------
from pathlib import Path
from tools.analysis.ccss.pass1 import canonical_file_id


def run_pipeline(file_path: str):
    """
    Deterministic CCSS pipeline:
    PASS1 -> PASS2 -> PASS3

    file_id is the single canonical identity for the file.
    """

    # SINGLE SOURCE OF TRUTH
    file_id = canonical_file_id(file_path)

    # pass canonical identity downstream
    p1 = exec_pass1(file_path=file_path)
    p2 = run_pass2(p1)
    p3 = run_pass3(p2)

    # attach derived metadata
    p3["file_id"] = file_id
    p3["fingerprint"] = compute_fingerprint(p3)

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