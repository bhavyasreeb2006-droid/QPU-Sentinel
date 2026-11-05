"""Local browser interface for the notebook's portfolio and QAOA workflow."""

from __future__ import annotations

import argparse
import json
import logging
import math
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import numpy as np

from src.benchmark_workflow import BENCHMARK_TYPES, run_benchmark_case, select_benchmark_specs
from src.experiment_engine import ALGORITHMS, SUPPORTED_ASSET_COUNTS, run_experiment
from src.experiment_store import DEFAULT_DATABASE, ExperimentStore
from src.hardware_suitability import CircuitRequirements, analyze_backends
from src.portfolio_workflow import prepare_portfolio
from src.qaoa_portfolio import run_qaoa_portfolio
from src.research_assistant import (
    AssistantProviderError,
    answer_experiment_question,
    configured_provider,
)


STATIC_ROOT = Path(__file__).resolve().parent / "static"
LOGGER = logging.getLogger(__name__)
_BENCHMARK_JOBS: dict[str, dict[str, object]] = {}
_BENCHMARK_JOBS_LOCK = threading.Lock()
_EXPERIMENT_STORE: ExperimentStore | None = None
_EXPERIMENT_STORE_LOCK = threading.Lock()
_EXPERIMENT_JOB_LOCK = threading.Lock()
_EXPERIMENT_JOB_ACTIVE = False
EXPERIMENT_DATABASE = DEFAULT_DATABASE
EXPERIMENT_JOB_LIMIT = 1
DEFAULT_INPUTS: dict[str, Any] = {
    "assets": ["ASSET_A", "ASSET_B", "ASSET_C", "ASSET_D"],
    "expected_returns": [0.12, 0.10, 0.07, 0.15],
    "covariance": [
        [0.0400, 0.0060, 0.0040, 0.0080],
        [0.0060, 0.0225, 0.0030, 0.0050],
        [0.0040, 0.0030, 0.0100, 0.0020],
        [0.0080, 0.0050, 0.0020, 0.0625],
    ],
    "cardinality": 2,
    "risk_aversion": 2.0,
    "penalty": 1.0,
    "depth": 2,
    "optimizer_shots": 1024,
    "final_shots": 8192,
    "max_iterations": 80,
    "seed": 42,
}


def _positive_integer(payload: dict[str, Any], key: str, maximum: int) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{key} must be a positive integer.")
    if value > maximum:
        raise ValueError(f"{key} cannot exceed {maximum}.")
    return value


def _finite_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number.")
    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite.")
    return float(value)


def _json_records(frame: Any) -> list[dict[str, object]]:
    records = (
        frame.to_dict(orient="records")
        if hasattr(frame, "to_dict")
        else frame
    )
    return [
        {
            key: value.item() if isinstance(value, np.generic) else value
            for key, value in record.items()
        }
        for record in records
    ]


def _experiment_store() -> ExperimentStore:
    global _EXPERIMENT_STORE
    with _EXPERIMENT_STORE_LOCK:
        if _EXPERIMENT_STORE is None:
            _EXPERIMENT_STORE = ExperimentStore(EXPERIMENT_DATABASE)
        return _EXPERIMENT_STORE


