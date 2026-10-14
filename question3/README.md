# Question 3 — FlightPath

Solution to `../../docs/question3.txt`, contained in `DSA/question3/`. Questions 1 and 2 remain separate.

Find the cheapest route from city **1** to city **N**, using at most **K intermediate stops** and up to **C coupons**. One coupon halves one flight's integer price, rounded down; coupons cannot be stacked on a flight.

Includes a Python solver, all three input methods, marked CSV export, and an interactive directed-flight map with journey animation. No third-party packages, build step, internet access, or API keys are required.

## Run the visualizer

Requires Python 3.10 or later. From the DSA directory:

```sh
python3 question3/app.py
```

Open **http://127.0.0.1:8002**. Questions 1 and 2 use ports 8000 and 8001, so the three applications can run at the same time. Stop the server with `Ctrl+C`. For a different port:

```sh
python3 question3/app.py serve --port 8082
```

Use the Python server rather than opening the HTML file directly.

### Use the app

1. Set N, K, and C. Enter flight rows as `u,v,price` or `u v price`. N is explicit, so isolated cities and a disconnected destination are represented correctly.
2. Alternatively, select an example, import a CSV, or open **Generate a new flight network**, choose M and a seed, and generate a graph. The generator guarantees a route within the chosen stop limit. CSV import keeps the current K and C settings.
3. Select **Find cheapest route**. The result shows the minimum cost, number of flights/stops, coupons used, and savings relative to paying full price on the **same chosen route**. This reference is not a separate coupon-free optimum.
4. Select **Play**. The aircraft follows the directed edges. Start is green, destination red, and intermediate stops become orange on arrival. Coupon flights turn gold and display `original price → discounted price`.
5. Running cost, stops used, and coupons remaining update when each flight arrives. Pause preserves the aircraft's position; step controls, the timeline, and itinerary buttons move to completed-flight boundaries. Change speed from 1× to 5×, or select **Route only** to hide unrelated edges.
6. Download the original network or the marked path. Parallel and reverse flights are drawn separately; hover an edge or price for its flight ID. Input row order identifies parallel tickets uniquely.

The browser supports 1–20 cities, at most 150 flights, and ticket prices from 0 to 1,000,000,000. N, K, C, M, endpoints, and prices are integers. K and C can be larger than the number of cities; the solver safely reduces its internal search bounds. Large dense graphs are easier to inspect in Route-only mode. CLI solving does not impose the browser's graph-size limits.

## Option 1 — Standard input

From the DSA directory:

```sh
python3 question3/app.py solve --output flight_path.csv <<'EOF'
4 5
1 1
1 2 100
2 4 100
1 3 50
3 4 300
1 4 500
EOF
```

Input:

- First line: `N M`
- Second line: `K C`
- Exactly M following flight rows: `u v p`

Standard output is a single integer:

```text
150
```

One cheapest route is **1 → 2 → 4**, with one of its two tickets reduced from 100 to 50. It uses one intermediate stop and one coupon. A marked graph is written to `flight_path.csv`.

The supplied input can also be used directly:

```sh
python3 question3/app.py solve < question3/examples/standard_input.txt
```

`solve` defaults to writing `flight_path.csv` in the current working directory. It overwrites the requested output file. Invalid input prints an error to stderr and exits with status 2. An impossible journey prints `-1`, writes the unmarked graph, and exits normally.

## Option 2 — CSV graph and K C on stdin

```sh
printf '2 1\n' | python3 question3/app.py solve \
  --csv question3/examples/coupon_choice.csv --output flight_path.csv
```

This example outputs **100**: city 1 → city 3 costs 15, and city 3 → city 6 costs `170 // 2 = 85` with a coupon. Standard input supplies exactly `K C` for CSV mode.

Accepted CSV format:

```csv
#cities,4
u,v,price
1,2,100
2,4,100
1,4,500
```

The metadata row preserves the full city count, including isolated cities. The header may use `p` instead of `price`, and a three-column headerless CSV is accepted too. Without metadata or an explicit override, N is inferred from the largest flight endpoint. To retain an isolated destination in a file without metadata:

```sh
printf '1 1\n' | python3 question3/app.py solve --csv graph.csv --cities 5
```

An explicit city count that conflicts with `#cities,N` is rejected. Empty graphs require city metadata or `--cities`. UTF-8 BOMs, blank rows, parallel flights, self-loops, and zero-price flights are supported.

### Marked output CSV

The output preserves every original flight in its original order and adds annotations:

