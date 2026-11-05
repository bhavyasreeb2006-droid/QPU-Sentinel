"""On-demand, reproducible benchmark cases executed with local Qiskit Aer."""

from __future__ import annotations

from collections.abc import Iterator
from time import perf_counter
from typing import Any

import numpy as np

from src.portfolio_workflow import prepare_portfolio
from src.qaoa_portfolio import run_qaoa_portfolio

BENCHMARK_TYPES = {
    "independent": "Independent assets",
    "correlated": "Positively correlated assets",
    "mixed": "Mixed-factor covariance",
}
ASSET_COUNTS = (3, 4, 5, 6)
REPLICATES = 5


def benchmark_specs() -> Iterator[dict[str, Any]]:
    """Yield the 60 planned configurations without generating their data."""
    for asset_count in ASSET_COUNTS:
        for problem_type in BENCHMARK_TYPES:
            for replicate in range(REPLICATES):
                yield {
                    "case_id": f"N{asset_count}-{problem_type[:3].upper()}-{replicate + 1:02d}",
                    "asset_count": asset_count,
                    "problem_type": problem_type,
                    "replicate": replicate + 1,
                    "seed": 202600 + asset_count * 100 + list(BENCHMARK_TYPES).index(problem_type) * 10 + replicate,
                }


def select_benchmark_specs(
    asset_count: int | None = None,
    problem_type: str | None = None,
) -> list[dict[str, Any]]:
    if asset_count is not None and asset_count not in ASSET_COUNTS:
        raise ValueError(f"asset_count must be one of {ASSET_COUNTS}.")
    if problem_type is not None and problem_type not in BENCHMARK_TYPES:
        raise ValueError(f"problem_type must be one of {tuple(BENCHMARK_TYPES)}.")
    return [
        spec for spec in benchmark_specs()
        if (asset_count is None or spec["asset_count"] == asset_count)
        and (problem_type is None or spec["problem_type"] == problem_type)
    ]


def generate_benchmark_case(spec: dict[str, Any]) -> dict[str, Any]:
    """Generate one deterministic PSD covariance instance from its recipe."""
    count = int(spec["asset_count"])
    rng = np.random.default_rng(int(spec["seed"]))
    expected_returns = rng.uniform(0.04, 0.18, count)
    if spec["problem_type"] == "independent":
        covariance = np.diag(rng.uniform(0.008, 0.045, count))
    elif spec["problem_type"] == "correlated":
        common_factor = rng.uniform(0.035, 0.11, (count, 1))
        covariance = common_factor @ common_factor.T + np.diag(
            rng.uniform(0.006, 0.02, count)
        )
    else:
        factor_loadings = rng.normal(0, 0.055, (count, 2))
        covariance = factor_loadings @ factor_loadings.T + np.diag(
            rng.uniform(0.007, 0.025, count)
        )
    return {
        **spec,
        "assets": [f"A{index + 1}" for index in range(count)],
        "expected_returns": expected_returns.tolist(),
        "covariance": covariance.tolist(),
        "cardinality": max(1, count // 2),
        "risk_aversion": float(rng.choice([0.5, 1.0, 2.0])),
    }


def run_benchmark_case(spec: dict[str, Any]) -> dict[str, Any]:
    """Generate and execute one benchmark case; return measured Aer results."""
    started = perf_counter()
    case = generate_benchmark_case(spec)
    problem = prepare_portfolio(
        assets=case["assets"],
        expected_returns=case["expected_returns"],
        covariance=case["covariance"],
        cardinality=case["cardinality"],
        risk_aversion=case["risk_aversion"],
        penalty=1.0,
    )
    exact = problem["benchmark"][0]
    penalty_sufficiency = problem["penalty_sufficiency"]
    _, metrics = run_qaoa_portfolio(
        linear=problem["linear"],
        quadratic=problem["quadratic"],
        cardinality=case["cardinality"],
        portfolio_objective=problem["objective"],
        qubo_energy=problem["qubo_energy"],
        exact_selection=str(exact["Selection"]),
        exact_objective=float(exact["Objective"]),
        depth=2,
        optimizer_shots=64,
        final_shots=256,
        max_iterations=8,
        seed=int(case["seed"]),
    )
    runtime = perf_counter() - started
    gap = float(metrics["best_feasible_objective"]) - float(exact["Objective"])
    denominator = max(abs(float(exact["Objective"])), 1e-12)
    return {
        "case_id": case["case_id"],
        "asset_count": case["asset_count"],
        "problem_type": case["problem_type"],
        "problem_label": BENCHMARK_TYPES[case["problem_type"]],
        "replicate": case["replicate"],
        "penalty_sufficiency_guaranteed": bool(penalty_sufficiency["guaranteed"]),
        "required_penalty_exclusive": penalty_sufficiency[
            "required_penalty_exclusive"
        ],
        "exact_objective": float(exact["Objective"]),
        "qaoa_objective": float(metrics["best_feasible_objective"]),
        "objective_gap": gap,
        "objective_gap_percent": gap / denominator * 100,
        "feasibility_rate": float(metrics["feasibility_rate"]),
        "runtime_seconds": runtime,
        "circuit_depth": int(metrics["circuit_depth"]),
        "two_qubit_gates": int(metrics["two_qubit_gates"]),
        "feasible_shots": int(metrics["feasible_shots"]),
        "final_shots": int(metrics["final_shots"]),
        "execution": "Qiskit Aer simulator",
    }
