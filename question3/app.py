"""Question 3: local flight planner and standard-input command-line solver."""
import argparse
import csv
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from flights import export_csv, generate, parse_csv, parse_flights, parse_standard, solve

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "static"), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def respond(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlsplit(self.path).path == "/api/examples":
            examples = []
            for title, filename, k, c in (("A coupon changes everything", "coupon_choice.csv", 2, 1),
                                        ("Direct flights only", "coupon_choice.csv", 0, 1),
                                        ("Two coupons, three flights", "two_coupons.csv", 2, 2),
                                        ("The stop limit blocks the route", "unreachable.csv", 0, 1),
                                        ("Already at the destination", "single_city.csv", 0, 2)):
                n, edges = parse_csv((ROOT / "examples" / filename).read_text())
                examples.append({"title": title, "n": n, "edges": edges, "k": k, "coupons": c})
            self.respond(200, examples)
        else:
            super().do_GET()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 100_000:
                raise ValueError("Send a JSON request smaller than 100 KB.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Request must be a JSON object.")
            endpoint = urlsplit(self.path).path
            if endpoint == "/api/import":
                n, edges = parse_csv(data.get("csv"), data.get("cities"))
                self.check_limits(n, edges)
                self.respond(200, {"n": n, "edges": edges})
            elif endpoint == "/api/solve":
                n = data.get("n")
                edges = parse_flights(data["text"]) if "text" in data else data.get("edges")
                self.check_limits(n, edges)
                self.respond(200, solve(n, edges, data.get("k"), data.get("coupons")))
            elif endpoint == "/api/generate":
                n, m = data.get("n"), data.get("m")
                if type(n) is not int or not 1 <= n <= 20 or type(m) is not int or not 0 <= m <= 150:
                    raise ValueError("Use 1–20 cities and 0–150 flights in the visualizer.")
                edges = generate(n, m, data.get("k"), data.get("coupons"), data.get("seed"))
                self.respond(200, {"n": n, "edges": edges})
            else:
                self.respond(404, {"error": "Unknown API endpoint."})
        except (ValueError, TypeError, csv.Error, OverflowError) as error:
            self.respond(400, {"error": str(error)})

    @staticmethod
    def check_limits(n, edges):
        if type(n) is not int or not 1 <= n <= 20 or not isinstance(edges, list) or len(edges) > 150:
            raise ValueError("The visualizer supports 1–20 cities and at most 150 flights.")
        for edge in edges:
            if isinstance(edge, (list, tuple)) and len(edge) == 3 and isinstance(edge[2], int) and edge[2] > 1_000_000_000:
                raise ValueError("Visualized ticket prices must not exceed 1,000,000,000.")


def main():
    parser = argparse.ArgumentParser(description="Cheapest flights with stop limits and half-price coupons.")
    commands = parser.add_subparsers(dest="command")
    serve = commands.add_parser("serve", help="Start the visualizer (default command).")
    serve.add_argument("--port", type=int, default=8002)
    solver = commands.add_parser("solve", help="Read standard input, or K C plus --csv.")
    solver.add_argument("--csv", type=Path)
    solver.add_argument("--cities", type=int, help="N for CSVs with isolated destination cities.")
    solver.add_argument("--output", type=Path, default=Path("flight_path.csv"))
    generator = commands.add_parser("generate", help="Generate a guaranteed solvable graph CSV.")
    generator.add_argument("--cities", type=int, default=8)
    generator.add_argument("--flights", type=int, default=14)
    generator.add_argument("--stops", type=int, default=3)
    generator.add_argument("--coupons", type=int, default=2)
    generator.add_argument("--seed", type=int, default=42)
    generator.add_argument("--output", type=Path, default=Path("flights.csv"))
    args = parser.parse_args()
    try:
        if args.command == "solve":
            if args.csv:
                values = sys.stdin.read().split()
                if len(values) != 2:
                    raise ValueError("With --csv, standard input must contain exactly K C.")
                k, c = map(int, values)
                n, edges = parse_csv(args.csv.read_text(encoding="utf-8-sig"), args.cities)
            else:
                if args.cities is not None:
                    raise ValueError("--cities applies only to CSV input.")
                n, edges, k, c = parse_standard(sys.stdin.read())
            result = solve(n, edges, k, c)
            args.output.write_text(result["csv"], encoding="utf-8")
            print(result["cost"])
        elif args.command == "generate":
            edges = generate(args.cities, args.flights, args.stops, args.coupons, args.seed)
            args.output.write_text(export_csv(args.cities, edges), encoding="utf-8")
            print(args.output)
        else:
            port = getattr(args, "port", 8002)
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            print(f"FlightPath: http://127.0.0.1:{port}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
    except (ValueError, OSError, csv.Error, OverflowError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
