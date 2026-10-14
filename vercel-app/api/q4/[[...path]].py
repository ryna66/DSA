"""Catch-all serverless function for Question 4 (Exam Scheduler) API."""
from http.server import BaseHTTPRequestHandler
import json, sys, os
from urllib.parse import parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from scheduler import graph, random_graph, compare, form_graph, graph_map, comparison_map, result_map


def respond(handler, status, data):
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def int_field(params, key, fallback):
    return int(params.get(key, str(fallback)))


def long_field(params, key, fallback):
    return int(params.get(key, str(fallback)))


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if length > 100_000:
                raise ValueError("Request must be smaller than 100 KB.")
            raw = self.rfile.read(length).decode()
            params = {k: v[0] for k, v in parse_qs(raw).items()}

            path = self.path.split('?')[0].rstrip('/')
            if path.endswith('/solve'):
                g = form_graph(params)
                budget = long_field(params, 'budget', 2000)
                c = compare(g, budget)
                respond(self, 200, comparison_map(c))
            elif path.endswith('/generate'):
                n = int_field(params, 'n', 10)
                halls = int_field(params, 'halls', 3)
                if n > 60 or halls > 20:
                    raise ValueError("The visualizer supports at most 60 courses and 20 halls.")
                density = float(params.get('density', '0.3'))
                seed = long_field(params, 'seed', 42)
                g = random_graph(n, halls, density, seed)
                respond(self, 200, graph_map(g))
            elif path.endswith('/benchmark'):
                n = int_field(params, 'n', 10)
                halls = int_field(params, 'halls', 3)
                if not 1 <= n <= 60 or halls > 20:
                    raise ValueError("Benchmark supports 1–60 courses and up to 20 halls.")
                density = float(params.get('density', '0.3'))
                seed = long_field(params, 'seed', 42)
                budget = long_field(params, 'budget', 1000)
                g = random_graph(n, halls, density, seed)
                c = compare(g, budget)
                respond(self, 200, {"n": n, "edges": len(g['edges']), "greedy": result_map(c['greedy']), "exact": result_map(c['exact'])})
            else:
                respond(self, 404, {"error": "Unknown endpoint."})
        except (ValueError, TypeError) as e:
            respond(self, 400, {"error": str(e)})
