"""Shortest paths through key-and-door mazes. Python standard library only."""

from __future__ import annotations

import csv
import io
import heapq
import random
from collections import deque

MAX_SIZE = 25
KEYS = "abcdef"
DOORS = {letter.upper(): letter for letter in KEYS if letter != "e"}
DOORS["D:e"] = "e"  # E is reserved for the exit.
TOKENS = {".", "#", "S", "E", *KEYS, *DOORS}


def parse_grid(text: str) -> list[list[str]]:
    """Accept CSV, whitespace-separated tokens, or compact character rows."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Enter a maze or choose a CSV file first.")
    rows = []
    for line in text.lstrip("\ufeff").splitlines():
        if not line.strip():
            continue
        if "," in line:
            row = next(csv.reader([line], strict=True))
        elif any(char.isspace() for char in line.strip()):
            row = line.split()
        else:
            row = list(line.strip())
        # Exported paths can be imported without losing their original symbols.
        row = [cell.strip() for cell in row]
        row = ["." if cell == "x" else cell[2:-1]
               if cell.startswith("x(") and cell.endswith(")") else cell
               for cell in row]
        rows.append(row)
    return rows


def validate_grid(grid: list[list[str]], types: int) -> None:
    if type(types) is not int or not 1 <= types <= 6:
        raise ValueError("T must be an integer between 1 and 6.")
    if not isinstance(grid, list) or not 2 <= len(grid) <= MAX_SIZE:
        raise ValueError(f"Use a square grid between 2 × 2 and {MAX_SIZE} × {MAX_SIZE}.")
    if any(not isinstance(row, list) or len(row) != len(grid) for row in grid):
        raise ValueError("The grid must be square: every row needs N cells, with N rows.")
    counts = {"S": 0, "E": 0}
    found = set()
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if not isinstance(cell, str) or cell not in TOKENS:
                raise ValueError(f"Unknown cell {cell!r} at row {r + 1}, column {c + 1}.")
            if cell in counts:
                counts[cell] += 1
            elif cell in KEYS or cell in DOORS:
                found.add(DOORS.get(cell, cell))
    if counts != {"S": 1, "E": 1}:
        raise ValueError("Include exactly one S (start) and one E (exit). Use D:e for door e.")
    if len(found) != types:
        raise ValueError(f"T is {types}, but this maze contains {len(found)} distinct key/door types.")


ALGORITHMS = {"bfs", "dfs", "dijkstra", "astar"}


def solve(grid: list[list[str]], types: int, algorithm: str = "bfs") -> dict:
    """Search position/inventory states and record the actual expansion decisions."""
    validate_grid(grid, types)
    if not isinstance(algorithm, str) or algorithm not in ALGORITHMS:
        raise ValueError("Algorithm must be bfs, dfs, dijkstra, or astar.")
    n = len(grid)
    sr, sc = next((r, c) for r in range(n) for c in range(n) if grid[r][c] == "S")
    er, ec = next((r, c) for r in range(n) for c in range(n) if grid[r][c] == "E")
    nodes = [{"row": sr, "col": sc, "mask": 0, "parent": None, "depth": 0}]
    best = {(sr, sc, 0): 0}
    frontier = deque([0])
    heap = [(0, 0)]
    pending = {0}
    trace, explored = [], []
    cells_seen = set()
    expanded = 0
    end = previous = None

    def record(kind, node_id, added=None, checks=None, removed=None):
        trace.append({"kind": kind, "node": node_id, "added": added or [],
                      "removed": removed or [], "checks": checks or [],
                      "frontier": len(pending), "expanded": expanded})

    while pending:
        if algorithm in {"dijkstra", "astar"}:
            _, node_id = heapq.heappop(heap)
        else:
            node_id = frontier.pop() if algorithm == "dfs" else frontier.popleft()
        if node_id not in pending:
            continue  # Superseded by a cheaper route.
        node = nodes[node_id]
        if algorithm == "dfs" and previous is not None:
            # The stack's next branch belongs to an ancestor of the last branch.
            ancestor = previous
            while ancestor is not None and ancestor != node["parent"]:
                ancestor = nodes[ancestor]["parent"]
                if ancestor is not None:
                    record("backtrack", ancestor)
        pending.remove(node_id)
        r, c, mask = node["row"], node["col"], node["mask"]
        expanded += 1
        if (r, c) not in cells_seen:
            cells_seen.add((r, c))
            explored.append([r, c])
        if grid[r][c] == "E":
            end = node_id
            record("goal", node_id)
            break
        added, checks, removed = [], [], []
        for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
            nr, nc = r + dr, c + dc
            check = {"row": nr, "col": nc}
            checks.append(check)
            if not (0 <= nr < n and 0 <= nc < n):
                check["status"] = "boundary"
                continue
            token = grid[nr][nc]
            if token == "#":
                check["status"] = "wall"
                continue
            if token in DOORS and not mask & (1 << KEYS.index(DOORS[token])):
                check.update(status="locked", key=DOORS[token])
                continue
            next_mask = mask | (1 << KEYS.index(token)) if token in KEYS else mask
            state = nr, nc, next_mask
            depth = node["depth"] + 1
            old = best.get(state)
            if old is not None and (algorithm in {"bfs", "dfs"} or nodes[old]["depth"] <= depth):
                check["status"] = "seen"
                continue
            if old in pending:
                pending.remove(old)
                removed.append(old)
            child = len(nodes)
            nodes.append({"row": nr, "col": nc, "mask": next_mask,
                          "parent": node_id, "depth": depth})
            best[state] = child
            pending.add(child)
            added.append(child)
            check["status"] = "queued"
            if algorithm in {"dijkstra", "astar"}:
                h = abs(nr - er) + abs(nc - ec) if algorithm == "astar" else 0
                heapq.heappush(heap, (depth + h, child))
        if algorithm not in {"dijkstra", "astar"}:
            frontier.extend(reversed(added) if algorithm == "dfs" else added)
        record("expand", node_id, added, checks, removed)
        previous = node_id
    if end is None:
        if algorithm == "dfs" and previous is not None:
            ancestor = nodes[previous]["parent"]
            while ancestor is not None:
                record("backtrack", ancestor)
                ancestor = nodes[ancestor]["parent"]
        record("exhausted", 0)
    route = []
    while end is not None:
        route.append(nodes[end])
        end = nodes[end]["parent"]
    route.reverse()
    path, opened = [], set()
    for index, node in enumerate(route):
        r, c, mask = node["row"], node["col"], node["mask"]
        token = grid[r][c]
        previous_mask = route[index - 1]["mask"] if index else 0
        pickup = token if token in KEYS and mask != previous_mask else None
        door = DOORS.get(token) if token in DOORS and (r, c) not in opened else None
        if door:
            opened.add((r, c))
        path.append({"row": r, "col": c, "mask": mask, "pickup": pickup, "door": door})
    length = len(path) - 1 if path else -1
    return {"grid": grid, "types": types, "algorithm": algorithm,
            "optimal": algorithm != "dfs", "length": length, "path": path,
            "nodes": nodes, "trace": trace,
            "explored": explored, "states_explored": expanded,
            "states_discovered": len(best), "csv": export_csv(grid, path)}


def export_csv(grid: list[list[str]], path: list[dict] | None = None) -> str:
    """Mark floor with x, and retain all special path cells as x(symbol)."""
    positions = {(step["row"], step["col"]) for step in path or []}
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    for r, row in enumerate(grid):
        writer.writerow([("x" if cell == "." else f"x({cell})")
                         if (r, c) in positions else cell for c, cell in enumerate(row)])
    return out.getvalue()


def generate(size: int, types: int, seed: int | None = None) -> list[list[str]]:
    """Carve a random spanning tree and place all pairs along its exit route."""
    if type(size) is not int or size < 7 or size > MAX_SIZE or size % 2 == 0:
        raise ValueError("Random maze size must be an odd integer from 7 to 25.")
    if type(types) is not int or not 1 <= types <= 6:
        raise ValueError("T must be an integer between 1 and 6.")
    rng = random.Random(seed)
    grid = [["#"] * size for _ in range(size)]
    grid[1][1] = "."
    stack = [(1, 1)]
    while stack:
        r, c = stack[-1]
        candidates = [(r + dr, c + dc) for dr, dc in ((-2, 0), (0, 2), (2, 0), (0, -2))
                      if 0 < r + dr < size - 1 and 0 < c + dc < size - 1
                      and grid[r + dr][c + dc] == "#"]
        if not candidates:
            stack.pop()
            continue
        nr, nc = rng.choice(candidates)
        grid[(r + nr) // 2][(c + nc) // 2] = "."
        grid[nr][nc] = "."
        stack.append((nr, nc))
    queue = deque([(1, 1)])
    parents = {(1, 1): None}
    farthest = (1, 1)
    while queue:
        farthest = queue.popleft()
        r, c = farthest
        for dr, dc in ((-1, 0), (0, 1), (1, 0), (0, -1)):
            p = r + dr, c + dc
            if grid[p[0]][p[1]] == "." and p not in parents:
                parents[p] = farthest
                queue.append(p)
    route = []
    p = farthest
    while p is not None:
        route.append(p)
        p = parents[p]
    route.reverse()
    # Ensure even the smallest maze has room for all requested key/door pairs.
    if len(route) - 2 < 2 * types:
        # Deterministic fallback: a single winding corridor through every odd row.
        grid = [["#"] * size for _ in range(size)]
        route = []
        for i, r in enumerate(range(1, size - 1, 2)):
            columns = list(range(1, size - 1))
            if i % 2:
                columns.reverse()
            route.extend((r, c) for c in columns)
            if r + 2 < size - 1:
                route.append((r + 1, columns[-1]))
        for r, c in route:
            grid[r][c] = "."
    positions = sorted(rng.sample(range(1, len(route) - 1), 2 * types))
    order = list(KEYS[:types])
    rng.shuffle(order)
    for i, key in enumerate(order):
        kr, kc = route[positions[2 * i]]
        dr, dc = route[positions[2 * i + 1]]
        grid[kr][kc] = key
        grid[dr][dc] = "D:e" if key == "e" else key.upper()
    grid[route[0][0]][route[0][1]] = "S"
    grid[route[-1][0]][route[-1][1]] = "E"
    validate_grid(grid, types)
    return grid