def _experiment_specification(payload: dict[str, Any]) -> dict[str, Any]:
    asset_count = _positive_integer(payload, "asset_count", 20)
    if asset_count not in SUPPORTED_ASSET_COUNTS:
        raise ValueError(f"asset_count must be one of {SUPPORTED_ASSET_COUNTS}.")
    cardinality = payload.get("cardinality")
    if (
        isinstance(cardinality, bool)
        or not isinstance(cardinality, int)
        or not 1 <= cardinality <= asset_count
    ):
        raise ValueError("cardinality must be an integer from 1 to asset_count.")
    seed = payload.get("seed", 2026)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")
    algorithms = payload.get("algorithms", ["greedy", "random", "annealing", "qaoa"])
    if not isinstance(algorithms, list) or not algorithms or len(algorithms) > 4:
        raise ValueError("algorithms must be a non-empty list of at most four methods.")
    if any(not isinstance(algorithm, str) for algorithm in algorithms):
        raise ValueError("algorithm names must be strings.")
    if len(set(algorithms)) != len(algorithms) or any(
        algorithm not in ALGORITHMS or algorithm == "exact"
        for algorithm in algorithms
    ):
        raise ValueError(
            f"Choose methods from {tuple(name for name in ALGORITHMS if name != 'exact')}."
        )
    covariance_structure = payload.get("covariance_structure", "mixed")
    if covariance_structure not in {"independent", "correlated", "mixed"}:
        raise ValueError("covariance_structure must be independent, correlated, or mixed.")
    specification: dict[str, Any] = {
        "asset_count": asset_count,
        "cardinality": cardinality,
        "seed": seed,
        "covariance_structure": covariance_structure,
        "risk_aversion": _finite_number(
            {**payload, "risk_aversion": payload.get("risk_aversion", 1.0)},
            "risk_aversion",
        ),
        "penalty": _finite_number(
            {**payload, "penalty": payload.get("penalty", 1.0)}, "penalty"
        ),
        "algorithms": algorithms,
    }
    if specification["risk_aversion"] < 0 or specification["penalty"] <= 0:
        raise ValueError("risk_aversion must be non-negative and penalty must be positive.")
    for key, maximum in (
        ("repetitions", 10),
        ("random_samples", 100_000),
        ("annealing_steps", 100_000),
        ("exact_candidate_limit", 250_000),
        ("qaoa_depth", 8),
        ("qaoa_optimizer_shots", 8192),
        ("qaoa_final_shots", 32768),
        ("qaoa_max_iterations", 100),
    ):
        specification[key] = _positive_integer(
            {**payload, key: payload.get(key, {
                "repetitions": 3,
                "random_samples": 512,
                "annealing_steps": 2000,
                "exact_candidate_limit": 250000,
                "qaoa_depth": 1,
                "qaoa_optimizer_shots": 128,
                "qaoa_final_shots": 512,
                "qaoa_max_iterations": 12,
            }[key])},
            key,
            maximum,
        )
    if "qaoa" in algorithms and specification["qaoa_max_iterations"] < (
        2 * specification["qaoa_depth"] + 2
    ):
        raise ValueError(
            "qaoa_max_iterations must be at least 2 * qaoa_depth + 2 for COBYLA."
        )
    return specification


def _start_experiment_job(specification: dict[str, Any]) -> tuple[int, dict[str, object]]:
    global _EXPERIMENT_JOB_ACTIVE
    with _EXPERIMENT_JOB_LOCK:
        if _EXPERIMENT_JOB_ACTIVE:
            raise RuntimeError("An experiment is already running; retry after it completes.")
        _EXPERIMENT_JOB_ACTIVE = True
    store = _experiment_store()
    try:
        experiment_id = store.create_job(specification)
    except Exception:
        with _EXPERIMENT_JOB_LOCK:
            _EXPERIMENT_JOB_ACTIVE = False
        raise

    def execute() -> None:
        global _EXPERIMENT_JOB_ACTIVE
        try:
            store.update_status(experiment_id, "running")
            result = run_experiment(**specification)
            store.complete(experiment_id, result)
        except Exception as error:
            LOGGER.exception("Experiment %s failed", experiment_id)
            store.fail(experiment_id, str(error))
        finally:
            with _EXPERIMENT_JOB_LOCK:
                _EXPERIMENT_JOB_ACTIVE = False

    threading.Thread(
        target=execute,
        name=f"experiment-{experiment_id[:8]}",
        daemon=True,
    ).start()
    return 202, {
        "experiment_id": experiment_id,
        "status": "queued",
        "message": "Experiment queued for local CPU/Aer execution.",
    }


