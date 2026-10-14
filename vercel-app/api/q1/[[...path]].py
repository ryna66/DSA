"""Catch-all serverless function for Question 1 (Maze Solver) API."""
from http.server import BaseHTTPRequestHandler
import json, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from maze import parse_grid, solve, generate, export_csv

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'lib', 'q1_examples')

EXAMPLE_LIST = [
    ("The first lock", "first_lock.csv", 1),
    ("Three-key journey", "three_keys.csv", 3),
    ("A necessary detour", "backtrack.csv", 1),
    ("All six keys", "six_keys.csv", 6),
    ("No way through", "unsolvable.csv", 1),
    ("Branches & dead ends", "branches.csv", 1),
]


def respond(handler, status, data):
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0].rstrip('/')
        if path.endswith('/examples'):
            try:
                examples = []
                for title, filename, types in EXAMPLE_LIST:
                    with open(os.path.join(EXAMPLES_DIR, filename), 'r') as f:
                        grid = parse_grid(f.read())
                    examples.append({"title": title, "types": types, "grid": grid})
                respond(self, 200, examples)
            except Exception as e:
                respond(self, 500, {"error": str(e)})
        else:
            respond(self, 404, {"error": "Not found."})

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 100_000:
                raise ValueError("Request must be smaller than 100 KB.")
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Request must be a JSON object.")

            path = self.path.split('?')[0].rstrip('/')
            if path.endswith('/solve'):
                grid = parse_grid(data['text']) if 'text' in data else data.get('grid')
                respond(self, 200, solve(grid, data.get('types'), data.get('algorithm', 'bfs')))
            elif path.endswith('/generate'):
                seed = data.get('seed')
                if seed is not None and type(seed) is not int:
                    raise ValueError("Seed must be an integer.")
                grid = generate(data.get('size'), data.get('types'), seed)
                respond(self, 200, {"grid": grid, "types": data["types"], "csv": export_csv(grid)})
            else:
                respond(self, 404, {"error": "Unknown endpoint."})
        except (ValueError, TypeError) as e:
            respond(self, 400, {"error": str(e)})
