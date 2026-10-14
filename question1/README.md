# KeyPath — keys, doors, and shortest paths

A complete solution to `../docs/question.txt`: Python BFS, DFS, Dijkstra, and A* solvers, a command-line interface, and an interactive browser visualizer. The interface follows the reference’s input → visualization → playback layout, using solid colors and responsive panels.

## Run the app

Requires **Python 3.10 or later**. No pip packages, Node installation, build step, internet connection, or API keys are required.

```sh
cd /Users/awanishkumar/hornet/bhang_b/DSA
python3 app.py
```

Open **http://127.0.0.1:8000** in a browser. Stop with `Ctrl+C`. If port 8000 is occupied, run `python3 app.py serve --port 8080` and open port 8080 instead. Use the Python server rather than opening `index.html` directly; the browser calls the Python solver.

1. Choose **Manual input**, **Upload CSV**, or **Random maze**. Six ready-made examples include branches and dead ends, a necessary key detour, all six keys, and an impossible maze.
2. Set **T**, the number of distinct key/door types in the maze. For random input, choose a size, optionally enter a reproducible seed, and select **Generate maze**.
3. Choose **BFS**, **DFS**, **Dijkstra**, or **A*** and select **Visualize search**. Actual search decisions animate first, then the resulting route. The result appears when exploration ends. BFS, Dijkstra, and A* guarantee a shortest route; DFS finds a valid route that may be longer. An impossible maze returns **-1** and still animates its search. Autoplay respects the browser’s reduced-motion preference.
4. Pause, step backward/forward, skip to either end, or scrub the timeline across both search and route phases. Change speed from 1 to 50 frames per second, or select **Jump to route**. Rewinding restores the visited cells, frontier, branch, keys, and doors at that frame.
5. Download the original maze or the marked path as CSV. The original maze thumbnail remains visible beside the visualization.

The visualization distinguishes **visited cells** (pale blue), **waiting cells / frontier** (yellow), the **active candidate branch** (purple), and the **final route** (blue). Red outlines identify wall/door checks that failed. Four direction cards explain each neighbor decision: queued, already seen, locked, wall, or boundary. DFS emits explicit backtracking frames.

**Show visited cells** toggles accumulated search shading. The counters and journey log advance with the animation. “States explored” and “Waiting states” count position/inventory states, so they can exceed the number of cells. During exploration, the keyring belongs to the current candidate branch; switching branches may change its keys. During the final route, keys stay collected. This depicts a search over possibilities, not a single traveler jumping between unrelated positions. The search stops at the exit or when all reachable states have been checked.

## Input format

Use a square N × N grid, from 2 × 2 to 25 × 25, with exactly one start and one exit. CSV files have no header or row-number column. Manual input accepts commas, whitespace, or compact single-character rows. Empty lines and a UTF-8 BOM are tolerated.

| Symbol | Meaning |
| --- | --- |
| `.` | Open cell |
| `#` | Wall |
| `S` | Start |
| `E` | Exit |
| `a`–`f` | Keys, collected automatically and never consumed |
| `A`, `B`, `C`, `D`, `F` | Corresponding doors |
| `D:e` | Door corresponding to key `e` |

**The question assigns `E` two meanings.** This implementation reserves `E` for the exit and uses `D:e` for door e. Use comma- or whitespace-separated input for grids containing `D:e`. This allows all six key/door types without guessing which `E` is the exit.

T is the number of distinct letter types present among keys and doors, from 1 to 6. For example, `a`, `A`, and `A` together count as one type. Manual mazes may have duplicate keys/doors or a door with no available key; the selected search determines whether the exit can still be reached. Unused keys need not be collected.

Example, T = 1:

```csv
S,a,A,E
#,#,#,#
#,#,#,#
#,#,#,#
```

Answer: **3** moves. This example’s marked path is:

```csv
x(S),x(a),x(A),x(E)
#,#,#,#
#,#,#,#
#,#,#,#
```

Ordinary path cells become `x`; special path cells become `x(S)`, `x(E)`, `x(a)`, `x(A)`, or `x(D:e)`, preserving their identity. Cells outside the path are unchanged. Exported paths can be imported again: `x` becomes floor, and `x(symbol)` restores its original symbol. A CSV marks the visited positions; the ordered route, including repeated visits, is available in the visualizer and solve API. For an unreachable exit, the CSV contains the original maze with no path marks.

## Command-line use

Read T from the first line of standard input and the grid from a CSV:

```sh
printf '1\n' | python3 app.py solve --csv examples/backtrack.csv --output path.csv
```

Standard output is exactly `8` followed by a newline. The solution CSV is written to `path.csv`.

Alternatively, provide T and the grid entirely through stdin:

```sh
python3 app.py solve --output path.csv <<'EOF'
1
S,a,A,E
#,#,#,#
#,#,#,#
#,#,#,#
EOF
```

Or supply T as an argument:

