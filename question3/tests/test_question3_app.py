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
spec = importlib.util.spec_from_file_location('question3_server', ROOT / 'app.py')
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


def request(method, path, data=None, raw=None):
    body = raw if raw is not None else json.dumps(data).encode() if data is not None else b''
    header = f'{method} {path} HTTP/1.0\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n'.encode()
    connection = Connection(header + body)
    QuietHandler(connection, ('127.0.0.1', 0), None)
    headers, body = bytes(connection.output).split(b'\r\n\r\n', 1)
    return int(headers.split()[1]), body


class ServerTests(unittest.TestCase):
    def test_static_and_examples(self):
        for path, word in (('/', b'FlightPath'), ('/app.js', b'solveGraph'), ('/styles.css', b'flight-edge')):
            status, body = request('GET', path)
            self.assertEqual(status, 200)
            self.assertIn(word, body)
        status, body = request('GET', '/api/examples')
        self.assertEqual(status, 200)
        examples = json.loads(body)
        self.assertEqual(len(examples), 5)
        for i, example in enumerate(examples):
            status, body = request('POST', '/api/solve', example)
            self.assertEqual(status, 200)
            if i == 3:
                self.assertEqual(json.loads(body)['cost'], -1)
            else:
                self.assertGreaterEqual(json.loads(body)['cost'], 0)

    def test_csv_import_and_generate(self):
        status, body = request('POST', '/api/import', {'csv': '#cities,5\nu,v,price\n1,2,3'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['n'], 5)
        status, body = request('POST', '/api/generate', {'n': 8, 'm': 12, 'k': 0, 'coupons': 0, 'seed': 4})
        self.assertEqual(status, 200)
        data = json.loads(body)
        data.update(k=0, coupons=0)
        status, body = request('POST', '/api/solve', data)
        self.assertEqual(status, 200)
        self.assertGreaterEqual(json.loads(body)['cost'], 0)

    def test_bad_requests(self):
        for path, data in (('solve', {}), ('solve', {'n': 2, 'edges': [[1, 2, -3]], 'k': 1, 'coupons': 1}),
                           ('generate', {'n': 21, 'm': 1}), ('import', {'csv': 'u,v,price\n1,no,3'}),
                           ('solve', {'n': 2, 'edges': [[1, 2, 1000000001]], 'k': 1, 'coupons': 1})):
            status, body = request('POST', f'/api/{path}', data)
            self.assertEqual(status, 400)
            self.assertIn('error', json.loads(body))
        for raw in (b'[]', b'{', b'\xff'):
            self.assertEqual(request('POST', '/api/solve', raw=raw)[0], 400)

    def test_cli_standard_and_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'path.csv'
            result = subprocess.run([sys.executable, str(ROOT / 'app.py'), 'solve', '--output', str(output)],
                                    input=(ROOT / 'examples/standard_input.txt').read_text(), text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '150\n')
            self.assertIn(',x,yes,', output.read_text())
            result = subprocess.run([sys.executable, str(ROOT / 'app.py'), 'solve', '--csv', str(output), '--output', str(Path(directory) / 'again.csv')],
                                    input='1 1\n', text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '150\n')

    def test_cli_generator_and_unreachable(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / 'flights.csv'
            process = subprocess.run([sys.executable, str(ROOT / 'app.py'), 'generate', '--cities', '4', '--flights', '5', '--stops', '0', '--output', str(generated)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertTrue(generated.exists())
            process = subprocess.run([sys.executable, str(ROOT / 'app.py'), 'solve', '--output', str(Path(directory)/'path.csv')], input='3 1\n0 2\n1 2 50\n', capture_output=True, text=True)
            self.assertEqual(process.stdout, '-1\n')
            self.assertEqual(process.returncode, 0)


if __name__ == '__main__':
    unittest.main()
