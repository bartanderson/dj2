"""Execute reproducible probability and balance simulations for candidate profiles.

Usage from the repository root:
    python tools/character_design/simulate_generation_profiles.py --trials 100000 --seed 20261107
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, asdict
from random import Random
from statistics import mean, median

from tools.character_design.generation_profiles import PROFILES, ProfileName, generate_pool


@dataclass(frozen=True)
class ProfileReport:
    profile: str
    trials: int
    mean_total: float
    median_total: float
    minimum_total: int
    maximum_total: int
    mean_modifier_total: float
    mean_highest_modifier: float
    mean_lowest_modifier: float
    probability_max_at_least_15: float
    probability_max_at_least_16: float
    probability_max_at_least_17: float
    probability_has_18: float
    probability_min_at_most_8: float
    probability_min_at_most_6: float
    probability_two_or_more_at_most_8: float
    probability_shape_15_and_13: float
    probability_shape_16_and_two_13: float


def modifier(score: int) -> int:
    return (score - 10) // 2


def probability(count: int, trials: int) -> float:
    return count / trials


def simulate(profile: ProfileName, trials: int, seed: int) -> ProfileReport:
    rng = Random(seed)
    totals: list[int] = []
    modifier_totals: list[int] = []
    highest_modifiers: list[int] = []
    lowest_modifiers: list[int] = []
    counters: Counter[str] = Counter()

    for _ in range(trials):
        pool = generate_pool(profile, rng)
        ordered = sorted(pool, reverse=True)
        mods = [modifier(score) for score in pool]

        totals.append(sum(pool))
        modifier_totals.append(sum(mods))
        highest_modifiers.append(max(mods))
        lowest_modifiers.append(min(mods))

        if ordered[0] >= 15:
            counters["max_15"] += 1
        if ordered[0] >= 16:
            counters["max_16"] += 1
        if ordered[0] >= 17:
            counters["max_17"] += 1
        if ordered[0] == 18:
            counters["has_18"] += 1
        if ordered[-1] <= 8:
            counters["min_8"] += 1
        if ordered[-1] <= 6:
            counters["min_6"] += 1
        if sum(score <= 8 for score in pool) >= 2:
            counters["two_min_8"] += 1
        if ordered[0] >= 15 and ordered[1] >= 13:
            counters["shape_15_13"] += 1
        if ordered[0] >= 16 and ordered[1] >= 13 and ordered[2] >= 13:
            counters["shape_16_13_13"] += 1

    return ProfileReport(
        profile=profile.value,
        trials=trials,
        mean_total=round(mean(totals), 4),
        median_total=float(median(totals)),
        minimum_total=min(totals),
        maximum_total=max(totals),
        mean_modifier_total=round(mean(modifier_totals), 4),
        mean_highest_modifier=round(mean(highest_modifiers), 4),
        mean_lowest_modifier=round(mean(lowest_modifiers), 4),
        probability_max_at_least_15=round(probability(counters["max_15"], trials), 6),
        probability_max_at_least_16=round(probability(counters["max_16"], trials), 6),
        probability_max_at_least_17=round(probability(counters["max_17"], trials), 6),
        probability_has_18=round(probability(counters["has_18"], trials), 6),
        probability_min_at_most_8=round(probability(counters["min_8"], trials), 6),
        probability_min_at_most_6=round(probability(counters["min_6"], trials), 6),
        probability_two_or_more_at_most_8=round(probability(counters["two_min_8"], trials), 6),
        probability_shape_15_and_13=round(probability(counters["shape_15_13"], trials), 6),
        probability_shape_16_and_two_13=round(probability(counters["shape_16_13_13"], trials), 6),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=20_261_107)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.trials <= 0:
        raise SystemExit("--trials must be positive")

    reports = [simulate(profile, args.trials, args.seed) for profile in ProfileName]

    if args.json:
        print(json.dumps([asdict(report) for report in reports], indent=2))
        return

    for report in reports:
        print(f"\\nPROFILE: {report.profile}")
        print(f"Trials: {report.trials}")
        for key, value in asdict(report).items():
            if key not in {"profile", "trials"}:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
