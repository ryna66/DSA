# Question 2 — Closest Pair Lab

Solution to `../../docs/question1.txt`, kept in this separate `question2/` folder. The original maze project remains in the DSA root.

Implements **brute force** and **divide-and-conquer** closest-pair algorithms, command-line output, a browser visualization with recursive animation, and measured performance comparisons. Uses only the Python standard library and plain HTML/CSS/JavaScript. No installation, build, internet access, or API keys are required.

## Run the interactive app

Python 3.10 or later:

```sh
# From the DSA folder:
python3 question2/app.py
```

Open **http://127.0.0.1:8001**. Question 1 uses port 8000, so both projects can run simultaneously. Stop with `Ctrl+C`. To use another port:

```sh
python3 question2/app.py serve --port 8081
```

Use the Python server instead of opening `static/index.html` directly: the browser calls the Python algorithms.

1. Choose N, a seed, and an arrangement, then select **Generate points**. Available arrangements include random floating-point and integer coordinates, collinear points, a shared x or y coordinate, and duplicates.
2. Both algorithms run on exactly the same points. Their cards show minimum distance to six decimal places, pair IDs and coordinates, time in milliseconds, and distance-comparison counts.
3. Select **Play** to replay divide-and-conquer. Pause, step in either direction, jump to either end, or scrub the timeline. Speed is adjustable from 1–50 frames per second.
4. Blue split lines show recursive divisions. Shaded strips have width **2d**, where d is the smaller distance returned by the two halves before cross-strip comparisons. The current comparison, region, depth, and local minimum are displayed. Points outside the active subproblem fade.
5. The brute-force answer is an orange reference. Divide-and-conquer uses blue. When the final pairs coincide, a thick orange line, a thinner dashed blue line, and concentric endpoint rings keep both visible. Use the legend checkboxes to inspect either algorithm separately. Hover points for full coordinates and IDs.
6. Click the plane to add a point, or use **Paste coordinates** to enter x,y pairs. Select **Compare algorithms** after editing. The **Points CSV** button exports the current input. The plot uses equal x/y units so Euclidean geometry is not distorted.
7. Under **How does it scale?**, choose increasing sizes and repeats, then select **Run performance test**. The time-versus-N graph and table fill in as real measurements finish. Export them with **Results CSV**.

The browser supports 0–2000 points; performance tests support up to 12 sizes from 2–3000 with 1–5 repeats. Coordinates must be finite and within ±1e100. These limits keep the interactive brute-force workload manageable. CLI generation does not impose the browser's N cap. Very large magnitudes use scientific notation in the interface; pair tooltips retain full input values.

## Required standard-input / standard-output format

From the DSA root:

```sh
printf '10\n' | python3 question2/app.py solve --seed 42
```

The first stdin line is integer **N**. The next N coordinate pairs are generated randomly. The program prints exactly three lines:

```text
Brute-Force: <distance, 6 decimals> (<x1>, <y1>) (<x2>, <y2>)
Divide-and-Conquer: <distance, 6 decimals> (<x1>, <y1>) (<x2>, <y2>)
Time: Brute-Force <milliseconds> ms; Divide-and-Conquer <milliseconds> ms
```

Coordinates are also printed to six decimal places. The chosen seed makes inputs reproducible; elapsed times naturally vary. Other examples:

```sh
printf '2\n' | python3 question2/app.py solve --seed 7
printf '100\n' | python3 question2/app.py solve --distribution integer
printf '20\n' | python3 question2/app.py solve --distribution duplicates
printf '20\n' | python3 question2/app.py solve --distribution same-x
printf '0\n' | python3 question2/app.py solve
```

For N < 2, both result lines explicitly report `undefined — no pair (N < 2)`; the third line still gives execution times. Negative or invalid N is rejected. CLI exits with status 1 if computed minimum distances disagree, and status 2 for invalid input.

## Algorithms and corner cases

**Brute force:** enumerate every unordered pair, calculate Euclidean distance with `math.hypot`, and retain the minimum. Exactly N(N−1)/2 distance evaluations; O(N²) time and O(1) auxiliary search space.

