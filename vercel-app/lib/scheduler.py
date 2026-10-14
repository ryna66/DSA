"""Dependency-free Python exam timetabling with capacity-aware DSatur and exact branch & bound."""
from __future__ import annotations

import math
import random
import re
import time


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def graph(n: int, halls: int, edges: list[list[int]]) -> dict:
    require(isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 200, "N must be between 0 and 200.")
    require(isinstance(halls, int) and not isinstance(halls, bool) and 1 <= halls <= 1000, "R must be between 1 and 1000.")
    if not isinstance(edges, (list, tuple)):
        raise ValueError("Edges must be a list of pairs.")

    adjacency = [[False] * n for _ in range(n)]
    unique = []
    for edge in edges:
        require(isinstance(edge, (list, tuple)) and len(edge) == 2, "Each conflict needs exactly two course IDs.")
        try:
            u_val, v_val = int(edge[0]), int(edge[1])
        except (ValueError, TypeError):
            raise ValueError("Course IDs must be integers.")
        u, v = u_val - 1, v_val - 1
        require(0 <= u < n and 0 <= v < n, "Course IDs must be between 1 and N.")
        require(u != v, "A course cannot conflict with itself.")
        if not adjacency[u][v]:
            adjacency[u][v] = adjacency[v][u] = True
            unique.append([min(u, v) + 1, max(u, v) + 1])

    unique.sort(key=lambda a: (a[0], a[1]))
    neighbors = [[v for v in range(n) if adjacency[u][v]] for u in range(n)]
    return {
        'n': n,
        'halls': halls,
        'conflicts': adjacency,
        'edges': unique,
        'neighbors': neighbors
    }


def parse(text: str) -> dict:
    tokens = text.strip().split()
    if len(tokens) < 3:
        raise ValueError("Expected N M R, followed by exactly M pairs of integer course IDs.")
    try:
        n = int(tokens[0])
        m = int(tokens[1])
        halls = int(tokens[2])
    except ValueError:
        raise ValueError("Expected N M R, followed by exactly M pairs of integer course IDs.")

    require(0 <= m <= 40000, "M must be between 0 and 40000.")
    if len(tokens) != 3 + 2 * m:
        if len(tokens) > 3 + 2 * m:
            raise ValueError("Extra input after the M conflict rows.")
        else:
            raise ValueError("Expected N M R, followed by exactly M pairs of integer course IDs.")

    edges = []
    idx = 3
    for _ in range(m):
        try:
            u = int(tokens[idx])
            v = int(tokens[idx + 1])
        except ValueError:
            raise ValueError("Course IDs must be integers.")
        edges.append([u, v])
        idx += 2

    return graph(n, halls, edges)


def random_graph(n: int, halls: int, density: float = 0.3, seed: int = 42) -> dict:
    require(isinstance(density, (int, float)) and math.isfinite(density) and 0 <= density <= 1, "Density must be from 0 to 1.")
    require(isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 200, "N must be between 0 and 200.")
    rng = random.Random(seed)
    edges = []
    for u in range(1, n + 1):
        for v in range(u + 1, n + 1):
            if rng.random() < density:
                edges.append([u, v])
    return graph(n, halls, edges)


def degrees(g: dict) -> list[int]:
    conflicts = g['conflicts']
    return [sum(1 for c in conflicts[u] if c) for u in range(g['n'])]


def choose(g: dict, colors: list[int], degree: list[int]) -> int:
    """Choose unassigned course with highest saturation, then degree, then lowest ID."""
    n = g['n']
    neighbors = g['neighbors']
    chosen = -1
    maximum = -1
    seen = [False] * (n + 1)

    for u in range(n):
        if colors[u] == 0:
            used_colors = []
            saturation = 0
            for v in neighbors[u]:
                c = colors[v]
                if c != 0 and not seen[c]:
                    seen[c] = True
                    used_colors.append(c)
                    saturation += 1
            for c in used_colors:
                seen[c] = False

            if chosen < 0 or saturation > maximum or (saturation == maximum and degree[u] > degree[chosen]):
                chosen = u
                maximum = saturation

    return chosen


def fits(g: dict, course: int, slot: int, colors: list[int], loads: list[int]) -> bool:
    if loads[slot] >= g['halls']:
        return False
    for v in g['neighbors'][course]:
        if colors[v] == slot:
            return False
    return True


def lower_bound(g: dict, degree: list[int]) -> int:
    """Valid lower bound from capacity and a constructed clique."""
    n = g['n']
    halls = g['halls']
    if n == 0:
        return 0
    lower = (n + halls - 1) // halls
    order = sorted(range(n), key=lambda i: (-degree[i], i))
    conflicts = g['conflicts']
    for seed in order:
        clique = [seed]
        for v in order:
            if v != seed:
                joins = True
                for u in clique:
                    if not conflicts[u][v]:
                        joins = False
                        break
                if joins:
                    clique.append(v)
        if len(clique) > lower:
            lower = len(clique)
    return lower


def csv_output(g: dict, colors: list[int], slots: int) -> str:
    header = ["Slot"] + [f"Hall {hall}" for hall in range(1, g['halls'] + 1)]
    lines = [",".join(header)]
    for slot in range(1, slots + 1):
        row = [f"Slot {slot}"]
        count = 0
        for course in range(g['n']):
            if colors[course] == slot:
                row.append(str(course + 1))
                count += 1
        while count < g['halls']:
            row.append("")
            count += 1
        lines.append(",".join(row))
    return "\n".join(lines) + "\n"


