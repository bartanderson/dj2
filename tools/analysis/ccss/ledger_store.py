# tools/analysis/ccss/ledger_store.py

from pathlib import Path
from datetime import datetime, timezone
import json

LEDGER_DIR = Path("tools/analysis/ccss/ledger")
LEDGER_FILE = LEDGER_DIR / "ledger.jsonl"


def make_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def append_ledger(file_id: str, snapshot_path: Path) -> Path:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)

    entry = {
        "file_id": file_id,
        "snapshot_path": str(snapshot_path),
        "timestamp": make_timestamp()
    }

    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return LEDGER_FILE