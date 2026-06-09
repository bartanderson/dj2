# tools/analysis/tests/observability/system_health.py

from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass
class HealthReport:
    file_count: int
    symbol_refs: int
    edge_count: int
    bucket_counts: dict
    warnings: list


def compute_health(snapshot: dict[str, Any]) -> HealthReport:
    symbol_refs = snapshot.get("symbol_reference_count", 0)
    edge_count = snapshot.get("edge_count", 0)
    file_count = snapshot.get("file_count", 0)

    bucket_counts = Counter()

    # optional defensive parsing
    for r in snapshot.get("results", []):
        bucket = r.get("bucket", "unknown")
        bucket_counts[bucket] += 1

    warnings = []

    if edge_count != symbol_refs:
        warnings.append(
            f"EDGE MISMATCH: edges={edge_count}, refs={symbol_refs}"
        )

    if file_count == 0:
        warnings.append("NO FILES PROCESSED")

    return HealthReport(
        file_count=file_count,
        symbol_refs=symbol_refs,
        edge_count=edge_count,
        bucket_counts=dict(bucket_counts),
        warnings=warnings,
    )


def print_health(report: HealthReport) -> None:
    print("\n=== SYSTEM HEALTH REPORT ===\n")

    print("files:", report.file_count)
    print("symbol_refs:", report.symbol_refs)
    print("edges:", report.edge_count)

    print("\n--- BUCKETS ---")
    for k, v in report.bucket_counts.items():
        print(f"{k}: {v}")

    print("\n--- WARNINGS ---")
    if not report.warnings:
        print("OK")
    else:
        for w in report.warnings:
            print(w)