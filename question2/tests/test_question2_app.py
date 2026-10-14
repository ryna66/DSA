import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("question2_server", ROOT / "app.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class QuietHandler(server.Handler):
    def log_message(self, *args):
        pass


class Connection:
    def __init__(self, data):
        self.input = io.BytesIO(data)
        self.output = bytearray()

    def makefile(self, *args, **kwargs):
        return self.input

    def sendall(self, data):
        self.output.extend(data)


def request(method, path, payload=None, raw=None):
    body = raw if raw is not None else json.dumps(payload).encode() if payload is not None else b""
    header = f"{method} {path} HTTP/1.0\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n".encode()
    connection = Connection(header + body)
    QuietHandler(connection, ("127.0.0.1", 0), None)
    headers, body = bytes(connection.output).split(b"\r\n\r\n", 1)
    return int(headers.split()[1]), body


class AppTests(unittest.TestCase):
    def test_static_assets(self):
        for path, marker in (("/", b"Closest Pair"), ("/app.js", b"runBenchmark"), ("/styles.css", b"strip-region")):
            status, body = request("GET", path)
            self.assertEqual(status, 200)
            self.assertIn(marker, body)

    def test_generate_solve_and_benchmark(self):
        status, body = request("POST", "/api/generate", {"n": 16, "seed": 42})
        self.assertEqual(status, 200)
        status, body = request("POST", "/api/solve", json.loads(body))
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["agree"])
        self.assertTrue(json.loads(body)["events"])
        status, body = request("POST", "/api/benchmark", {"sizes": [10, 30], "repeats": 1})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["agree"])

    def test_bad_input_returns_400(self):
        for endpoint, value in (("generate", {"n": -1}), ("generate", {"n": 2001}),
                                ("solve", {"points": [[0, "bad"]]}), ("solve", {}),
                                ("benchmark", {"sizes": [0]}), ("solve", [])):
            status, body = request("POST", f"/api/{endpoint}", value)
            self.assertEqual(status, 400)
            self.assertIn("error", json.loads(body))
        for raw in (b"{", b"\xff"):
            self.assertEqual(request("POST", "/api/solve", raw=raw)[0], 400)

    def test_cli_three_lines_and_corner_cases(self):
        for n in (0, 1, 2, 20):
            completed = subprocess.run([sys.executable, str(ROOT / "app.py"), "solve", "--seed", "42"],
                                       input=f"{n}\n", text=True, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            lines = completed.stdout.splitlines()
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[0].startswith("Brute-Force:"))
            self.assertTrue(lines[1].startswith("Divide-and-Conquer:"))
            self.assertIn("ms", lines[2])
            if n >= 2:
                self.assertRegex(lines[0], r"Brute-Force: \d+\.\d{6} ")

    def test_cli_creates_csv_and_svg(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory) / "out.csv"
            svg = Path(directory) / "out.svg"
            completed = subprocess.run([sys.executable, str(ROOT / "app.py"), "benchmark", "--sizes", "5,10", "--repeats", "1", "--output", str(csv), "--plot", str(svg)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("distances_agree", csv.read_text())
            self.assertIn("<svg", svg.read_text())
            import xml.etree.ElementTree as ET
            ET.parse(svg)


if __name__ == "__main__":
    unittest.main()
