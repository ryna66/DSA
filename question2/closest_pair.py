"""Closest-pair algorithms, recorded recursion, and reproducible benchmarks."""
from __future__ import annotations

import math
import random
import statistics
from time import perf_counter_ns

DISTRIBUTIONS = {"uniform", "integer", "collinear", "same-x", "same-y", "duplicates"}


def validate_points(points):
    if not isinstance(points, list):
        raise ValueError("Points must be a list of [x, y] coordinates.")
    normalized = []
    for index, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"Point {index + 1} must have exactly two coordinates.")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in point):
            raise ValueError(f"Point {index + 1} must contain numbers.")
        if any(not math.isfinite(v) or abs(v) > 1e100 for v in point):
            raise ValueError("Coordinates must be finite and within ±1e100.")
        normalized.append((float(point[0]), float(point[1])))
    return normalized


def generate_points(n, seed=None, distribution="uniform"):
    if type(n) is not int or n < 0:
        raise ValueError("N must be a nonnegative integer.")
    if distribution not in DISTRIBUTIONS:
        raise ValueError("Unknown point distribution.")
    if seed is not None and type(seed) is not int:
        raise ValueError("Seed must be an integer.")
    rng = random.Random(seed)
    points = []
    for _ in range(n):
        x, y = rng.uniform(-100, 100), rng.uniform(-100, 100)
        if distribution == "integer":
            x, y = rng.randint(-100, 100), rng.randint(-100, 100)
        elif distribution == "collinear":
            y = 0.7 * x + 12
        elif distribution == "same-x":
            x = 0
        elif distribution == "same-y":
            y = 0
        points.append((x, y))
    if distribution == "duplicates" and n >= 2:
        points[-1] = points[0]
    return points


def candidate(points, i, j):
    i, j = min(i, j), max(i, j)
    return math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1]), i, j


def answer(best, comparisons):
    return {"distance": best[0] if best else None,
            "pair": list(best[1:]) if best else None, "comparisons": comparisons}


def brute_force(points):
    """All N(N-1)/2 pairs. Inputs are validated once by compare()."""
    best = None
    comparisons = 0
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            current = candidate(points, i, j)
            comparisons += 1
            if best is None or current < best:
                best = current
    return answer(best, comparisons)