def greedy(g: dict) -> dict:
    start = time.monotonic_ns()
    n = g['n']
    degree = degrees(g)
    colors = [0] * n
    loads = [0] * (n + 2)
    lower = lower_bound(g, degree)
    slots = 0
    events = []

    for _ in range(n):
        u = choose(g, colors, degree)
        slot = 1
        while slot <= slots and not fits(g, u, slot, colors, loads):
            slot += 1
        slots = max(slots, slot)
        colors[u] = slot
        loads[slot] += 1
        events.append({'course': u + 1, 'slot': slot})

    return {
        'algorithm': 'DSatur greedy',
        'slots': slots,
        'optimal': (slots == lower),
        'timedOut': False,
        'lowerBound': lower,
        'assignment': list(colors),
        'events': events,
        'timeMs': (time.monotonic_ns() - start) / 1_000_000.0,
        'searchNodes': n,
        'csv': csv_output(g, colors, slots)
    }


class Search:
    def __init__(self, g: dict, initial: dict, deadline: int):
        self.g = g
        self.degree = degrees(g)
        self.colors = [0] * g['n']
        self.loads = [0] * (g['n'] + 2)
        self.lower = initial['lowerBound']
        self.best_slots = initial['slots']
        self.best = list(initial['assignment'])
        self.best_order = list(initial['events'])
        self.deadline = deadline
        self.path = []
        self.nodes = 0
        self.timed_out = False

    def visit(self, assigned: int, used: int) -> None:
        if self.best_slots == self.lower or self.timed_out:
            return
        if time.monotonic_ns() >= self.deadline:
            self.timed_out = True
            return

        self.nodes += 1

        if assigned == self.g['n']:
            self.best_slots = used
            self.best = list(self.colors)
            self.best_order = list(self.path)
            return

        # Capacity pruning
        halls = self.g['halls']
        free = 0
        for slot in range(1, used + 1):
            free += halls - self.loads[slot]
        extra = max(0, self.g['n'] - assigned - free)
        if used + (extra + halls - 1) // halls >= self.best_slots:
            return

        course = choose(self.g, self.colors, self.degree)

        # Symmetry breaking: only one new slot label (used + 1)
        for slot in range(1, used + 2):
            if slot >= self.best_slots:
                break
            if not fits(self.g, course, slot, self.colors, self.loads):
                continue

            self.colors[course] = slot
            self.loads[slot] += 1
            self.path.append({'course': course + 1, 'slot': slot})

            self.visit(assigned + 1, max(used, slot))

            self.path.pop()
            self.loads[slot] -= 1
            self.colors[course] = 0

            if self.timed_out or self.best_slots == self.lower:
                return


def exact(graph_obj: dict, time_limit_ms: int = 2000) -> dict:
    require(0 <= time_limit_ms <= 60000, "Exact search budget must be 0–60000 ms.")
    started = time.monotonic_ns()
    initial = greedy(graph_obj)
    deadline = started + int(time_limit_ms * 1_000_000)
    search = Search(graph_obj, initial, deadline)
    search.visit(0, 0)
    optimal = (search.best_slots == search.lower or not search.timed_out)
    return {
        'algorithm': 'Exact branch & bound',
        'slots': search.best_slots,
        'optimal': optimal,
        'timedOut': search.timed_out,
        'lowerBound': search.best_slots if optimal else search.lower,
        'assignment': search.best,
        'events': search.best_order,
        'timeMs': (time.monotonic_ns() - started) / 1_000_000.0,
        'searchNodes': search.nodes,
        'csv': csv_output(graph_obj, search.best, search.best_slots)
    }


def compare(graph_obj: dict, budget_ms: int = 2000) -> dict:
    first = greedy(graph_obj)
    second = exact(graph_obj, budget_ms)
    # A completed exact search may also certify the greedy result.
    if second['optimal'] and first['slots'] == second['slots'] and not first['optimal']:
        first = dict(first)
        first['optimal'] = True
        first['lowerBound'] = second['slots']
    return {
        'graph': graph_obj,
        'greedy': first,
        'exact': second
    }


def graph_map(g: dict) -> dict:
    return {
        'n': g['n'],
        'halls': g['halls'],
        'edges': g['edges']
    }


def comparison_map(c: dict) -> dict:
    return {
        'graph': graph_map(c['graph']),
        'greedy': c['greedy'],
        'exact': c['exact']
    }


def form_graph(data: dict) -> dict:
    try:
        n = int(data.get('n', 10))
    except (ValueError, TypeError):
        raise ValueError("N must be an integer.")
    try:
        halls = int(data.get('halls', 3))
    except (ValueError, TypeError):
        raise ValueError("R must be an integer.")
    require(n <= 60 and halls <= 20, "The visualizer supports at most 60 courses and 20 halls.")

    raw = data.get('edges', '')
    if raw is None:
        raw = ''
    raw = raw.strip()
    pairs = []
    if raw:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            tokens = re.split(r'[\s,]+', line)
            require(len(tokens) == 2, "Each row needs two course IDs: u,v.")
            try:
                u = int(tokens[0])
                v = int(tokens[1])
            except ValueError:
                raise ValueError("Course IDs must be integers.")
            pairs.append([u, v])

    return graph(n, halls, pairs)