def _ask_research_assistant(payload: dict[str, Any]) -> tuple[int, dict[str, object]]:
    if payload.get("external_data_consent") is not True:
        raise ValueError(
            "Explicit consent is required before sending experiment evidence to the configured AI provider."
        )
    experiment_id = payload.get("experiment_id")
    if not isinstance(experiment_id, str) or not experiment_id:
        raise ValueError("experiment_id must identify a saved experiment.")
    question = payload.get("question")
    if not isinstance(question, str):
        raise ValueError("question must be a string.")
    provider = configured_provider()
    if provider is None:
        return 503, {
            "error": (
                "AI assistant is not configured. Set QPU_SENTINEL_AI_API_KEY and "
                "optionally QPU_SENTINEL_AI_BASE_URL and QPU_SENTINEL_AI_MODEL."
            )
        }
    record = _experiment_store().get(experiment_id)
    if record is None:
        return 404, {"error": "Experiment not found."}
    if record["status"] != "completed":
        return 409, {"error": "The selected experiment has no completed result yet."}
    return 200, answer_experiment_question(
        record,
        question,
        provider,
        external_data_consent=True,
    )


def run_application_workflow(payload: dict[str, Any]) -> dict[str, object]:
    """Run classical optimization, existing QAOA, and profile analysis."""
    assets = payload.get("assets")
    if not isinstance(assets, list) or not all(isinstance(item, str) for item in assets):
        raise ValueError("assets must be a list of names.")

    cardinality = payload.get("cardinality")
    if isinstance(cardinality, bool) or not isinstance(cardinality, int):
        raise ValueError("cardinality must be an integer.")
    depth = _positive_integer(payload, "depth", 8)
    optimizer_shots = _positive_integer(payload, "optimizer_shots", 8192)
    final_shots = _positive_integer(payload, "final_shots", 32768)
    max_iterations = _positive_integer(payload, "max_iterations", 100)
    seed = payload.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")

    problem = prepare_portfolio(
        assets=assets,
        expected_returns=payload.get("expected_returns", []),
        covariance=payload.get("covariance", []),
        cardinality=cardinality,
        risk_aversion=_finite_number(payload, "risk_aversion"),
        penalty=_finite_number(payload, "penalty"),
    )
    benchmark = problem["benchmark"]
    exact = benchmark[0]
    qaoa_results, metrics = run_qaoa_portfolio(
        linear=problem["linear"],
        quadratic=problem["quadratic"],
        cardinality=cardinality,
        portfolio_objective=problem["objective"],
        qubo_energy=problem["qubo_energy"],
        exact_selection=str(exact["Selection"]),
        exact_objective=float(exact["Objective"]),
        depth=depth,
        optimizer_shots=optimizer_shots,
        final_shots=final_shots,
        max_iterations=max_iterations,
        seed=seed,
        include_circuit=True,
    )

    required_couplings = tuple(
        (left, right)
        for left in range(len(assets))
        for right in range(left + 1, len(assets))
        if problem["quadratic"][left, right] != 0
    )
    hardware = analyze_backends(
        CircuitRequirements(
            qubits=len(assets),
            circuit_depth=int(metrics["circuit_depth"]),
            two_qubit_gates=int(metrics["two_qubit_gates"]),
            required_couplings=required_couplings,
        )
    )
    logical_circuit = metrics["logical_circuit"]
    penalty_sufficiency = problem["penalty_sufficiency"]
    execution_notice = (
        "QAOA results below are measured from a new local Qiskit Aer simulator "
        "run using the inputs shown. Backend candidates are fictional simulated "
        "profiles, not real hardware."
    )
    if not penalty_sufficiency["guaranteed"]:
        execution_notice += (
            " The selected QUBO penalty is not certified sufficient by the "
            "conservative bound; infeasible configurations may have lower QUBO energy."
        )
    return {
        "execution_notice": execution_notice,
        "input_summary": {
            "assets": assets,
            "cardinality": cardinality,
            "risk_aversion": float(problem["risk_aversion"]),
            "penalty_sufficiency": penalty_sufficiency,
            "qubo_configurations_verified": int(problem["verified_configurations"]),
        },
        "classical_results": _json_records(benchmark),
        "qaoa_metrics": metrics,
        "qaoa_results": _json_records(qaoa_results),
        "circuit_explorer": {
            "qubits": [
                {"index": index, "label": asset}
                for index, asset in enumerate(assets)
            ],
            "operations": logical_circuit["operations"],
            "gate_counts": logical_circuit["gate_counts"],
            "logical_depth": logical_circuit["depth"],
            "measurement_count": logical_circuit["measurement_count"],
            "compiled_depth": int(metrics["circuit_depth"]),
            "compiled_two_qubit_gates": int(metrics["two_qubit_gates"]),
            "description": "Uncompiled QAOA circuit with final optimized parameters; compiled metrics are measured separately.",
        },
        "hardware_analysis": hardware,
    }


