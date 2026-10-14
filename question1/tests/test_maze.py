import random
import unittest
from collections import deque

from maze import DOORS, KEYS, export_csv, generate, parse_grid, solve


def reference_distance(grid):
    """Independent state representation for differential testing."""
    n = len(grid)
    start = next((r, c, frozenset()) for r in range(n) for c in range(n) if grid[r][c] == "S")
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        (r, c, keys), distance = queue.popleft()
        if grid[r][c] == "E":
            return distance
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c - 1), (r, c + 1)):
            if not (0 <= nr < n and 0 <= nc < n):
                continue
            cell = grid[nr][nc]
            if cell == "#" or cell in DOORS and DOORS[cell] not in keys:
                continue
            inventory = keys | {cell} if cell in KEYS else keys
            state = nr, nc, frozenset(inventory)
            if state not in seen:
                seen.add(state)
                queue.append((state, distance + 1))
    return -1


class MazeTests(unittest.TestCase):
    def assert_valid_path(self, grid, result):
        self.assertGreaterEqual(result["length"], 0)
        self.assertEqual(len(result["path"]) - 1, result["length"])
        keys = set()
        previous = None
        for step in result["path"]:
            r, c = step["row"], step["col"]
            if previous:
                self.assertEqual(abs(r - previous[0]) + abs(c - previous[1]), 1)
            token = grid[r][c]
            self.assertNotEqual(token, "#")
            if token in DOORS:
                self.assertIn(DOORS[token], keys)
            if token in KEYS:
                keys.add(token)
            self.assertEqual(step["mask"], sum(1 << KEYS.index(key) for key in keys))
            previous = r, c
        first, last = result["path"][0], result["path"][-1]
        self.assertEqual(grid[first["row"]][first["col"]], "S")
        self.assertEqual(grid[last["row"]][last["col"]], "E")

    def test_revisiting_start_with_key_is_required(self):
        grid = parse_grid("#######\n#S.A.E#\n#.#####\n#a#####\n#######\n#######\n#######")
        result = solve(grid, 1)
        self.assertEqual(result["length"], 8)
        self.assert_valid_path(grid, result)
        visits = [p["mask"] for p in result["path"] if (p["row"], p["col"]) == (1, 1)]
        self.assertEqual(visits, [0, 1])

    def test_missing_or_inaccessible_key_is_unsolvable(self):
        for text in ("S.A.E\n#####\na....\n.....\n.....", "SAE\n###\n###"):
            result = solve(parse_grid(text), 1)
            self.assertEqual(result["length"], -1)
            self.assertEqual(result["path"], [])
            self.assertNotIn("x", result["csv"])

    def test_exit_does_not_require_key_e(self):
        self.assertEqual(solve(parse_grid("SE\naA"), 1)["length"], 1)

    def test_door_e_is_distinct_from_exit(self):
        grid = parse_grid("S,e,D:e,E\n#,#,#,#\n#,#,#,#\n#,#,#,#")
        result = solve(grid, 1)
        self.assertEqual(result["length"], 3)
        self.assertEqual(result["path"][2]["door"], "e")
        self.assertIn("x(D:e)", result["csv"])
        self.assertEqual(parse_grid(result["csv"]), grid)

    def test_export_preserves_path_keys_doors_and_endpoints(self):
        grid = parse_grid("S,a,A,E\n#,#,#,#\n#,#,#,#\n#,#,#,#")
        result = solve(grid, 1)
        self.assertTrue(result["csv"].startswith("x(S),x(a),x(A),x(E)\n"))
        self.assertEqual(parse_grid(result["csv"]), grid)

    def test_parsing_formats_and_bom(self):
        expected = [["S", "E"], ["a", "A"]]
        for text in ("SE\naA", " S E\n a A ", '\ufeff"S","E"\n"a","A"\n'):
            self.assertEqual(parse_grid(text), expected)
        self.assertEqual(parse_grid(export_csv(expected)), expected)

    def test_invalid_input(self):
        cases = [([], 1), ([["S", "E"]], 1), (parse_grid("SSE\na..\n..."), 1),
                 (parse_grid("S?\naE"), 1), (parse_grid("SE\naA"), 2),
                 (parse_grid("SE\naA"), True), (parse_grid("SE\naA"), 0),
                 (parse_grid("SE\naA"), 7), ([["S", "E"], [[], "."]], 1)]
        for grid, types in cases:
            with self.subTest(grid=grid, types=types), self.assertRaises(ValueError):
                solve(grid, types)
        with self.assertRaises(ValueError):
            parse_grid("")

    def test_generated_mazes_are_solvable_and_use_every_pair(self):
        for size in (7, 11, 25):
            for types in range(1, 7):
                for seed in range(15):
                    with self.subTest(size=size, types=types, seed=seed):
                        grid = generate(size, types, seed)
                        result = solve(grid, types)
                        self.assert_valid_path(grid, result)
                        self.assertEqual(sum(bool(p["pickup"]) for p in result["path"]), types)
                        self.assertEqual(sum(bool(p["door"]) for p in result["path"]), types)
                        self.assertEqual(parse_grid(result["csv"]), grid)
                        self.assertEqual(set(c for row in grid for c in row if c in KEYS), set(KEYS[:types]))

    def test_seed_is_reproducible(self):
        self.assertEqual(generate(11, 3, 82), generate(11, 3, 82))

    def test_invalid_generation(self):
        for size, types in ((6, 1), (26, 1), (8, 2), (7, 0), (7, 7), (7.0, 1)):
            with self.subTest(size=size, types=types), self.assertRaises(ValueError):
                generate(size, types)

    def test_shortest_distance_matches_independent_reference(self):
        rng = random.Random(274)
        for _ in range(150):
            grid = [["#" if rng.random() < .27 else "." for _ in range(5)] for _ in range(5)]
            for (r, c), token in zip(rng.sample([(r, c) for r in range(5) for c in range(5)], 6), "SEaAbB"):
                grid[r][c] = token
            result = solve(grid, 2)
            self.assertEqual(result["length"], reference_distance(grid))
            if result["length"] != -1:
                self.assert_valid_path(grid, result)


if __name__ == "__main__":
    unittest.main()
