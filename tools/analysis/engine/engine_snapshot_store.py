# tools/analysis/engine/engine_snapshot_store.py

import json
from dataclasses import asdict
from pathlib import Path

def write_snapshot(snapshot, path: str):
    Path(path).write_text(json.dumps(asdict(snapshot), indent=2))


def load_snapshot(path: str):
    return json.loads(Path(path).read_text())