**Divide-and-conquer:** sort point IDs by x (then y and original ID), split by rank, and recurse. Subproblems of at most three points use brute force. Each recursion returns its points sorted by y; the parent combines those lists with a linear merge. From the smaller distance d of the two halves, construct the central strip and compare each strip point against at most the next seven points in y order, stopping earlier if their y separation exceeds the current minimum. This gives O(N log N) time and O(N) auxiliary search space. Optional animation storage is O(N log N) in the worst case and is excluded from timing runs.

Corner cases:

- **Duplicates:** scan the x-sorted points for identical coordinates and return a zero-distance pair before recursion. Original point IDs keep coincident points distinct. The animation explains this shortcut; no unnecessary splitting is performed.
- **Same x, same y, or collinear points:** partition by sorted rank, not by `x < split`, so neither side accidentally loses points or becomes unbalanced.
- **N = 2:** return the sole pair.
- **N = 0 or 1:** return `distance: null`, `pair: null`; no infinity or invented pair.
- **Ties:** each algorithm uses point IDs to break equal-distance ties deterministically among checked candidates. Different valid pairs may have the same minimum; agreement checks compare the distances rather than requiring identical pair IDs.
- **Large and tiny finite coordinates:** `math.hypot` avoids the overflow/underflow caused by squaring coordinates directly. Negative coordinates are fully supported.

Every solve checks exact equality between the two returned floating-point distances. Both algorithms use the same distance primitive. Tests additionally compare with an independent exhaustive `math.dist` reference. Display rounding does not participate in correctness checks.

## Performance measurements and analysis

Reproduce the supplied report from the DSA root:

```sh
python3 question2/app.py benchmark \
  --sizes 50,100,200,400,800,1600 --repeats 3 --seed 42 \
  --output question2/results/performance.csv \
  --plot question2/results/performance.svg
```

The standalone [SVG chart](results/performance.svg) and [CSV measurements](results/performance.csv) are already included. See [results/ANALYSIS.md](results/ANALYSIS.md) for the measured results and interpretation.

Methodology: generate the input before timing, run both algorithms on that same input, alternate their execution order across repetitions, and report the median. Each repetition uses a reproducible seed derived from the requested seed, N, and repeat index. Timings include the algorithm's own sorting and search, but exclude generation, input validation, animation recording, network time, and plotting. Every repetition verifies minimum-distance agreement. The interface runs performance work separately from its own solve requests to avoid overlapping those workloads.

These are actual measurements, not synthetic curves. Small input sizes, Python overhead, duplicate shortcuts, coordinate distributions, system load, and timer resolution can affect results. The report illustrates growth on this machine; it does not claim a universal speedup.

## Tests

From the DSA folder:

```sh
python3 -m unittest discover -s question2/tests -v
node --check question2/static/app.js  # Optional; Node is not needed to run the app.
```

The 14 tests cover all required corner cases, 600 generated datasets across six distributions and ten sizes, 100 independent-reference cases, cross-split closest pairs, recursion events, input validation, HTTP requests, CLI output, and CSV/SVG generation.

Python tests, JavaScript syntax, HTML element bindings, actual CLI runs, and the saved benchmark were verified. Live browser layout and interaction checks remain unverified because the development sandbox blocked localhost binding and headless-browser launch during this session.

## Files

```text
question2/
  app.py                    Local server (port 8001), stdin solver, benchmark CLI
  closest_pair.py           Both algorithms, recursion events, benchmarks
  reports.py                Benchmark CSV and standalone SVG generation
  static/index.html         Interactive interface
  static/styles.css         Responsive solid-color design
  static/app.js              SVG plots, recursive playback, benchmark controls
  tests/                    Algorithm, HTTP, and CLI tests
  results/performance.csv   Actual measured running times
  results/performance.svg   Standalone time-versus-N chart
  results/ANALYSIS.md        Methodology and interpretation
```

The server serves only `question2/static/` and exposes JSON POST endpoints `/api/generate`, `/api/solve`, and `/api/benchmark`. Inputs stay on the local machine.
