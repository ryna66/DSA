import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from closest_pair import (DISTRIBUTIONS, benchmark, brute_force, compare,
                          divide_and_conquer, generate_points, validate_points)


class ClosestPairTests(unittest.TestCase):
    def assert_valid_result(self, points, entry):
        if len(points) < 2:
            self.assertIsNone(entry["pair"])
            self.assertIsNone(entry["distance"])
            return
        i, j = entry["pair"]
        self.assertNotEqual(i, j)
        self.assertGreaterEqual(i, 0)
        self.assertLess(j, len(points))
        self.assertEqual(entry["distance"], math.dist(points[i], points[j]))

    def test_zero_one_and_two_points(self):
        for points in ([], [(4, 5)], [(0, 0), (3, 4)]):
            result = compare(points)
            self.assertTrue(result["agree"])
            for key in ("brute", "divide"):
                self.assert_valid_result(points, result[key])
        self.assertEqual(compare([(0, 0), (3, 4)])["divide"]["distance"], 5)

    def test_duplicates_and_all_coincident(self):
        for points in ([(1, 2)] * 30, [(4, 5), (0, 0), (4, 5), (0, 0)]):
            result = compare(points)
            self.assertEqual(result["divide"]["distance"], 0)
            self.assertEqual(result["brute"]["pair"], result["divide"]["pair"])
            self.assertEqual(result["events"][-1]["kind"], "duplicate")

    def test_collinear_shared_axes_and_ties(self):
        fixtures = [[(0, i * 3) for i in range(45)], [(i * 3, 0) for i in range(45)],
                    [(i, 2 * i + 5) for i in range(45)],
                    [(x, y) for x in range(8) for y in range(8)]]
        for points in fixtures:
            result = compare(points)
            self.assertTrue(result["agree"])
            self.assert_valid_result(points, result["divide"])

    def test_closest_pair_crosses_split_and_strip_is_shown(self):
        points = [(-50, 25), (-20, 40), (-.1, 0), (.1, 0), (20, -40), (50, -25)]
        result = compare(points)
        self.assertEqual(result["divide"]["pair"], [2, 3])
        self.assertAlmostEqual(result["divide"]["distance"], .2)
        self.assertTrue(any(e["kind"] == "split" for e in result["events"]))
        self.assertTrue(any(e["kind"] == "strip" and e["strip_d"] > 0 for e in result["events"]))
        self.assertTrue(any(e["kind"] == "merge" for e in result["events"]))
        self.assertEqual(result["events"][-1]["best"], result["divide"]["pair"])
        for event in result["events"]:
            self.assertGreaterEqual(event["lo"], 0)
            self.assertLessEqual(event["hi"], len(points))
            if "checking" in event:
                for point_id in event["checking"]:
                    self.assertIn(point_id, result["order"][event["lo"]:event["hi"]])

    def test_randomized_agreement(self):
        for distribution in DISTRIBUTIONS:
            for n in (0, 1, 2, 3, 4, 5, 11, 32, 65, 127):
                for seed in range(10):
                    with self.subTest(distribution=distribution, n=n, seed=seed):
                        points = generate_points(n, seed, distribution)
                        brute, divide = brute_force(points), divide_and_conquer(points)
                        self.assertEqual(brute["distance"], divide["distance"])
                        self.assert_valid_result(points, divide)
                        self.assertEqual(brute["comparisons"], n * (n - 1) // 2)

    def test_independent_reference_and_input_not_mutated(self):
        rng = random.Random(445)
        for _ in range(100):
            points = [(rng.uniform(-1000, 1000), rng.uniform(-1000, 1000)) for _ in range(30)]
            original = points.copy()
            expected = min(math.dist(a, b) for i, a in enumerate(points) for b in points[i+1:])
            self.assertEqual(compare(points)["divide"]["distance"], expected)
            self.assertEqual(points, original)

    def test_large_and_tiny_finite_coordinates(self):
        for factor in (1e-100, 1e99):
            result = compare([(0, 0), (factor, factor), (3 * factor, 3 * factor), (-factor, -factor)])
            self.assertTrue(result["agree"])
            self.assertGreater(result["divide"]["distance"], 0)
            self.assertTrue(math.isfinite(result["divide"]["distance"]))

    def test_validation(self):
        for points in (None, [(1,)], [(1, 2, 3)], [(True, 1)], [("1", 2)], [(math.nan, 0)], [(math.inf, 0)], [(1e101, 0)]):
            with self.subTest(points=points), self.assertRaises(ValueError):
                validate_points(points)
        for n in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                generate_points(n)

    def test_benchmarks_use_matching_data_and_sorted_unique_sizes(self):
        result = benchmark([20, 2, 10, 20], repeats=3, seed=71)
        self.assertEqual([r["n"] for r in result["rows"]], [2, 10, 20])
        self.assertTrue(result["agree"])
        for row in result["rows"]:
            self.assertGreaterEqual(row["brute_ms"], 0)
            self.assertGreaterEqual(row["divide_ms"], 0)
        for sizes in ([], [1], [3001], [True]):
            with self.assertRaises(ValueError):
                benchmark(sizes)


if __name__ == "__main__":
    unittest.main()
