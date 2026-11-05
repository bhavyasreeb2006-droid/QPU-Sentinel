import json
from http.server import BaseHTTPRequestHandler
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from src import webapp


class ExperimentApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        webapp.EXPERIMENT_DATABASE = Path(self.temporary_directory.name) / "api.sqlite3"
        webapp._EXPERIMENT_STORE = None
        webapp._EXPERIMENT_JOB_ACTIVE = False
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), webapp.QPUSentinelHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        webapp._EXPERIMENT_STORE = None
        webapp._EXPERIMENT_JOB_ACTIVE = False
        self.temporary_directory.cleanup()

    def _json_request(self, path, body=None):
        request = Request(
            self.base_url + path,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={"Content-Type": "application/json"},
            method="POST" if body is not None else "GET",
        )
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            return error.code, json.loads(error.read())

    def test_experiment_api_runs_and_persists_results(self):
        status, created = self._json_request(
            "/api/experiments/run",
            {
                "asset_count": 3,
                "cardinality": 1,
                "seed": 9,
                "algorithms": ["greedy", "random"],
                "repetitions": 2,
                "random_samples": 16,
                "annealing_steps": 30,
            },
        )
        self.assertEqual(status, 202)
        experiment_id = created["experiment_id"]
        record = None
        for _ in range(500):
            _, record = self._json_request(f"/api/experiments/{experiment_id}")
            if record["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)

        self.assertEqual(record["status"], "completed", record)
        self.assertEqual(record["result"]["instance"]["cardinality"], 1)
        self.assertIn("exact", record["result"]["algorithm_configuration"]["algorithms"])
        self.assertEqual(
            {run["algorithm"] for run in record["result"]["runs"]},
            {"exact", "greedy", "random"},
        )
        list_status, listed = self._json_request("/api/experiments?limit=10")
        self.assertEqual(list_status, 200)
        self.assertEqual(listed["experiments"][0]["experiment_id"], experiment_id)

    def test_invalid_experiment_request_returns_client_error(self):
        status, response = self._json_request(
            "/api/experiments/run",
            {"asset_count": 11, "cardinality": 2, "seed": 1},
        )
        self.assertEqual(status, 400)
        self.assertIn("asset_count", response["error"])

    def test_assistant_requires_explicit_data_sharing_consent(self):
        status, response = self._json_request(
            "/api/assistant/ask",
            {
                "experiment_id": "not-used-without-consent",
                "question": "Explain the result.",
                "external_data_consent": False,
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("consent", response["error"])

    def test_assistant_uses_selected_record_with_local_openai_compatible_provider(self):
        received = {}

        class LocalProviderHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                received["authorization"] = self.headers.get("Authorization")
                received["request"] = json.loads(self.rfile.read(length))
                body = json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": "The stored exact result is -0.1 [exact_reference.objective]."
                                }
                            }
                        ]
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                return

        provider_server = ThreadingHTTPServer(("127.0.0.1", 0), LocalProviderHandler)
        provider_thread = threading.Thread(
            target=provider_server.serve_forever, daemon=True
        )
        provider_thread.start()
        try:
            store = webapp._experiment_store()
            specification = {
                "asset_count": 3,
                "cardinality": 1,
                "seed": 2026,
                "algorithms": ["qaoa"],
            }
            experiment_id = store.create_job(specification)
            store.update_status(experiment_id, "running")
            store.complete(
                experiment_id,
                {
                    "dataset_id": "dataset-abc",
                    "instance": {
                        "covariance_structure": "mixed",
                        "risk_aversion": 1.0,
                        "penalty": 1.0,
                        "covariance": [[0.1]],
                    },
                    "exact_reference": {"selection": "100", "objective": -0.1},
                    "penalty_diagnostic": {"certified_sufficient": True},
                    "qubo_validation": {"checked_configurations": 8},
                    "algorithm_configuration": {"algorithms": ["exact", "qaoa"]},
                    "summaries": [{"algorithm": "qaoa", "feasibility_rate": 0.75}],
                    "runs": [{"algorithm": "qaoa", "selection": "100"}],
                },
            )
            with patch.dict(
                os.environ,
                {
                    "QPU_SENTINEL_AI_API_KEY": "test-key-not-for-production",
                    "QPU_SENTINEL_AI_BASE_URL": (
                        f"http://127.0.0.1:{provider_server.server_port}/v1"
                    ),
                    "QPU_SENTINEL_AI_MODEL": "test-model",
                },
            ):
                status, provider_status = self._json_request("/api/assistant/status")
                self.assertEqual(status, 200)
                self.assertTrue(provider_status["configured"])
                self.assertNotIn("api_key", provider_status)
                status, answer = self._json_request(
                    "/api/assistant/ask",
                    {
                        "experiment_id": experiment_id,
                        "question": "Explain the exact result.",
                        "external_data_consent": True,
                    },
                )
            self.assertEqual(status, 200)
            self.assertIn("[exact_reference.objective]", answer["answer"])
            self.assertEqual(
                received["authorization"], "Bearer test-key-not-for-production"
            )
            self.assertIn(experiment_id, received["request"]["messages"][1]["content"])
            self.assertNotIn('"covariance"', received["request"]["messages"][1]["content"])
        finally:
            provider_server.shutdown()
            provider_server.server_close()
            provider_thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