```csv
#cities,4
u,v,price,path,coupon,paid_price,step
1,2,100,x,no,100,1
2,4,100,x,yes,50,2
1,4,500,,,,
```

- `path`: `x` for a chosen flight, otherwise empty.
- `coupon`: `yes` or `no` on chosen flights.
- `paid_price`: actual fare paid, after any discount.
- `step`: position in the journey, beginning at 1.

Exported CSVs can be imported again. Annotations are ignored when reconstructing the original graph. No annotations are added when the journey is impossible or when N = 1 and no flight is required.

## Option 3 — Random valid graph

```sh
python3 question3/app.py generate \
  --cities 8 --flights 14 --stops 3 --coupons 2 --seed 42 \
  --output random_flights.csv

printf '3 2\n' | python3 question3/app.py solve \
  --csv random_flights.csv --output flight_path.csv
```

Generation first installs a directed route from 1 to N with no more than K+1 flights, then adds random directed edges. It creates exactly M distinct directed connections, without self-loops; input files can still contain parallel flights or loops. Prices are integers from 40 to 900. Reusing the same parameters and seed reproduces the graph.

For N > 1, at least one flight is required, and M cannot exceed N(N−1). For N = 1, M must be 0. K = 0 forces the guaranteed route to be direct. A coupon is optional, so generation does not depend on spending every coupon.

## Algorithm and correctness

The solver uses layered dynamic programming. Define:

```text
DP[f][v][c] = minimum cost to reach city v
              using exactly f flights and exactly c coupons
```

Initialize `DP[0][1][0] = 0`. For every outgoing flight `(u, v, p)` from a reachable state:

```text
Pay full price:  DP[f+1][v][c]   ← min(existing, DP[f][u][c] + p)
Use one coupon: DP[f+1][v][c+1] ← min(existing, DP[f][u][c] + floor(p/2))
```

Only states within the flight and coupon bounds are admitted. Parents store the exact flight ID and whether a coupon was applied, allowing path and CSV reconstruction. The answer is the minimum over all permitted flight counts and coupon counts at city N. Equal-cost routes prefer fewer flights, then fewer coupons; remaining ties follow input order.

K counts **intermediate cities**, so at most K+1 flights are allowed. Destination is not counted as a stop. All prices are nonnegative, so removing a cycle cannot increase cost or consume more coupons; some optimal route is simple. Consequently the internal flight bound is `L = min(K+1, N−1)` and the coupon bound is `Q = min(C, L)`. This also makes very large K and C inexpensive on a small graph. Search time is O(L × (N+M) × (Q+1)), and storage is O(L × N × (Q+1) + M), including parents. N = 1 is answered immediately with cost 0.

Important cases covered:

- K = 0: only a direct flight can reach N (unless N = 1).
- C = 0: all tickets are full price.
- C exceeds the flight count: at most one coupon still applies per flight.
- Odd prices: 101 becomes 50; price 1 becomes 0.
- No valid route within the limit: return -1, even if a longer route exists.
- Directed, parallel, disconnected, self-loop, and zero-price edges.
- Coupons need not all be used. The best discounted route may differ from the best full-price route.
- Nonnegative integer prices use exact Python integer arithmetic.

## Verification

From DSA:

```sh
python3 -m unittest discover -s question3/tests -v
node --check question3/static/app.js  # Optional; Node is not required to run.
```

All 15 tests passed. They include 250 small random graph comparisons against an independent exhaustive walk solver and 192 generated graphs checked for a route within the bounds. Tests also validate path continuity, coupon arithmetic, CSV round-trips and parallel-edge annotations, stdin and CSV CLI modes, HTTP handlers, invalid input, and the corner cases above.

JavaScript syntax and HTML element bindings were checked. Live browser layout and animation remain unverified in the development sandbox because localhost binding and headless-browser launch were unavailable during this session.

## Project files

```text
question3/
  app.py                  Local HTTP server (8002), CLI solver and generator
  flights.py              Validation, parsing, dynamic programming, CSV export
  static/index.html       Flight planning interface
  static/styles.css       Responsive layout and flight-map styles
  static/app.js           Directed graph, smooth aircraft playback, downloads
  examples/               Four CSV graphs and a standard-input example
  tests/                  Algorithm, HTTP, and CLI tests
```

JSON endpoints: `GET /api/examples`, `POST /api/solve` with `{n, edges, k, coupons}` (or `text` instead of `edges`), `POST /api/import` with `{csv, cities?}`, and `POST /api/generate` with `{n, m, k, coupons, seed?}`. Everything runs locally; the server serves only `question3/static/`.
