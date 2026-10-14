"""Catch-all serverless function for Question 3 (Flight Path) API."""
from http.server import BaseHTTPRequestHandler
import json, csv, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from flights import parse_csv, parse_flights, solve, generate

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'lib', 'q3_examples')

EXAMPLE_LIST = [
    ("A coupon changes everything", "coupon_choice.csv", 2, 1),
    ("Direct flights only", "coupon_choice.csv", 0, 1),
    ("Two coupons, three flights", "two_coupons.csv", 2, 2),
    ("The stop limit blocks the route", "unreachable.csv", 0, 1),
    ("Already at the destination", "single_city.csv", 0, 2),
]


def respond(handler, status, data):
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def check_limits(n, edges):
    if type(n) is not int or not 1 <= n <= 20 or not isinstance(edges, list) or len(edges) > 150:
        raise ValueError("The visualizer supports 1–20 cities and at most 150 flights.")
    for edge in edges:
        if isinstance(edge, (list, tuple)) and len(edge) == 3 and isinstance(edge[2], int) and edge[2] > 1_000_000_000:
            raise ValueError("Ticket prices must not exceed 1,000,000,000.")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0].rstrip('/')
        if path.endswith('/examples'):
            try:
                examples = []
                for title, filename, k, c in EXAMPLE_LIST:
                    with open(os.path.join(EXAMPLES_DIR, filename), 'r') as f:
                        n, edges = parse_csv(f.read())
                    examples.append({"title": title, "n": n, "edges": edges, "k": k, "coupons": c})
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
            if path.endswith('/import_csv'):
                n, edges = parse_csv(data.get('csv'), data.get('cities'))
                check_limits(n, edges)
                respond(self, 200, {"n": n, "edges": edges})
            elif path.endswith('/solve'):
                n = data.get('n')
                edges = parse_flights(data['text']) if 'text' in data else data.get('edges')
                check_limits(n, edges)
                respond(self, 200, solve(n, edges, data.get('k'), data.get('coupons')))
            elif path.endswith('/generate'):
                n, m = data.get('n'), data.get('m')
                if type(n) is not int or not 1 <= n <= 20 or type(m) is not int or not 0 <= m <= 150:
                    raise ValueError("Use 1–20 cities and 0–150 flights.")
                edges = generate(n, m, data.get('k'), data.get('coupons'), data.get('seed'))
                respond(self, 200, {"n": n, "edges": edges})
            else:
                respond(self, 404, {"error": "Unknown endpoint."})
        except (ValueError, TypeError, csv.Error, OverflowError) as e:
            respond(self, 400, {"error": str(e)})
