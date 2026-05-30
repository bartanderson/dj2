# tools/analysis/ccss/model.py

from dataclasses import dataclass
from typing import List


@dataclass
class TestSignal:
    test_name: str
    file_path: str
    raw_symbols: List[str]
    candidate_symbols: List[str]