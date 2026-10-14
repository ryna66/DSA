"""Catch-all serverless function for Question 2 (Closest Pair) API."""
from http.server import BaseHTTPRequestHandler
import json, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'lib'))
from closest_pair import generate_points, compare, benchmark


def respond(handler, status, data):
    body = json.dumps(data, allow_nan=False).encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 250_000:
                raise ValueError("Request must be smaller than 250 KB.")
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError("Request must be a JSON object.")

            path = self.path.split('?')[0].rstrip('/')
            if path.endswith('/generate'):
                n = data.get('n')
                if type(n) is not int or not 0 <= n <= 2000:
                    raise ValueError("Use an integer N from 0 to 2000.")
                points = generate_points(n, data.get('seed'), data.get('distribution', 'uniform'))
                respond(self, 200, {"points": points})
            elif path.endswith('/solve'):
                points = data.get('points')
                if not isinstance(points, list) or len(points) > 2000:
                    raise ValueError("Provide a list of at most 2000 points.")
                respond(self, 200, compare(points))
            elif path.endswith('/benchmark'):
                result = benchmark(data.get('sizes'), data.get('repeats', 3),
                                   data.get('seed', 42), data.get('distribution', 'uniform'))
                respond(self, 200, result)
            else:
                respond(self, 404, {"error": "Unknown endpoint."})
        except (ValueError, TypeError, OverflowError) as e:
            respond(self, 400, {"error": str(e)})
