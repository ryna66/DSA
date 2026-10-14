"""Exercise the deployable handler so broken imports cannot ship unnoticed."""
import importlib.util
import json
from pathlib import Path
from http.server import ThreadingHTTPServer
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SchedulerAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'api/q4/[[...path]].py'
        spec = importlib.util.spec_from_file_location('scheduler_api_test', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), module.handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}/api/q4/'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def post(self, endpoint, **data):
        request = Request(self.url + endpoint, data=urlencode(data).encode(),
                          headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    def valid_schedule(self, graph, result):
        assignment = result['assignment']
        self.assertEqual(len(assignment), graph['n'])
        self.assertEqual(len(result['events']), graph['n'])
        self.assertEqual(max(assignment, default=0), result['slots'])
        for u, v in graph['edges']:
            self.assertNotEqual(assignment[u - 1], assignment[v - 1])
        for slot in set(assignment):
            self.assertLessEqual(assignment.count(slot), graph['halls'])

    def test_default_example_and_exact_improvement(self):
        result = self.post('solve', n=7, halls=3, budget=2000,
                           edges='1,3\n1,4\n1,6\n2,4\n2,5\n2,7\n3,4\n5,6\n5,7\n6,7')
        self.assertEqual(result['greedy']['slots'], 4)
        self.assertEqual(result['exact']['slots'], 3)
        self.assertTrue(result['exact']['optimal'])
        for key in ['greedy', 'exact']:
            self.valid_schedule(result['graph'], result[key])

    def test_empty_and_capacity_only(self):
        for n, slots in [(0, 0), (1, 1), (10, 4)]:
            result = self.post('solve', n=n, halls=3, edges='', budget=100)
            self.assertEqual(result['exact']['slots'], slots)
            self.valid_schedule(result['graph'], result['exact'])

    def test_generate_and_benchmark_response_contract(self):
        graph = self.post('generate', n=8, halls=3, density=.3, seed=42)
        self.assertEqual(graph['n'], 8)
        result = self.post('benchmark', n=8, halls=3, density=.3, seed=42, budget=100)
        for key in ['greedy', 'exact']:
            self.valid_schedule(graph, result[key])
            self.assertIn('timeMs', result[key])
            self.assertIn('csv', result[key])

    def test_invalid_conflict_and_overlong_budget_return_json(self):
        for endpoint, data in [('solve', dict(n=2,halls=1,edges='1,1')),
                               ('solve', dict(n=2,halls=1,edges='',budget=60000)),
                               ('benchmark', dict(n=2,halls=1,budget=60000))]:
            with self.assertRaises(HTTPError) as caught:
                self.post(endpoint, **data)
            self.assertEqual(caught.exception.code, 400)
            self.assertIn('error', json.load(caught.exception))


if __name__ == '__main__':
    unittest.main()
