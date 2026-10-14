"""Cheapest directed flight route with bounded stops and discount coupons."""
from __future__ import annotations

import csv
import io
import random


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}.")
    return value


def validate(n, edges, k, coupons):
    integer(n, "N", 1)
    integer(k, "K")
    integer(coupons, "C")
    if not isinstance(edges, list):
        raise ValueError("Flights must be a list of [from, to, price].")
    normalized = []
    for i, edge in enumerate(edges):
        if not isinstance(edge, (list, tuple)) or len(edge) != 3:
            raise ValueError(f"Flight {i + 1} needs exactly u, v, price.")
        u, v, price = edge
        integer(u, f"Flight {i + 1} origin", 1)
        integer(v, f"Flight {i + 1} destination", 1)
        integer(price, f"Flight {i + 1} price")
        if u > n or v > n:
            raise ValueError(f"Flight {i + 1}: city IDs must be between 1 and {n}.")
        normalized.append((u, v, price))
    return normalized


def parse_flights(text):
    """Manual edge rows: comma- or whitespace-separated u v price."""
    if not isinstance(text, str):
        raise ValueError("Flight input must be text.")
    edges = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.replace(",", " ").split()
        if len(parts) != 3:
            raise ValueError(f"Line {line_number}: enter u, v, price.")
        try:
            edges.append(tuple(map(int, parts)))
        except ValueError:
            raise ValueError(f"Line {line_number}: all three values must be integers.") from None
    return edges


def parse_standard(text):
    rows = [line.strip() for line in text.splitlines() if line.strip()]
    if len(rows) < 2:
        raise ValueError("Expected N M, then K C, then M flight rows.")
    try:
        n, m = map(int, rows[0].split())
        k, coupons = map(int, rows[1].split())
    except ValueError:
        raise ValueError("The first two lines must contain N M and K C.") from None
    integer(m, "M")
    if len(rows) - 2 != m:
        raise ValueError(f"M is {m}, but {len(rows) - 2} flight rows were provided.")
    edges = parse_flights("\n".join(rows[2:]))
    validate(n, edges, k, coupons)
    return n, edges, k, coupons


def parse_csv(text, cities=None):
    """CSV supports optional '#cities,N' metadata and exported annotations."""
    if not isinstance(text, str):
        raise ValueError("CSV input must be text.")
    rows = [row for row in csv.reader(io.StringIO(text.lstrip("\ufeff")), strict=True)
            if any(cell.strip() for cell in row)]
    metadata = None
    if rows and rows[0][0].strip().lower() == "#cities":
        if len(rows[0]) != 2:
            raise ValueError("CSV city metadata must be #cities,N.")
        try:
            metadata = int(rows.pop(0)[1])
        except ValueError:
            raise ValueError("CSV city count must be an integer.") from None
    has_header = bool(rows and rows[0][0].strip().lower() == "u")
    if has_header:
        header = [cell.strip().lower() for cell in rows.pop(0)]
        if header[:3] not in (["u", "v", "price"], ["u", "v", "p"]):
            raise ValueError("CSV header must start with u,v,price (or u,v,p).")
    edges = []
    for i, row in enumerate(rows, 1):
        if len(row) < 3 or (len(row) != 3 and not has_header):
            raise ValueError(f"CSV flight row {i} must contain u,v,price.")
        try:
            edges.append(tuple(int(value.strip()) for value in row[:3]))
        except ValueError:
            raise ValueError(f"CSV flight row {i} must use integer endpoints and prices.") from None
    if cities is not None:
        integer(cities, "N", 1)
        if metadata is not None and cities != metadata:
            raise ValueError("Specified N conflicts with the CSV's #cities metadata.")
    n = cities if cities is not None else metadata
    if n is None:
        if not edges:
            raise ValueError("An empty CSV needs #cities,N metadata or an explicit city count.")
        n = max(max(u, v) for u, v, _ in edges)
    validate(n, edges, 0, 0)
    return n, edges


