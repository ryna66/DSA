import csv
import io
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from flights import export_csv, generate, parse_csv, parse_standard, solve


def reference(n, edges, k, coupons):
    """Enumerate bounded walks and both ticket choices; independent of DP."""
    best = None
    stack = [(1, 0, 0, 0)]
    while stack:
        city, count, used, cost = stack.pop()
        if city == n:
            value = cost, count, used
            best = value if best is None else min(value, best)
            continue
        if count == k + 1:
            continue
        for u, v, price in edges:
            if u == city:
                stack.append((v, count + 1, used, cost + price))
                if used < coupons:
                    stack.append((v, count + 1, used + 1, cost + price // 2))
    return best


class FlightTests(unittest.TestCase):
    def verify_path(self, result):
        if result["cost"] == -1:
            self.assertEqual(result["path"], [])
            return
        city, cost, used = 1, 0, 0
        seen = {1}
        for i, leg in enumerate(result["path"], 1):
            self.assertEqual(leg["from"], city)
            self.assertEqual(tuple(result["edges"][leg["edge_id"]]), (leg["from"], leg["to"], leg["price"]))
            self.assertEqual(leg["paid"], leg["price"] // 2 if leg["coupon"] else leg["price"])
            city = leg["to"]
            self.assertNotIn(city, seen)
            seen.add(city)
            cost += leg["paid"]; used += leg["coupon"]
            self.assertEqual(leg["running_cost"], cost)
            self.assertEqual(leg["stops_used"], i if city != result["n"] else i - 1)
        self.assertEqual(city, result["n"])
        self.assertEqual(cost, result["cost"])
        self.assertLessEqual(used, result["coupons"])
        self.assertLessEqual(len(result["path"]), result["k"] + 1)
        self.assertEqual(result["stops"], max(0, len(result["path"]) - 1))

    def test_direct_only_and_floor_discount(self):
        edges = [(1, 2, 2), (2, 3, 2), (1, 3, 101)]
        result = solve(3, edges, 0, 5)
        self.assertEqual(result["cost"], 50)
        self.assertEqual(result["coupons_used"], 1)
        self.assertEqual(result["stops"], 0)
        self.verify_path(result)
        self.assertEqual(solve(3, edges, 1, 0)["cost"], 4)

    def test_coupon_changes_the_best_route(self):
        edges = [(1, 2, 80), (2, 4, 80), (1, 3, 15), (3, 4, 170)]
        self.assertEqual(solve(4, edges, 1, 0)["cost"], 160)
        result = solve(4, edges, 1, 1)
        self.assertEqual(result["cost"], 100)
        self.assertEqual([leg["to"] for leg in result["path"]], [3, 4])
        self.assertEqual([leg["coupon"] for leg in result["path"]], [False, True])
        self.verify_path(result)

    def test_unreachable_and_directed(self):
        self.assertEqual(solve(3, [(1, 2, 5), (2, 3, 5)], 0, 4)["cost"], -1)
        self.assertEqual(solve(2, [(2, 1, 20)], 3, 1)["cost"], -1)
        self.assertEqual(solve(5, [], 10, 2)["cost"], -1)

    def test_start_is_destination(self):
        result = solve(1, [(1, 1, 20)], 1000, 1000)
        self.assertEqual(result["cost"], 0)
        self.assertEqual(result["path"], [])
        self.verify_path(result)

    def test_parallel_flights_and_marked_csv(self):
        edges = [(1, 2, 100), (1, 2, 51), (2, 3, 1), (1, 3, 100)]
        result = solve(3, edges, 1, 2)
        self.assertEqual(result["cost"], 25)
        self.assertEqual([p["edge_id"] for p in result["path"]], [1, 2])
        rows = list(csv.DictReader(io.StringIO('\n'.join(result["csv"].splitlines()[1:]))))
        self.assertEqual([r["path"] for r in rows], ["", "x", "x", ""])
        self.assertEqual([r["coupon"] for r in rows], ["", "yes", "yes", ""])
        self.assertEqual(parse_csv(result["csv"]), (3, edges))
        self.verify_path(result)

    def test_zero_prices_cycles_and_ties(self):
        result = solve(3, [(1, 1, 0), (1, 2, 0), (2, 1, 0), (2, 3, 0), (1, 3, 0)], 1000000, 1000000)
        self.assertEqual(result["cost"], 0)
        self.assertEqual(len(result["path"]), 1)
        self.assertEqual(result["coupons_used"], 0)
        self.verify_path(result)

    def test_randomized_exhaustive_reference(self):
        rng = random.Random(362)
        for _ in range(250):
            n = rng.randint(1, 5)
            edges = [(rng.randint(1, n), rng.randint(1, n), rng.randint(0, 30)) for _ in range(rng.randint(0, 8))]
            k, c = rng.randrange(4), rng.randrange(4)
            expected = reference(n, edges, k, c)
            result = solve(n, edges, k, c)
            self.assertEqual(result["cost"], expected[0] if expected else -1)
            if expected:
                self.assertEqual((result["cost"], len(result["path"]), result["coupons_used"]), expected)
            self.verify_path(result)

    def test_generated_graphs_always_have_bounded_route(self):
        for n in (1, 2, 5, 12):
            for k in (0, 1, 3, 30):
                for c in (0, 1, 4):
                    for seed in range(4):
                        m = min(n * (n - 1), n * 2)
                        edges = generate(n, m, k, c, seed)
                        self.assertEqual(len(edges), m)
                        self.assertEqual(len({(u, v) for u, v, _ in edges}), m)
                        result = solve(n, edges, k, c)
                        self.assertNotEqual(result["cost"], -1)
                        self.verify_path(result)

    def test_input_and_csv_formats(self):
        self.assertEqual(parse_standard('3 2\n1 1\n1 2 5\n2 3 6'), (3, [(1, 2, 5), (2, 3, 6)], 1, 1))
        self.assertEqual(parse_csv('u,v,p\n1,2,3\n'), (2, [(1, 2, 3)]))
        self.assertEqual(parse_csv('1,2,3\n', cities=5), (5, [(1, 2, 3)]))
        self.assertEqual(parse_csv(export_csv(5, [])), (5, []))
        self.assertEqual(parse_csv('\ufeff#cities,1\nu,v,price\n'), (1, []))

    def test_reject_invalid_values(self):
        for n, edges, k, c in ((0, [], 0, 0), (2, [(1, 3, 3)], 0, 0), (2, [(1, 2, -1)], 0, 0),
                                (2, [], -1, 0), (2, [], 0, -1), (2, [(1, 2, 1.5)], 0, 0), (True, [], 0, 0)):
            with self.assertRaises(ValueError): solve(n, edges, k, c)
        for text in ('3 2\n1 1\n1 2 5', '3\n1 1', '3 -1\n1 1'):
            with self.assertRaises(ValueError): parse_standard(text)
        with self.assertRaises(ValueError): parse_csv('#cities,5\n1,2,5', cities=3)
        with self.assertRaises(ValueError): generate(3, 0, 1, 1)
        with self.assertRaises(ValueError): generate(3, 7, 1, 1)


if __name__ == '__main__':
    unittest.main()
