# ExamSlot — Exam Timetabling with Graph Coloring

**Question 4 · DSA Project · Java**

Schedule N university exams into the minimum number of time slots, respecting:
- **Conflict constraints**: courses sharing students cannot occupy the same slot.
- **Capacity constraints**: at most R exams per slot (limited exam halls).

## Algorithms

### 1. DSatur Greedy Heuristic
A capacity-aware DSatur (Degree of Saturation) algorithm:
1. Pick the unassigned course with the highest saturation (number of distinct slots used by its neighbors), breaking ties by degree, then course ID.
2. Assign it to the first valid slot (no conflict, hall capacity not exceeded).
3. Repeat until all courses are assigned.

**Time complexity**: O(N² · k) where k is the number of slots used.

### 2. Exact Branch & Bound
- Seeds with the greedy solution as an upper bound.
- Computes a lower bound from capacity (⌈N/R⌉) and a greedy clique search.
- Explores assignments using DSatur ordering with pruning:
  - Capacity pruning: if remaining courses can't fit in existing free slots without exceeding the best-known solution.
  - Symmetry breaking: only one canonical label for a new (empty) slot.
- Reports whether the result is **proven optimal** or the best found within the time budget.

## Input Formats

### Option 1 — Manual conflict list
```
N M R
u₁ v₁
u₂ v₂
...
```
Where N = number of courses, M = number of conflict edges, R = halls per slot.

### Option 2 — Random graph
Provide `N R` on stdin and use the `random` command with `--density` and `--seed` flags.

## Output

1. **Minimum number of slots** for each algorithm, with optimality proof status.
2. **Slot-wise list**: `Slot 1: 2, 5, 9` etc.
3. **CSV timetable**: rows = slots, columns = halls.

## Project Structure

```
question4/
├── src/
│   ├── ExamScheduler.java      # Core algorithms, HTTP server, CLI
│   └── BenchmarkReport.java    # CLI benchmark with CSV + SVG output
├── static/
│   ├── index.html              # Web visualization UI
│   ├── styles.css              # Responsive styling
│   └── app.js                  # Interactive graph, timetable, animation, charts
├── tests/
│   └── ExamSchedulerTest.java  # 78,000+ assertions, exhaustive + random verification
├── examples/
│   └── greedy_gap.txt          # Input where greedy uses more slots than optimal
├── results/                    # Pre-generated output files
│   ├── greedy_timetable.csv
│   ├── exact_timetable.csv
│   ├── comparison.json
│   ├── benchmark.csv
│   └── benchmark.svg
├── run.sh                      # Compile and run
├── test.sh                     # Compile and test
├── .gitignore
└── README.md
```

## How to Run

### Prerequisites
- **Java 17+** (uses records, pattern matching, sealed types)

### Start the Web Visualization Server
```bash
./run.sh
# Opens at http://127.0.0.1:8003
```

### Solve from stdin (CLI)
```bash
# Option 1: Manual conflict list
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

# Option 2: Random graph (N R on stdin)
echo "20 4" | ./run.sh random --density 0.3 --seed 42 --out results
```

### Run Benchmark Comparison
```bash
./run.sh benchmark --sizes 6,8,10,12,16,20,24 --halls 3 --density 0.35 --out results
```
Outputs `benchmark.csv` and `benchmark.svg` showing slots used and running time as N increases.

### Run Tests
```bash
./test.sh
```
Verifies all 680 exhaustive/random graph comparisons against an independent brute-force reference, plus edge cases, animation consistency, CSV format, API endpoints, and CLI integration.

## Web Visualization Features

1. **Conflict graph** — nodes colored by assigned slot, edges highlight conflicts.
2. **Timetable grid** — rows = slots, columns = halls, matching color scheme.
3. **Assignment animation** — step through or auto-play the order in which courses are placed.
4. **Benchmark charts** — slots used and running time vs. N, comparing both algorithms.
5. **CSV download** — export the timetable for either algorithm.
6. **Built-in examples** — odd cycle, capacity-only, complete graph, greedy gap, single course, empty graph.

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8003` | HTTP server port |
| `--static` | `./static` | Path to static files |
| `--budget` | `5000` | Exact search time limit (ms) |
| `--out` | `.` | Output directory for CSV/JSON |
| `--density` | `0.3` | Random graph edge density |
| `--seed` | `42` | Random graph seed |
| `--sizes` | `6,8,10,12,16,20,24` | Benchmark course counts |
| `--halls` | `3` | Halls per slot (R) |

## Example Output

```
DSatur greedy: 4 slots; proven optimal: no; time: 0.042000 ms
Slot 1: 1, 2
Slot 2: 3, 5
Slot 3: 4, 7
Slot 4: 6
Exact branch & bound: 3 slots; proven optimal: yes; time: 0.156000 ms
Slot 1: 1, 5
Slot 2: 2, 3, 6
Slot 3: 4, 7
```

This example (from `examples/greedy_gap.txt`) shows the greedy heuristic using 4 slots while branch & bound proves 3 is optimal.
