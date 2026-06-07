# tools/analysis/ccss/snapshot_store.py

from pathlib import Path
from datetime import datetime, timezone
import json


SNAPSHOT_DIR = Path("tools/analysis/ccss/snapshots")


def make_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def extract_filename(file_path: str) -> str:
    # PURE extraction only
    return Path(file_path).name


def build_snapshot_filename(file_id: str) -> str:
    base = Path(file_id).stem   # <- IMPORTANT CHANGE

    return f"{base}_{make_timestamp()}.json"


def write_snapshot(file_id: str, data: dict) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    filename = build_snapshot_filename(file_id)
    path = SNAPSHOT_DIR / filename

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path