import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app import Handler, ROOT


class MemoryConnection:
    """Exercise the real HTTP parser/handler without binding a network socket."""
    def __init__(self, request):
        self.input = io.BytesIO(request)
        self.output = bytearray()

    def makefile(self, *args, **kwargs):
        return self.input

    def sendall(self, data):
        self.output.extend(data)


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


def request(method, path, data=None, raw=None):
    body = raw if raw is not None else json.dumps(data).encode() if data is not None else b""
    headers = (f"{method} {path} HTTP/1.0\r\nHost: localhost\r\n"
               f"Content-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n").encode()
    connection = MemoryConnection(headers + body)
    QuietHandler(connection, ("127.0.0.1", 1), None)
    head, response = bytes(connection.output).split(b"\r\n\r\n", 1)
    status = int(head.split()[1])
    return status, response


class AppTests(unittest.TestCase):
    def test_serves_application_assets(self):
        for path, snippet in (("/", b"KeyPath"), ("/app.js", b"solveMaze"), ("/styles.css", b".grid")):
            status, body = request("GET", path)
            self.assertEqual(status, 200)
            self.assertIn(snippet, body)

    def test_examples_and_solve(self):
        status, body = request("GET", "/api/examples")
        self.assertEqual(status, 200)
        examples = json.loads(body)
        self.assertEqual(len(examples), 6)
        for index, example in enumerate(examples):
            status, body = request("POST", "/api/solve", example)
            self.assertEqual(status, 200)
            result = json.loads(body)
            if index == 4:
                self.assertEqual(result["length"], -1)
            else:
                self.assertGreater(result["length"], 0)

    def test_generate_then_solve_api(self):
        status, body = request("POST", "/api/generate", {"size": 7, "types": 6, "seed": 91})
        self.assertEqual(status, 200)
        generated = json.loads(body)
        status, body = request("POST", "/api/solve", {"text": generated["csv"], "types": 6})
        self.assertEqual(status, 200)
        self.assertGreater(json.loads(body)["length"], 0)

    def test_bad_requests_return_errors(self):
        for raw in (b"{", b"[]", b"null", b"\xff", b"{}"):
            status, body = request("POST", "/api/solve", raw=raw)
            self.assertEqual(status, 400)
            self.assertIn("error", json.loads(body))
        status, body = request("POST", "/api/generate", {"size": 8, "types": 2})
        self.assertEqual(status, 400)
        status, body = request("POST", "/api/generate", {"size": 7, "types": 2, "seed": []})
        self.assertEqual(status, 400)
        for method in ("GET", "POST"):
            status, _ = request(method, "/api/missing", {})
            self.assertEqual(status, 404)

    def test_cli_stdin_csv_and_export(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "path.csv"
            result = subprocess.run([sys.executable, str(ROOT / "app.py"), "solve", "--csv",
                                     str(ROOT / "examples/backtrack.csv"), "--output", str(output)],
                                    input="1\n", capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "8\n")
            self.assertIn("x(A)", output.read_text())
            result = subprocess.run([sys.executable, str(ROOT / "app.py"), "solve", "--output", str(output)],
                                    input="1\nSE\naA\n", capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "1\n")


if __name__ == "__main__":
    unittest.main()
