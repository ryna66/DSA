"""Run `python3 app.py` for the UI; see --help for CLI commands."""

import argparse
import csv
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from maze import ALGORITHMS, export_csv, generate, parse_grid, solve

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "static"), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def respond(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlsplit(self.path).path == "/api/examples":
            examples = []
            for title, filename, types in (("The first lock", "first_lock.csv", 1),
                                           ("Three-key journey", "three_keys.csv", 3),
                                           ("A necessary detour", "backtrack.csv", 1),
                                           ("All six keys", "six_keys.csv", 6),
                                           ("No way through", "unsolvable.csv", 1),
                                           ("Branches & dead ends", "branches.csv", 1)):
                grid = parse_grid((ROOT / "examples" / filename).read_text())
                examples.append({"title": title, "types": types, "grid": grid})
            self.respond(200, examples)
        elif urlsplit(self.path).path.startswith("/api/"):
            self.respond(404, {"error": "Unknown API endpoint."})
        else:
            super().do_GET()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 100_000:
                raise ValueError("Request must contain JSON smaller than 100 KB.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Request must be a JSON object.")
            endpoint = urlsplit(self.path).path
            if endpoint == "/api/solve":
                grid = parse_grid(data["text"]) if "text" in data else data.get("grid")
                self.respond(200, solve(grid, data.get("types"), data.get("algorithm", "bfs")))
            elif endpoint == "/api/generate":
                seed = data.get("seed")
                if seed is not None and type(seed) is not int:
                    raise ValueError("Seed must be an integer.")
                grid = generate(data.get("size"), data.get("types"), seed)
                self.respond(200, {"grid": grid, "types": data["types"], "csv": export_csv(grid)})
            else:
                self.respond(404, {"error": "Unknown API endpoint."})
        except (ValueError, TypeError, csv.Error) as error:
            self.respond(400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description="KeyPath: shortest paths with keys and doors.")
    commands = parser.add_subparsers(dest="command")
    server = commands.add_parser("serve", help="Start the local visualizer (default command).")
    server.add_argument("--port", type=int, default=8000)
    solver = commands.add_parser("solve", help="Read T from stdin unless --types is supplied.")
    solver.add_argument("--csv", type=Path, help="Input CSV; otherwise read the grid from stdin.")
    solver.add_argument("--types", type=int)
    solver.add_argument("--algorithm", choices=sorted(ALGORITHMS), default="bfs",
                        help="DFS finds a route; the other algorithms guarantee a shortest route.")
    solver.add_argument("--output", type=Path, default=Path("shortest_path.csv"))
    generator = commands.add_parser("generate", help="Write a solvable random maze CSV.")
    generator.add_argument("--size", type=int, default=11)
    generator.add_argument("--types", type=int, default=3)
    generator.add_argument("--seed", type=int)
    generator.add_argument("--output", type=Path, default=Path("maze.csv"))
    args = parser.parse_args()
    try:
        if args.command == "solve":
            types = args.types if args.types is not None else int(sys.stdin.readline().strip())
            source = args.csv.read_text(encoding="utf-8-sig") if args.csv else sys.stdin.read()
            result = solve(parse_grid(source), types, args.algorithm)
            args.output.write_text(result["csv"], encoding="utf-8")
            print(result["length"])
        elif args.command == "generate":
            args.output.write_text(export_csv(generate(args.size, args.types, args.seed)), encoding="utf-8")
            print(args.output)
        else:
            port = getattr(args, "port", 8000)
            httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            print(f"KeyPath is ready at http://127.0.0.1:{port}", flush=True)
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                httpd.server_close()
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
