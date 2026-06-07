import argparse
from pathlib import Path

from tools.analysis.ccss.run import run_pipeline
from tools.analysis.ccss.snapshot_store import write_snapshot
from tools.analysis.ccss.ledger_store import append_ledger

ROOT_DIR = Path("tools/analysis/tests")

def scan_directory(root: Path):
    for file_path in root.rglob("test_*.py"):
        file_path = file_path.resolve()

        result = run_pipeline(file_path=str(file_path))
        file_id = result["file_id"]

        snapshot_path = write_snapshot(file_id, result)
        append_ledger(file_id, snapshot_path)

        print(f"[CCSS SCAN] {file_path} -> {snapshot_path}")


def run_single(file_path: Path):
    result = run_pipeline(file_path=str(file_path))
    file_id = result["file_id"]

    snapshot_path = write_snapshot(file_id, result)
    append_ledger(file_id, snapshot_path)

    print(f"[CCSS RUN] {file_path} -> {snapshot_path}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--file",
        help="Run single file instead of directory sweep",
    )

    args = parser.parse_args()

    if args.file:
        run_single(Path(args.file).resolve())
    else:
        scan_directory(ROOT_DIR)


if __name__ == "__main__":
    main()