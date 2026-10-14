import random
import unittest

from maze import ALGORITHMS, DOORS, KEYS, parse_grid, solve
from test_app import request
import test_maze
from test_maze import reference_distance
import json


class AlgorithmTests(unittest.TestCase):
    def test_all_algorithms_against_reference(self):
        rng = random.Random(816)
        for _ in range(150):
            grid = [["#" if rng.random() < .23 else "." for _ in range(5)] for _ in range(5)]
            for (r, c), token in zip(rng.sample([(r, c) for r in range(5) for c in range(5)], 6), "SEaAbB"):
                grid[r][c] = token
            expected = reference_distance(grid)
            for algorithm in ALGORITHMS:
                result = solve(grid, 2, algorithm)
                with self.subTest(algorithm=algorithm, grid=grid):
                    self.assertEqual(result["optimal"], algorithm != "dfs")
                    if expected < 0:
                        self.assertEqual(result["length"], -1)
                    else:
                        test_maze.MazeTests.assert_valid_path(self, grid, result)
                        if algorithm != "dfs":
                            self.assertEqual(result["length"], expected)
                        else:
                            self.assertGreaterEqual(result["length"], expected)

    def test_trace_is_actual_search_and_neighbors_obey_keys(self):
        grid = parse_grid("#######\n#S.A.E#\n#.#####\n#a#####\n#######\n#######\n#######")
        for algorithm in ALGORITHMS:
            result = solve(grid, 1, algorithm)
            pending, expanded = {0}, 0
            nodes = result["nodes"]
            locked = False
            for event in result["trace"]:
                node = nodes[event["node"]]
                if event["kind"] in {"expand", "goal"}:
                    self.assertIn(event["node"], pending)
                    pending.remove(event["node"])
                    pending.difference_update(event["removed"])
                    pending.update(event["added"])
                    expanded += 1
                self.assertEqual(event["frontier"], len(pending))
                self.assertEqual(event["expanded"], expanded)
                for child in event["added"]:
                    self.assertEqual(nodes[child]["parent"], event["node"])
                    self.assertEqual(nodes[child]["depth"], node["depth"] + 1)
                for check in event["checks"]:
                    r, c = check["row"], check["col"]
                    self.assertEqual(abs(r - node["row"]) + abs(c - node["col"]), 1)
                    if check["status"] == "locked":
                        locked = True
                        key = DOORS[grid[r][c]]
                        self.assertFalse(node["mask"] & (1 << KEYS.index(key)))
            self.assertTrue(locked)
            self.assertEqual(result["length"], 8)
            self.assertEqual(result["trace"][-1]["kind"], "goal")
            self.assertEqual(result["states_explored"], expanded)

    def test_dfs_can_return_longer_route_and_backtracks(self):
        grid = parse_grid("S...E\n.###.\n.....\n.###.\na...A")
        # DFS uses the upper branch here; reversing the exit makes a longer first route.
        grid[0][4], grid[1][0] = ".", "E"
        bfs = solve(grid, 1)
        dfs = solve(grid, 1, "dfs")
        self.assertEqual(bfs["length"], 1)
        self.assertGreater(dfs["length"], bfs["length"])
        blocked = parse_grid("S..##\n.#.##\na#.##\n#####\n####E")
        result = solve(blocked, 1, "dfs")
        self.assertEqual(result["length"], -1)
        self.assertTrue(any(e["kind"] == "backtrack" for e in result["trace"]))
        self.assertEqual(result["trace"][-1]["kind"], "exhausted")

    def test_astar_guidance_and_dijkstra_unit_weights(self):
        grid = parse_grid("S....\n.....\n..a..\n.....\nE...A")
        bfs = solve(grid, 1)
        dijkstra = solve(grid, 1, "dijkstra")
        astar = solve(grid, 1, "astar")
        self.assertEqual(bfs["trace"], dijkstra["trace"])
        self.assertEqual(astar["length"], bfs["length"])
        self.assertLess(astar["states_explored"], bfs["states_explored"])

    def test_api_algorithm_selection_and_validation(self):
        for algorithm in ALGORITHMS:
            status, body = request("POST", "/api/solve", {"text": "SE\naA", "types": 1, "algorithm": algorithm})
            self.assertEqual(status, 200)
            result = json.loads(body)
            self.assertEqual(result["algorithm"], algorithm)
            self.assertTrue(result["trace"])
        for algorithm in ("unknown", [], None):
            status, _ = request("POST", "/api/solve", {"text": "SE\naA", "types": 1, "algorithm": algorithm})
            self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