```sh
python3 app.py solve --types 6 --csv examples/six_keys.csv --output path.csv
python3 app.py generate --size 15 --types 6 --seed 42 --output random.csv
python3 app.py solve --types 6 --csv random.csv --output path.csv
python3 app.py solve --algorithm astar --types 1 --csv examples/branches.csv --output astar_path.csv
python3 app.py solve --algorithm dfs --types 1 --csv examples/branches.csv --output dfs_path.csv
```

`solve` defaults to `shortest_path.csv`; `generate` defaults to `maze.csv`. These commands overwrite the specified output file. Invalid input prints an error to stderr and exits with status 2. A valid but unsolvable maze prints `-1` and exits normally.

## Algorithm and generation

All algorithms search states `(row, column, key_mask)`. Each bit represents a held key. A neighbor is valid when it is inside the grid, is not a wall, and any door there has a matching held key. Entering a key adds its bit. The visited state includes inventory, so returning to a cell with a new key remains possible. Parent states reconstruct routes.

| Algorithm | Search strategy | Shortest route? |
| --- | --- | --- |
| BFS (default) | FIFO queue; increasing move count | Yes |
| DFS | LIFO stack; deep branches, then backtracking | Not guaranteed |
| Dijkstra | Priority queue ordered by accumulated move cost | Yes |
| A* (`astar` in CLI/API) | Priority queue ordered by cost + Manhattan distance to exit | Yes |

All moves cost one. Dijkstra therefore expands in the same order as BFS under the shared tie-breaking. A* uses an admissible, consistent Manhattan heuristic: walls and key requirements can only increase the true remaining distance. Priority-queue searches replace more expensive tentative states when a cheaper route is found.

With V = N² × 2ᵀ, BFS/DFS take O(V) time; Dijkstra/A* take O(V log V) time. State storage and event recording are O(V), since each state has at most four neighbors. There are at most 40,000 distinct position/inventory combinations with the application limits. Neighbor checks use up, right, down, left order. DFS pushes children in reverse order so it visits the first available direction first.

Every run records state nodes, parent links, expansion events, four neighbor checks, frontier additions/removals, DFS backtracking, and a terminal goal/exhausted event. `static/playback.js` incrementally reconstructs this record; it resets and replays when scrubbing backward. The route is hidden until the search reaches its terminal event. A DFS export is named `dfs_path.csv` in the browser to distinguish it from a guaranteed shortest-path export.

Random mazes use randomized depth-first carving to create a connected corridor tree, choose a distant exit, and place exactly T keys and T doors in valid order along its unique route. A winding-corridor fallback ensures enough placement space. Every generated pair must be traversed, and every generated maze is solvable. Supported sizes are odd integers from 7 to 25; seeds reproduce the same maze.

## Project files

```text
app.py                Local HTTP server and command-line interface
maze.py               Parsing, validation, four search algorithms, CSV export, generation
static/index.html     Accessible interface and instructions
static/styles.css     Responsive layout, pair colors, animations
static/app.js         Input workflows, search rendering, playback controls, downloads
static/playback.js    Search timeline and rewind state reconstruction
examples/*.csv        Six example mazes
tests/test_maze.py    Solver, generator, CSV and differential tests
tests/test_app.py     HTTP-handler and command-line integration tests
tests/test_algorithms.py  Algorithm correctness and search trace tests
tests/test_playback.cjs   Search playback and rewind tests (optional Node)
```

The server binds to loopback and serves only `static/`. API endpoints are `GET /api/examples`, `POST /api/solve` (JSON `{ "text": "CSV grid", "types": 3 }` or `{ "grid": [["S", "E"], ["a", "A"]], "types": 1 }`), and `POST /api/generate` (JSON `{ "size": 11, "types": 3, "seed": 42 }`). The solve request also accepts `"algorithm": "bfs"`, `"dfs"`, `"dijkstra"`, or `"astar"` (default BFS). Its response includes `algorithm`, `optimal` (whether the algorithm guarantees a shortest route), integer length, ordered path, per-step key inventory and events, searched cells, state counts, marked CSV, state `nodes`, and the full search `trace`. Each trace event includes its node ID, kind, added/removed frontier IDs, neighbor checks, pending-state count, and expanded-state count.

## Verify

```sh
python3 -m unittest discover -s tests -v
```

Tests compare all four algorithms against an independent reference, validate search traces and frontier counts, demonstrate a longer DFS route, and check A* guidance. They also cover key-dependent backtracking, unreachable exits, the E/door-e ambiguity, input errors, CSV round-trips, 270 generated mazes across sizes and key counts, and 150 comparisons with an independent solver. Request-handler tests use in-memory HTTP connections, so they do not require permission to open a port. CLI tests run the actual program in subprocesses.

Optional JavaScript playback tests and syntax checks, if Node is installed:

```sh
node --test tests/test_playback.cjs
node --check static/app.js
node --check static/playback.js
```

Validation in the development sandbox: Python tests and JavaScript syntax checks were run. The sandbox prevented binding a localhost server and launching the available headless browser, so live browser layout and interaction checks remain unverified there.
