# DSA — Data Structures & Algorithms Assignment

A collection of four algorithm-focused projects, each solving a classic CS problem with full implementations, interactive web/CLI interfaces, comprehensive test suites, and empirical performance analysis.

---

## Table of Contents

| # | Problem | Core Algorithm(s) | Language | Interface |
|---|---------|-------------------|----------|-----------|
| [Q1](#question-1--keypath-maze-solver-with-keys--doors) | Maze Solver with Keys & Doors | BFS, DFS, Dijkstra, A* (bitmask state) | Python | Flask Web App + CLI |
| [Q2](#question-2--closest-pair-of-points) | Closest Pair of Points | Divide & Conquer O(n log n), Brute-Force | Python | Web App + CLI |
| [Q3](#question-3--cheapest-flight-itinerary-with-coupons) | Cheapest Flights with Stops & Coupons | Layered DP (bounded level expansion) | Python | Web App + CLI |
| [Q4](#question-4--exam-scheduling-capacitated-graph-colouring) | Exam Scheduling (Graph Colouring) | DSatur, Branch & Bound (capacitated) | Java | Web App + CLI |

---

## Prerequisites

- **Python 3.10+** — no external pip packages required (all projects use only the standard library)
- **Java 17+** (for Question 4 — uses records, switch expressions, text blocks)
- **Node.js** (optional — for Question 1 frontend playback tests)

---

## Question 1 — KeyPath: Maze Solver with Keys & Doors

> **Problem:** Given an N×N grid (up to 25×25) with walls, keys (`a`–`f`), and doors (`A`–`F`), find the shortest path from Start to Exit, collecting keys to unlock doors. Supports up to 6 key/door types (T ≤ 6).

### Algorithms

| Algorithm | Optimal? | Time Complexity | Notes |
|-----------|----------|-----------------|-------|
| **BFS** | ✓ | O(N² · 2ᵀ) | Default; FIFO queue |
| **DFS** | ✗ | O(N² · 2ᵀ) | Emits backtrack traces; finds *a* path, not necessarily shortest |
| **Dijkstra** | ✓ | O(N² · 2ᵀ · log(N² · 2ᵀ)) | Min-heap priority queue |
| **A\*** | ✓ | O(N² · 2ᵀ · log(N² · 2ᵀ)) | Manhattan distance heuristic; explores fewer states than BFS |

- **State space:** `(row, col, keys_bitmask)` — max 25² × 2⁶ = 40,000 states
- **Maze generation:** Randomized DFS / recursive backtracking with guaranteed solvability

### Key Files

| File | Purpose |
|------|---------|
| [`maze.py`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question1/maze.py) | `parse_grid`, `validate_grid`, `solve` (BFS/DFS/Dijkstra/A*), `generate`, `export_csv` |
| [`app.py`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question1/app.py) | HTTP server (port 8000) + CLI (`serve`, `solve`, `generate`) |
| [`static/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question1/static) | Interactive visualizer with step-by-step playback, key inventory, door animation |
| [`tests/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question1/tests) | 21 Python + 3 Node.js tests (reference BFS verification, 270+ generated mazes, trace validation) |
| [`examples/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question1/examples) | `backtrack.csv`, `branches.csv`, `three_keys.csv`, `six_keys.csv`, `unsolvable.csv`, `first_lock.csv` |

### Run

```bash
cd question1
python3 app.py                                     # Web UI → http://127.0.0.1:8000
python3 app.py solve --types 1 --csv examples/backtrack.csv --algorithm astar --output path.csv
python3 app.py generate --size 15 --types 3 --seed 42 --output random.csv
python3 -m unittest discover -s tests -v           # Run tests
```

---

## Question 2 — Closest Pair of Points

> **Problem:** Given N points in 2D, find the pair with the smallest Euclidean distance. Compare Brute-Force vs Divide & Conquer empirically.

### Algorithms

| Algorithm | Time Complexity | Space Complexity | Comparisons |
|-----------|----------------|-----------------|-------------|
| **Brute-Force** | O(n²) | O(1) | Exactly n(n−1)/2 |
| **Divide & Conquer** | O(n log n) | O(n) | O(n log n) — 7-neighbor strip check |

- True **O(n log n)** achieved via linear merge of y-sorted sublists (not re-sorting at each level)
- Duplicate shortcut: detects coincident points in O(n) before deep recursion
- Handles extreme coordinates (±10¹⁰⁰) using `math.hypot` to prevent overflow

### Empirical Results

| N | Brute-Force | Divide & Conquer | Speedup |
|---:|---:|---:|:---:|
| 50 | 0.27 ms | 0.09 ms | 2.9× |
| 400 | 18.2 ms | 1.08 ms | 16.9× |
| 1600 | 280.3 ms | 4.77 ms | **58.8×** |

### Key Files

| File | Purpose |
|------|---------|
| [`closest_pair.py`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question2/closest_pair.py) | `brute_force`, `divide_and_conquer` (with trace recording), `benchmark`, `compare` |
| [`reports.py`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question2/reports.py) | `benchmark_csv`, `benchmark_svg` — standalone SVG chart generation |
| [`app.py`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question2/app.py) | HTTP server (port 8001) + CLI (`serve`, `solve`, `benchmark`) |
| [`static/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question2/static) | Interactive visualizer with recursive split animation, strip regions, benchmark charts |
| [`results/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question2/results) | [`ANALYSIS.md`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question2/results/ANALYSIS.md), `performance.csv`, `performance.svg` |
| [`tests/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question2/tests) | 14 tests (600+ randomized agreement trials across 6 distributions, 100 independent reference checks) |

### Run

```bash
cd question2
python3 app.py                                     # Web UI → http://127.0.0.1:8001
printf '10\n' | python3 app.py solve --seed 42      # 3-line stdout output
python3 app.py benchmark --sizes 50,100,200,400,800,1600 --output results/performance.csv --plot results/performance.svg
python3 -m unittest discover -s tests -v            # Run tests
```

---

## Question 3 — Cheapest Flight Itinerary with Coupons

> **Problem:** Find the cheapest route from city 1 to city N with at most K intermediate stops and C discount coupons (each halves one flight's cost, floor division). Return −1 if impossible.

### Algorithm

**Layered Dynamic Programming (Bounded Level Expansion)**

| Dimension | Description |
|-----------|-------------|
| **State** | `DP[flights_taken][city][coupons_used] = min cost` |
| **Time** | O(L × (N + M) × (Q + 1)), where L = min(K+1, N−1), Q = min(C, L) |
| **Space** | O(L × N × (Q + 1) + M) |

- Exploits nonnegative prices: removing cycles never increases cost → bounds search at N−1 flights
- Deterministic tie-breaking: fewer flights → fewer coupons → original edge order
- Path reconstruction via backtrack hash map

### Key Files

| File | Purpose |
|------|---------|
| [`flights.py`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question3/flights.py) | `parse_standard`, `parse_csv`, `solve` (layered DP), `generate`, `export_csv` |
| [`app.py`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question3/app.py) | HTTP server (port 8002) + CLI (`serve`, `solve`, `generate`) |
| [`static/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question3/static) | Interactive flight map with animated airplane journey, coupon highlighting, Bézier edge rendering |
| [`tests/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question3/tests) | 15 tests (250 randomized exhaustive reference comparisons, 192 generated graph solvability checks) |
| [`examples/`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question3/examples) | `standard_input.txt`, `coupon_choice.csv`, `two_coupons.csv`, `unreachable.csv`, `single_city.csv` |

### Input Format

**Option 1 — Standard Input:**
```
4 5
1 1
1 2 100
2 4 100
1 3 50
3 4 300
1 4 500
```
Line 1: `N M` (cities, flights). Line 2: `K C` (max stops, coupons). Remaining: `source dest price`.

**Option 2 — CSV file** (with `#cities,N` metadata header).

**Option 3 — Random generator** with guaranteed solvable route.

### Run

```bash
cd question3
python3 app.py                                     # Web UI → http://127.0.0.1:8002
python3 app.py solve < examples/standard_input.txt  # CLI solve
python3 app.py generate --cities 8 --flights 14 --stops 3 --coupons 2 --seed 42 --output random.csv
python3 -m unittest discover -s tests -v            # Run tests
```

---

## Question 4 — Exam Scheduling (Capacitated Graph Colouring)

> **Problem:** Schedule N exams into minimum time slots where conflicting exams (shared students) cannot overlap and each slot holds at most R exams (limited halls). Modelled as capacitated graph colouring.

### Algorithms

| Algorithm | Time | Optimal? | Notes |
|-----------|------|----------|-------|
| **DSatur Greedy** | O(N² · K) ⊆ O(N³) | ✗ | Capacity-aware; dynamic saturation ordering |
| **Branch & Bound** | O(Kᴺ) worst case | ✓ | Greedy incumbent + clique lower bound + capacity pruning + symmetry breaking + time budget |

- **Lower bound:** max(⌈N/R⌉, clique size from greedy maximal clique)
- If greedy matches lower bound, optimality is certified with 0 search nodes
- Retroactive greedy certification when B&B proves same slot count

### Key Files

| File | Purpose |
|------|---------|
| [`src/ExamScheduler.java`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question4/src/ExamScheduler.java) | `parse`, `randomGraph`, `greedy`, `exact`, `compare`, `csv`, `json`, `api`, `serve`, CLI |
| [`src/BenchmarkReport.java`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question4/src/BenchmarkReport.java) | Performance benchmarks with dual-panel SVG chart output |
| [`test.sh`](file:///Users/awanishkumar/hornet/bhang_b/DSA/question4/test.sh) | Compile + test (78,656 assertions, 680 exhaustive/random graph comparisons) |

### Test Coverage

- **680 reference graph comparisons**: all 64 graphs on 4 vertices × 5 capacities + 360 random graphs (N ≤ 8)
- Independent brute-force reference solver verifying absolute ground-truth optimality
- Constraint validation: conflict independence, capacity adherence, event replay, CSV formatting
- Edge cases: N=0, single exam, complete graphs, duplicate edges, self-loops, timeout handling

### Run

```bash
cd question4

# Web visualizer
./run.sh                                            # http://127.0.0.1:8003

# CLI — solve from stdin (Option 1)
echo "7 10 3
1 3
1 4
1 6
2 4
2 5
2 7
3 4
5 6
5 7
6 7" | ./run.sh solve --out results

# CLI — random graph (Option 2)
echo "20 4" | ./run.sh random --density 0.3 --seed 42 --out results

# Benchmark
./run.sh benchmark --sizes 6,8,10,12,16,20,24 --halls 3 --density 0.35 --out results

# Run full test suite
bash test.sh
```

---

## Project Structure

```
DSA/
├── README.md
├── .gitignore
├── docs/
│   ├── question.txt            # Q1 problem statement (Key/Door Maze)
│   ├── question1.txt           # Q2 problem statement (Closest Pair)
│   ├── question3.txt           # Q3 problem statement (Flights)
│   ├── question4.txt           # Q4 problem statement (Exam Scheduling)
│   └── front_page_format.jpg   # UI reference mockup for visualizer layout
│
├── question1/                  # KeyPath — Maze Solver
│   ├── maze.py                 # Core solver (BFS/DFS/Dijkstra/A*) + generator
│   ├── app.py                  # HTTP server (port 8000) + CLI
│   ├── static/                 # Web visualizer + playback engine
│   ├── tests/                  # 21 Python + 3 Node.js tests
│   └── examples/               # 6 example mazes
│
├── question2/                  # Closest Pair of Points
│   ├── closest_pair.py         # Brute-force + D&C solver with trace
│   ├── reports.py              # CSV/SVG benchmark report generator
│   ├── app.py                  # HTTP server (port 8001) + CLI
│   ├── static/                 # Interactive point visualizer + benchmarks
│   ├── results/                # ANALYSIS.md, performance.csv/svg
│   └── tests/                  # 14 tests (600+ randomized trials)
│
├── question3/                  # Cheapest Flight Path
│   ├── flights.py              # Layered DP solver + graph generator
│   ├── app.py                  # HTTP server (port 8002) + CLI
│   ├── static/                 # Flight map with animated journey
│   └── tests/                  # 15 tests (250+ reference comparisons)
│
└── question4/                  # Exam Scheduling
    ├── src/
    │   ├── ExamScheduler.java  # DSatur + Branch & Bound + web server
    │   └── BenchmarkReport.java
    ├── test.sh                 # 78,656 assertions
    └── static/                 # Conflict graph + timetable visualizer
```

---

## Running All Tests

```bash
# Python tests (Q1, Q2, Q3)
python3 -m unittest discover -s question1/tests -v
python3 -m unittest discover -s question2/tests -v
python3 -m unittest discover -s question3/tests -v

# Java tests (Q4)
cd question4 && bash test.sh
```

---

## Port Allocation

| Question | Port | URL |
|----------|------|-----|
| Q1 — Maze Solver | 8000 | http://127.0.0.1:8000 |
| Q2 — Closest Pair | 8001 | http://127.0.0.1:8001 |
| Q3 — Flight Path | 8002 | http://127.0.0.1:8002 |
| Q4 — Exam Scheduler | 8003 | http://127.0.0.1:8003 |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend (Q1–Q3) | Python 3.10+ (standard library only — zero pip dependencies) |
| Backend (Q4) | Java 17+ (zero external dependencies — no Maven/Gradle/JUnit/Jackson) |
| Web Servers | Python `http.server` / Java `com.sun.net.httpserver` (built-in) |
| Frontend | Vanilla HTML5, CSS3, ES6+ JavaScript, SVG |
| Testing | Python `unittest`, custom Java test runner, Node.js `node:test` |
| Visualization | In-browser SVG/Canvas, Python SVG string generation |
