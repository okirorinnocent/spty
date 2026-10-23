import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(OPENDIAG_TOKEN="test-token", SUPABASE_URL="https://x.supabase.co",
                  SUPABASE_SERVICE_KEY="svc-key")
import app as index  # noqa: E402

GOOD = {"device_id": "PC-01", "records": [
    {"id": 1, "recorded_at": "2026-10-23T10:00:00Z", "cpu_percent": 5.0,
     "memory_percent": 40.0, "health_status": "ok"}]}
AUTH = {"Authorization": "Bearer test-token"}


class Resp:
    def __init__(self, code): self.status_code = code


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = index.app.test_client()

    def test_requires_token(self):
        self.assertEqual(self.client.post("/api/v1/reports", json=GOOD).status_code, 401)
        r = self.client.post("/api/v1/reports", json=GOOD, headers={"Authorization": "Bearer wrong"})
        self.assertEqual(r.status_code, 401)

    def test_rejects_unexpected_fields(self):
        bad = {"device_id": "PC", "records": [{**GOOD["records"][0], "screenshot": "x"}]}
        self.assertEqual(self.client.post("/api/v1/reports", json=bad, headers=AUTH).status_code, 400)

    def test_accepts_and_forwards_to_supabase(self):
        with mock.patch.object(index.requests, "post", return_value=Resp(201)) as p:
            r = self.client.post("/api/v1/reports", json=GOOD, headers=AUTH)
        self.assertEqual(r.status_code, 201)
        url = p.call_args.args[0]
        self.assertIn("/rest/v1/reports", url)
        self.assertEqual(p.call_args.kwargs["json"][0]["device_id"], "PC-01")
        self.assertEqual(p.call_args.kwargs["timeout"], 10)

    def test_storage_failure_returns_502_so_agent_retries(self):
        with mock.patch.object(index.requests, "post", return_value=Resp(500)):
            self.assertEqual(self.client.post("/api/v1/reports", json=GOOD, headers=AUTH).status_code, 502)
        with mock.patch.object(index.requests, "post", side_effect=index.requests.ConnectionError()):
            self.assertEqual(self.client.post("/api/v1/reports", json=GOOD, headers=AUTH).status_code, 502)

    def test_health(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)


if __name__ == "__main__":
    unittest.main()