def export_csv(n, edges, path=None):
    selected = {leg["edge_id"]: leg for leg in path or []}
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["#cities", n])
    writer.writerow(["u", "v", "price", "path", "coupon", "paid_price", "step"])
    for i, (u, v, price) in enumerate(edges):
        leg = selected.get(i)
        writer.writerow([u, v, price, "x" if leg else "",
                         "yes" if leg and leg["coupon"] else "no" if leg else "",
                         leg["paid"] if leg else "", leg["step"] if leg else ""])
    return output.getvalue()


def solve(n, edges, k, coupons):
    edges = validate(n, edges, k, coupons)
    # Nonnegative prices mean a cycle can be removed without increasing cost.
    # Thus an optimal simple path uses no more than N-1 flights, even with coupons.
    max_flights = min(k + 1, n - 1)
    max_coupons = min(coupons, max_flights)
    outgoing = [[] for _ in range(n + 1)]
    for index, (u, v, price) in enumerate(edges):
        outgoing[u].append((index, v, price))
    layers = [{(1, 0): 0}]
    parents = {}
    states_count = 1
    transitions = 0
    best = (0, 0, 0) if n == 1 else None  # cost, flights, coupons
    for count in range(1, max_flights + 1):
        layer = {}
        for (city, used), cost in layers[-1].items():
            if city == n:
                continue  # A journey ends on reaching its destination.
            for edge_id, target, price in outgoing[city]:
                for coupon in (False, True):
                    if coupon and used == max_coupons:
                        continue
                    transitions += 1
                    next_used = used + int(coupon)
                    next_cost = cost + (price // 2 if coupon else price)
                    key = target, next_used
                    if key not in layer or next_cost < layer[key]:
                        layer[key] = next_cost
                        parents[(count, target, next_used)] = (city, used, edge_id, coupon)
        layers.append(layer)
        states_count += len(layer)
        for (city, used), cost in layer.items():
            if city == n:
                candidate = cost, count, used
                if best is None or candidate < best:
                    best = candidate
        if not layer:
            break
    path = []
    if best is not None:
        total, count, used = best
        city = n
        while count:
            source, previous_used, edge_id, coupon = parents[(count, city, used)]
            price = edges[edge_id][2]
            path.append({"edge_id": edge_id, "from": source, "to": city,
                         "price": price, "coupon": coupon,
                         "paid": price // 2 if coupon else price})
            city, used, count = source, previous_used, count - 1
        path.reverse()
    running = 0
    for i, leg in enumerate(path, 1):
        running += leg["paid"]
        leg.update(step=i, running_cost=running, stops_used=i if leg["to"] != n else max(0, i - 1))
    return {"n": n, "edges": edges, "k": k, "coupons": coupons,
            "cost": best[0] if best else -1, "path": path,
            "stops": max(0, len(path) - 1), "coupons_used": sum(leg["coupon"] for leg in path),
            "full_price": sum(leg["price"] for leg in path),
            "states": states_count, "transitions": transitions,
            "csv": export_csv(n, edges, path)}


def generate(n, m, k, coupons, seed=None):
    integer(n, "N", 1); integer(m, "M"); integer(k, "K"); integer(coupons, "C")
    if seed is not None and type(seed) is not int:
        raise ValueError("Seed must be an integer.")
    if m > n * (n - 1):
        raise ValueError("M cannot exceed N × (N − 1) for generated graphs.")
    if n > 1 and m == 0:
        raise ValueError("At least one flight is needed to generate a solvable graph.")
    rng = random.Random(seed)
    if n == 1:
        return []
    flights = min(k + 1, n - 1, m)
    route = [1, *rng.sample(range(2, n), flights - 1), n]
    edges = [(u, v, rng.randint(40, 900)) for u, v in zip(route, route[1:])]
    occupied = {(u, v) for u, v, _ in edges}
    available = [(u, v) for u in range(1, n + 1) for v in range(1, n + 1)
                 if u != v and (u, v) not in occupied]
    for u, v in rng.sample(available, m - len(edges)):
        edges.append((u, v, rng.randint(40, 900)))
    rng.shuffle(edges)
    return edges