def _start_benchmark_job(payload: dict[str, Any]) -> tuple[int, dict[str, object]]:
    asset_value = payload.get("asset_count")
    if asset_value in (None, "", "all"):
        asset_count = None
    elif (
        isinstance(asset_value, int)
        and not isinstance(asset_value, bool)
        and asset_value in {3, 4, 5, 6}
    ):
        asset_count = asset_value
    elif isinstance(asset_value, str) and asset_value in {"3", "4", "5", "6"}:
        asset_count = int(asset_value)
    else:
        raise ValueError("asset_count must be all, 3, 4, 5, or 6.")
    problem_value = payload.get("problem_type")
    if problem_value in (None, "", "all"):
        problem_type = None
    elif isinstance(problem_value, str) and problem_value in BENCHMARK_TYPES:
        problem_type = problem_value
    else:
        raise ValueError("problem_type must be all or one of the listed types.")

    specs = select_benchmark_specs(asset_count, problem_type)
    job_id = uuid.uuid4().hex
    job: dict[str, object] = {
        "job_id": job_id,
        "status": "queued",
        "completed": 0,
        "total": len(specs),
        "results": [],
        "error": None,
        "asset_count_filter": asset_count,
        "problem_type_filter": problem_type,
    }
    with _BENCHMARK_JOBS_LOCK:
        _BENCHMARK_JOBS[job_id] = job

    def execute() -> None:
        with _BENCHMARK_JOBS_LOCK:
            job["status"] = "running"
        try:
            for spec in specs:
                row = run_benchmark_case(spec)
                with _BENCHMARK_JOBS_LOCK:
                    results = job["results"]
                    assert isinstance(results, list)
                    results.append(row)
                    job["completed"] = len(results)
            with _BENCHMARK_JOBS_LOCK:
                job["status"] = "completed"
        except Exception as error:
            LOGGER.exception("Benchmark job %s failed", job_id)
            with _BENCHMARK_JOBS_LOCK:
                job["status"] = "failed"
                job["error"] = str(error)

    threading.Thread(target=execute, name=f"benchmark-{job_id[:8]}", daemon=True).start()
    return 202, {
        "job_id": job_id,
        "status": job["status"],
        "total": job["total"],
        "message": "Selected cases will be generated and measured on local Qiskit Aer.",
    }


def _benchmark_job(job_id: str) -> dict[str, object] | None:
    with _BENCHMARK_JOBS_LOCK:
        job = _BENCHMARK_JOBS.get(job_id)
        if job is None:
            return None
        snapshot = dict(job)
        snapshot["results"] = list(job["results"])
        return snapshot