def divide_and_conquer(points, record=False):
    """O(N log N) using one x-sort and linear y-merges at each level."""
    ordered = sorted(range(len(points)), key=lambda i: (points[i][0], points[i][1], i))
    events = []
    comparisons = 0

    def emit(kind, lo, hi, depth, best=None, **extra):
        if record:
            events.append({"kind": kind, "lo": lo, "hi": hi, "depth": depth,
                           "best": list(best[1:]) if best else None,
                           "distance": best[0] if best else None, **extra})

    # Zero-distance cases are handled before strip processing. This also avoids
    # unbounded runs of coincident points and gives deterministic tie-breaking.
    duplicate = None
    for i, j in zip(ordered, ordered[1:]):
        if points[i] == points[j]:
            value = (0.0, min(i, j), max(i, j))
            duplicate = value if duplicate is None else min(value, duplicate)
    if duplicate is not None:
        emit("duplicate", 0, len(points), 0, duplicate)
        return {**answer(duplicate, 0), "events": events, "order": ordered}
    if len(points) < 2:
        emit("insufficient", 0, len(points), 0)
        return {**answer(None, 0), "events": events, "order": ordered}

    def recurse(lo, hi, depth):
        nonlocal comparisons
        if hi - lo <= 3:
            best = None
            emit("base", lo, hi, depth)
            for a in range(lo, hi):
                for b in range(a + 1, hi):
                    i, j = ordered[a], ordered[b]
                    current = candidate(points, i, j)
                    comparisons += 1
                    best = current if best is None else min(best, current)
                    emit("compare", lo, hi, depth, best, checking=[i, j])
            emit("merge", lo, hi, depth, best)
            return best, sorted(ordered[lo:hi], key=lambda i: (points[i][1], points[i][0], i))
        mid = (lo + hi) // 2
        # Midpoint between partitions makes strip membership symmetric, even
        # when the two middle points share x coordinates.
        split_x = points[ordered[mid - 1]][0] / 2 + points[ordered[mid]][0] / 2
        emit("split", lo, hi, depth, split_x=split_x, mid=mid)
        left, yl = recurse(lo, mid, depth + 1)
        right, yr = recurse(mid, hi, depth + 1)
        best = min(left, right)
        ysorted = []
        i = j = 0
        while i < len(yl) and j < len(yr):
            if (points[yl[i]][1], points[yl[i]][0], yl[i]) <= (points[yr[j]][1], points[yr[j]][0], yr[j]):
                ysorted.append(yl[i]); i += 1
            else:
                ysorted.append(yr[j]); j += 1
        ysorted.extend(yl[i:]); ysorted.extend(yr[j:])
        width = best[0]
        strip = [i for i in ysorted if abs(points[i][0] - split_x) <= width]
        emit("strip", lo, hi, depth, best, split_x=split_x, strip_d=width)
        # Packing bound: only the following seven y-neighbors can improve d.
        # Include equal distances to select a deterministic pair on ties.
        for a, i in enumerate(strip):
            for j in strip[a + 1:a + 8]:
                if points[j][1] - points[i][1] > best[0]:
                    break
                current = candidate(points, i, j)
                comparisons += 1
                best = min(best, current)
                emit("compare", lo, hi, depth, best, checking=[i, j],
                     split_x=split_x, strip_d=width)
        emit("merge", lo, hi, depth, best, split_x=split_x, strip_d=width)
        return best, ysorted

    best, _ = recurse(0, len(points), 0)
    emit("complete", 0, len(points), 0, best)
    return {**answer(best, comparisons), "events": events, "order": ordered}


def timed(function, points):
    start = perf_counter_ns()
    result = function(points)
    result["time_ms"] = (perf_counter_ns() - start) / 1_000_000
    return result


def agree(first, second):
    # Both implementations use the same hypot computation for candidate pairs.
    return first["distance"] == second["distance"]


def compare(points, animate=True):
    points = validate_points(points)
    brute = timed(brute_force, points)
    divide = timed(divide_and_conquer, points)
    trace = divide_and_conquer(points, record=True) if animate else divide
    return {"points": points, "brute": brute, "divide": divide,
            "agree": agree(brute, divide), "events": trace["events"], "order": trace["order"]}


def benchmark(sizes, repeats=3, seed=42, distribution="uniform"):
    if not isinstance(sizes, list) or not sizes or len(sizes) > 12:
        raise ValueError("Provide between 1 and 12 benchmark sizes.")
    if any(type(n) is not int or not 2 <= n <= 3000 for n in sizes):
        raise ValueError("Benchmark sizes must be integers from 2 to 3000.")
    if type(repeats) is not int or not 1 <= repeats <= 5:
        raise ValueError("Repeats must be an integer from 1 to 5.")
    if type(seed) is not int:
        raise ValueError("Seed must be an integer.")
    rows = []
    for n in sorted(set(sizes)):
        times = {"brute": [], "divide": []}
        agreement = True
        for repeat in range(repeats):
            points = generate_points(n, seed + n * 31 + repeat, distribution)
            # Alternate order to reduce systematic timing bias. No trace recording
            # or point generation is included inside timed algorithm calls.
            functions = [("brute", brute_force), ("divide", divide_and_conquer)]
            if repeat % 2:
                functions.reverse()
            results = {}
            for name, function in functions:
                results[name] = timed(function, points)
                times[name].append(results[name]["time_ms"])
            agreement = agreement and agree(results["brute"], results["divide"])
        rows.append({"n": n, "brute_ms": statistics.median(times["brute"]),
                     "divide_ms": statistics.median(times["divide"]), "agree": agreement})
    return {"rows": rows, "repeats": repeats, "seed": seed, "distribution": distribution,
            "agree": all(row["agree"] for row in rows)}
