import importlib.util
import os
from pathlib import Path
from unittest import TestCase, mock

spec = importlib.util.spec_from_file_location("pool", Path(__file__).resolve().parents[1] / "scripts" / "cloudshell_cluster.py")
pool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pool)

class PoolTests(TestCase):
    def test_default_loopback(self):
        with mock.patch.dict(os.environ, {"ZWSL_OLLAMA_ENDPOINTS": "http://127.0.0.1:11434"}):
            self.assertEqual(len(pool.endpoints()), 1)

    def test_reject_remote_plain_http(self):
        with mock.patch.dict(os.environ, {"ZWSL_OLLAMA_ENDPOINTS": "http://example.com:11434"}):
            with self.assertRaises(ValueError):
                pool.endpoints()

    def test_reject_credentials_in_url(self):
        with mock.patch.dict(os.environ, {"ZWSL_OLLAMA_ENDPOINTS": "https://user:pass@example.com"}):
            with self.assertRaises(ValueError):
                pool.endpoints()

    def test_health_no_workers(self):
        with mock.patch.object(pool, "healthy", return_value=[]):
            self.assertEqual(pool.main(["health"]), 1)

    def test_bounded_jobs(self):
        with self.assertRaises(SystemExit):
            pool.main(["agents", "--jobs", "100"])
