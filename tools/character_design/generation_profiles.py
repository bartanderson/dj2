"""Candidate six-ability score-generation profiles.

This module is intentionally non-production design code. It provides deterministic,
seedable implementations so candidate numerical rules can be measured before any
character-system cutover.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from random import Random
from typing import Callable

ABILITY_COUNT = 6
MIN_SCORE = 3
MAX_SCORE = 18


class ProfileName(str, Enum):
    BALANCED = "balanced"
    RANDOM_DESTINY = "random_destiny"
    CONCEPT_GUIDED = "concept_guided"
    HEROIC = "heroic"


@dataclass(frozen=True)
class GenerationProfile:
    name: ProfileName
    description: str
    generate: Callable[[Random], tuple[int, ...]]


def roll_4d6_drop_lowest(rng: Random) -> int:
    """Roll four d6 and return the sum of the highest three."""
    dice = sorted(rng.randint(1, 6) for _ in range(4))
    return sum(dice[1:])


def _validate_pool(pool: tuple[int, ...]) -> tuple[int, ...]:
    if len(pool) != ABILITY_COUNT:
        raise ValueError(f"Expected {ABILITY_COUNT} scores, got {len(pool)}")
    if any(score < MIN_SCORE or score > MAX_SCORE for score in pool):
        raise ValueError(f"Scores must remain in {MIN_SCORE}..{MAX_SCORE}: {pool}")
    return pool


def generate_balanced(_: Random) -> tuple[int, ...]:
    """Fixed, predictable baseline used as the reference profile."""
    return _validate_pool((15, 14, 13, 12, 10, 8))


def generate_random_destiny(rng: Random) -> tuple[int, ...]:
    """Traditional six independent 4d6-drop-lowest scores."""
    return _validate_pool(tuple(roll_4d6_drop_lowest(rng) for _ in range(ABILITY_COUNT)))


def generate_concept_guided(rng: Random) -> tuple[int, ...]:
    """Random pool with one bounded protection opportunity.

    Candidate rule under evaluation:
    1. Generate six 4d6-drop-lowest scores.
    2. If the pool's highest score is below 15, generate one additional score.
    3. Replace the lowest score only when the additional score is higher.

    The resulting pool does not encode which ability is protected. Assignment is a
    separate deterministic phase and may place the best available score in the
    player's one confirmed defining ability.
    """
    pool = list(generate_random_destiny(rng))
    if max(pool) < 15:
        candidate = roll_4d6_drop_lowest(rng)
        lowest_index = pool.index(min(pool))
        if candidate > pool[lowest_index]:
            pool[lowest_index] = candidate
    return _validate_pool(tuple(pool))


def generate_heroic(rng: Random) -> tuple[int, ...]:
    """Generate seven 4d6-drop-lowest scores and discard the lowest."""
    pool = sorted(roll_4d6_drop_lowest(rng) for _ in range(ABILITY_COUNT + 1))
    return _validate_pool(tuple(pool[1:]))


PROFILES: dict[ProfileName, GenerationProfile] = {
    ProfileName.BALANCED: GenerationProfile(
        ProfileName.BALANCED,
        "Fixed array: 15, 14, 13, 12, 10, 8.",
        generate_balanced,
    ),
    ProfileName.RANDOM_DESTINY: GenerationProfile(
        ProfileName.RANDOM_DESTINY,
        "Six independent 4d6-drop-lowest scores.",
        generate_random_destiny,
    ),
    ProfileName.CONCEPT_GUIDED: GenerationProfile(
        ProfileName.CONCEPT_GUIDED,
        "Random Destiny plus one bounded rescue roll when no score reaches 15.",
        generate_concept_guided,
    ),
    ProfileName.HEROIC: GenerationProfile(
        ProfileName.HEROIC,
        "Seven 4d6-drop-lowest scores, discard the lowest.",
        generate_heroic,
    ),
}


def generate_pool(profile: ProfileName, rng: Random) -> tuple[int, ...]:
    return PROFILES[profile].generate(rng)