class QPUSentinelHandler(BaseHTTPRequestHandler):
    server_version = "QPU-Sentinel-Local/1.0"

    def _send_json(self, status: int, data: object) -> None:
        body = json.dumps(data, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, filename: str) -> None:
        path = STATIC_ROOT / filename
        if not path.is_file():
            self._send_json(404, {"error": "Interface asset not found."})
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }[path.suffix]
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            self._send_static("index.html")
        elif route == "/app.js":
            self._send_static("app.js")
        elif route == "/styles.css":
            self._send_static("styles.css")
        elif route == "/api/defaults":
            self._send_json(200, DEFAULT_INPUTS)
        elif route == "/api/health":
            self._send_json(200, {"status": "ok", "execution": "local Qiskit Aer"})
        elif route == "/api/benchmark/types":
            self._send_json(200, {
                "planned_configurations": 60,
                "asset_counts": [3, 4, 5, 6],
                "problem_types": [
                    {"id": key, "label": label}
                    for key, label in BENCHMARK_TYPES.items()
                ],
                "note": "Configurations are recipes only; an instance exists as a result only after it is generated and executed.",
            })
        elif route == "/api/benchmark/jobs":
            job_id = parse_qs(urlparse(self.path).query).get("id", [""])[0]
            job = _benchmark_job(job_id)
            if job is None:
                self._send_json(404, {"error": "Benchmark job not found."})
            else:
                self._send_json(200, job)
        elif route == "/api/experiment/options":
            self._send_json(
                200,
                {
                    "asset_counts": list(SUPPORTED_ASSET_COUNTS),
                    "algorithms": [
                        {"id": algorithm, "label": algorithm.title()}
                        for algorithm in ALGORITHMS
                    ],
                    "covariance_structures": ["independent", "correlated", "mixed"],
                    "maximum_repetitions": 10,
                    "execution": "local CPU and Qiskit Aer simulator",
                },
            )
        elif route == "/api/assistant/status":
            provider = configured_provider()
            status = (
                provider.status()
                if provider is not None
                else {
                    "configured": False,
                    "provider": "OpenAI-compatible",
                    "setup": (
                        "Set QPU_SENTINEL_AI_API_KEY; optionally configure "
                        "QPU_SENTINEL_AI_BASE_URL and QPU_SENTINEL_AI_MODEL."
                    ),
                    "requires_experiment_data_consent": True,
                }
            )
            self._send_json(200, status)
        elif route == "/api/experiments":
            query = parse_qs(urlparse(self.path).query)
            try:
                limit = int(query.get("limit", ["50"])[0])
                offset = int(query.get("offset", ["0"])[0])
                self._send_json(200, {"experiments": _experiment_store().list(limit, offset)})
            except (ValueError, TypeError) as error:
                self._send_json(400, {"error": str(error)})
        elif route.startswith("/api/experiments/"):
            experiment_id = route.removeprefix("/api/experiments/")
            if not experiment_id or "/" in experiment_id:
                self._send_json(404, {"error": "Experiment not found."})
            else:
                record = _experiment_store().get(experiment_id)
                if record is None:
                    self._send_json(404, {"error": "Experiment not found."})
                else:
                    self._send_json(200, record)
        else:
            self._send_json(404, {"error": "Route not found."})

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route not in {
            "/api/run",
            "/api/benchmark/run",
            "/api/experiments/run",
            "/api/assistant/ask",
        }:
            self._send_json(404, {"error": "Route not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1_000_000:
                raise ValueError("Request body must be between 1 byte and 1 MB.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Request body must be a JSON object.")
            if route == "/api/benchmark/run":
                status, result = _start_benchmark_job(payload)
            elif route == "/api/experiments/run":
                status, result = _start_experiment_job(
                    _experiment_specification(payload)
                )
            elif route == "/api/assistant/ask":
                status, result = _ask_research_assistant(payload)
            else:
                status = 200
                result = run_application_workflow(payload)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self._send_json(400, {"error": str(error)})
            return
        except AssistantProviderError as error:
            self._send_json(502, {"error": str(error)})
            return
        except RuntimeError as error:
            self._send_json(422, {"error": str(error)})
            return
        self._send_json(status, result)

    def log_message(self, format: str, *args: object) -> None:
        super().log_message(format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local QPU Sentinel interface.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    arguments = parser.parse_args()
    if arguments.host not in {"127.0.0.1", "localhost"}:
        parser.error("The interface binds to localhost only.")
    if not 1 <= arguments.port <= 65535:
        parser.error("Port must be between 1 and 65535.")

    server = ThreadingHTTPServer((arguments.host, arguments.port), QPUSentinelHandler)
    print(f"QPU Sentinel interface: http://{arguments.host}:{arguments.port}")
    print("Local-only server. QAOA execution uses Qiskit Aer; no hardware is contacted.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping QPU Sentinel interface.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
