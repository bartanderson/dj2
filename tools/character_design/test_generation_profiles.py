"""Tests for candidate score-generation profiles.

Run from repository root:
    python -m unittest tools.character_design.test_generation_profiles
"""

from __future__ import annotations

from random import Random
import unittest

from tools.character_design.generation_profiles import (
    MAX_SCORE,
    MIN_SCORE,
    ProfileName,
    generate_balanced,
    generate_pool,
)
from tools.character_design.simulate_generation_profiles import simulate


class GenerationProfileTests(unittest.TestCase):
    def test_every_profile_generates_six_valid_scores(self) -> None:
        for profile in ProfileName:
            rng = Random(12345)
            for _ in range(1000):
                pool = generate_pool(profile, rng)
                self.assertEqual(len(pool), 6)
                self.assertTrue(all(MIN_SCORE <= score <= MAX_SCORE for score in pool))

    def test_balanced_profile_is_exact_fixed_array(self) -> None:
        self.assertEqual(generate_balanced(Random(1)), (15, 14, 13, 12, 10, 8))

    def test_seeded_generation_is_reproducible(self) -> None:
        for profile in ProfileName:
            first_rng = Random(20261107)
            second_rng = Random(20261107)
            first = [generate_pool(profile, first_rng) for _ in range(100)]
            second = [generate_pool(profile, second_rng) for _ in range(100)]
            self.assertEqual(first, second)

    def test_seeded_simulation_is_reproducible(self) -> None:
        for profile in ProfileName:
            first = simulate(profile, trials=1000, seed=4242)
            second = simulate(profile, trials=1000, seed=4242)
            self.assertEqual(first, second)

    def test_balanced_profile_has_expected_numerical_identity(self) -> None:
        report = simulate(ProfileName.BALANCED, trials=100, seed=1)
        self.assertEqual(report.mean_total, 72.0)
        self.assertEqual(report.median_total, 72.0)
        self.assertEqual(report.minimum_total, 72)
        self.assertEqual(report.maximum_total, 72)
        self.assertEqual(report.probability_max_at_least_15, 1.0)
        self.assertEqual(report.probability_max_at_least_16, 0.0)
        self.assertEqual(report.probability_has_18, 0.0)


if __name__ == "__main__":
    unittest.main()
