"""Question 2: run the visualizer, solve from stdin, or benchmark both algorithms."""
import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from closest_pair import DISTRIBUTIONS, benchmark, compare, generate_points
from reports import benchmark_csv, benchmark_svg

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "static"), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def respond(self, status, value):
        body = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 250_000:
                raise ValueError("Send a JSON request smaller than 250 KB.")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Request must be a JSON object.")
            endpoint = urlsplit(self.path).path
            if endpoint == "/api/generate":
                n = data.get("n")
                if type(n) is not int or not 0 <= n <= 2000:
                    raise ValueError("Use an integer N from 0 to 2000 in the visualizer.")
                points = generate_points(n, data.get("seed"), data.get("distribution", "uniform"))
                self.respond(200, {"points": points})
            elif endpoint == "/api/solve":
                points = data.get("points")
                if not isinstance(points, list) or len(points) > 2000:
                    raise ValueError("Provide a list of at most 2000 points.")
                self.respond(200, compare(points))
            elif endpoint == "/api/benchmark":
                result = benchmark(data.get("sizes"), data.get("repeats", 3),
                                   data.get("seed", 42), data.get("distribution", "uniform"))
                self.respond(200, result)
            else:
                self.respond(404, {"error": "Unknown API endpoint."})
        except (ValueError, TypeError, OverflowError) as error:
            self.respond(400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description="Question 2 · closest pair of points")
    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="Start the visualizer (default).")
    serve.add_argument("--port", type=int, default=8001)
    solver = commands.add_parser("solve", help="Read integer N from stdin and generate N points.")
    solver.add_argument("--seed", type=int, default=42)
    solver.add_argument("--distribution", choices=sorted(DISTRIBUTIONS), default="uniform")
    perf = commands.add_parser("benchmark", help="Measure increasing sizes and write CSV + SVG.")
    perf.add_argument("--sizes", default="50,100,200,400,800,1600")
    perf.add_argument("--repeats", type=int, default=3)
    perf.add_argument("--seed", type=int, default=42)
    perf.add_argument("--distribution", choices=sorted(DISTRIBUTIONS), default="uniform")
    perf.add_argument("--output", type=Path, default=Path("performance.csv"))
    perf.add_argument("--plot", type=Path, default=Path("performance.svg"))
    args = parser.parse_args()
    try:
        if args.command == "solve":
            n = int(sys.stdin.readline().strip())
            result = compare(generate_points(n, args.seed, args.distribution), animate=False)
            for key, label in (("brute", "Brute-Force"), ("divide", "Divide-and-Conquer")):
                entry = result[key]
                if entry["pair"] is None:
                    print(f"{label}: undefined — no pair (N < 2)")
                else:
                    a, b = (result["points"][i] for i in entry["pair"])
                    print(f'{label}: {entry["distance"]:.6f} ({a[0]:.6f}, {a[1]:.6f}) ({b[0]:.6f}, {b[1]:.6f})')
            print(f'Time: Brute-Force {result["brute"]["time_ms"]:.6f} ms; Divide-and-Conquer {result["divide"]["time_ms"]:.6f} ms')
            if not result["agree"]:
                parser.exit(1, "Error: algorithms disagree.\n")
        elif args.command == "benchmark":
            data = benchmark([int(n.strip()) for n in args.sizes.split(",")], args.repeats, args.seed, args.distribution)
            args.output.write_text(benchmark_csv(data), encoding="utf-8")
            args.plot.write_text(benchmark_svg(data), encoding="utf-8")
            print(benchmark_csv(data), end="")
            print(f"Saved {args.output} and {args.plot}")
            if not data["agree"]:
                parser.exit(1, "Error: algorithms disagree.\n")
        else:
            port = getattr(args, "port", 8001)
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            print(f"Closest Pair Lab: http://127.0.0.1:{port}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
    except (ValueError, OSError, OverflowError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
