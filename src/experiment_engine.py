"""Reproducible, matched classical and QAOA experiments for synthetic portfolios."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from itertools import combinations
import json
from math import comb
import platform
from statistics import mean, pstdev
from time import perf_counter
from typing import Any, Callable

import numpy as np
import qiskit
import qiskit_aer
import scipy

from src.portfolio_workflow import (
    build_qubo,
    validate_portfolio_inputs,
    verify_qubo,
)
from src.qaoa_portfolio import MAX_AER_SEED, run_qaoa_portfolio

SUPPORTED_ASSET_COUNTS = (3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20)
ALGORITHMS = ("exact", "greedy", "random", "annealing", "qaoa")


def generate_portfolio_instance(
    asset_count: int,
    cardinality: int,
    seed: int,
    covariance_structure: str = "mixed",
) -> dict[str, Any]:
    if isinstance(asset_count, bool) or not isinstance(asset_count, int) or asset_count not in SUPPORTED_ASSET_COUNTS:
        raise ValueError(f"asset_count must be one of {SUPPORTED_ASSET_COUNTS}.")
    if isinstance(cardinality, bool) or not isinstance(cardinality, int) or not 1 <= cardinality <= asset_count:
        raise ValueError("cardinality must be an integer from 1 to asset_count.")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")
    if covariance_structure not in {"independent", "correlated", "mixed"}:
        raise ValueError("covariance_structure must be independent, correlated, or mixed.")

    rng = np.random.default_rng(seed)
    if covariance_structure == "independent":
        covariance = np.diag(rng.uniform(0.008, 0.045, asset_count))
    elif covariance_structure == "correlated":
        factor = rng.uniform(0.035, 0.11, (asset_count, 1))
        covariance = factor @ factor.T + np.diag(
            rng.uniform(0.006, 0.02, asset_count)
        )
    else:
        factor = rng.normal(0, 0.055, (asset_count, min(3, asset_count)))
        covariance = factor @ factor.T + np.diag(
            rng.uniform(0.007, 0.025, asset_count)
        )
    return {
        "assets": [f"A{index + 1}" for index in range(asset_count)],
        "expected_returns": rng.uniform(0.04, 0.18, asset_count).tolist(),
        "covariance": covariance.tolist(),
        "cardinality": cardinality,
        "seed": seed,
        "covariance_structure": covariance_structure,
    }


def _selection_string(selection: np.ndarray) -> str:
    return "".join(str(int(bit)) for bit in selection)


def _candidate_objective(
    selection: np.ndarray,
    returns: np.ndarray,
    covariance: np.ndarray,
    risk_aversion: float,
) -> float:
    return float(risk_aversion * (selection @ covariance @ selection) - returns @ selection)


def _exact_search(
    returns: np.ndarray,
    covariance: np.ndarray,
    cardinality: int,
    risk_aversion: float,
    candidate_limit: int,
) -> tuple[dict[str, Any], int]:
    candidate_count = comb(len(returns), cardinality)
    if candidate_count > candidate_limit:
        raise ValueError(
            f"Exact search requires {candidate_count} candidates, exceeding "
            f"the configured limit of {candidate_limit}."
        )
    best: dict[str, Any] | None = None
    for selected_indices in combinations(range(len(returns)), cardinality):
        selection = np.zeros(len(returns), dtype=int)
        selection[list(selected_indices)] = 1
        objective = _candidate_objective(
            selection, returns, covariance, risk_aversion
        )
        if best is None or objective < best["objective"]:
            best = {
                "selection": _selection_string(selection),
                "objective": objective,
            }
    if best is None:
        raise RuntimeError("Exact search generated no feasible portfolios.")
    return best, candidate_count


def _greedy_search(
    returns: np.ndarray,
    covariance: np.ndarray,
    cardinality: int,
    risk_aversion: float,
) -> tuple[str, float, int]:
    selected: list[int] = []
    evaluations = 0
    while len(selected) < cardinality:
        candidates = []
        for index in range(len(returns)):
            if index not in selected:
                proposal = np.zeros(len(returns), dtype=int)
                proposal[selected + [index]] = 1
                candidates.append(
                    (
                        _candidate_objective(
                            proposal, returns, covariance, risk_aversion
                        ),
                        index,
                    )
                )
                evaluations += 1
        selected.append(min(candidates)[1])

    current = np.zeros(len(returns), dtype=int)
    current[selected] = 1
    current_value = _candidate_objective(current, returns, covariance, risk_aversion)
    while True:
        best_swap: tuple[float, int, int] | None = None
        for removed in selected:
            for added in range(len(returns)):
                if added in selected:
                    continue
                proposal = current.copy()
                proposal[removed] = 0
                proposal[added] = 1
                value = _candidate_objective(
                    proposal, returns, covariance, risk_aversion
                )
                evaluations += 1
                if value < current_value and (
                    best_swap is None or value < best_swap[0]
                ):
                    best_swap = (value, removed, added)
        if best_swap is None:
            break
        current_value, removed, added = best_swap
        selected.remove(removed)
        selected.append(added)
        current[removed] = 0
        current[added] = 1
    return _selection_string(current), current_value, evaluations


def _random_search(
    returns: np.ndarray,
    covariance: np.ndarray,
    cardinality: int,
    risk_aversion: float,
    samples: int,
    seed: int,
) -> tuple[str, float, int]:
    rng = np.random.default_rng(seed)
    best_selection: np.ndarray | None = None
    best_value = float("inf")
    for _ in range(samples):
        selection = np.zeros(len(returns), dtype=int)
        selection[rng.choice(len(returns), cardinality, replace=False)] = 1
        value = _candidate_objective(selection, returns, covariance, risk_aversion)
        if value < best_value:
            best_selection, best_value = selection, value
    if best_selection is None:
        raise RuntimeError("Random feasible search generated no candidates.")
    return _selection_string(best_selection), best_value, samples


def _annealing_search(
    returns: np.ndarray,
    covariance: np.ndarray,
    cardinality: int,
    risk_aversion: float,
    steps: int,
    seed: int,
) -> tuple[str, float, int]:
    rng = np.random.default_rng(seed)
    size = len(returns)
    current = np.zeros(size, dtype=int)
    current[rng.choice(size, cardinality, replace=False)] = 1
    current_value = _candidate_objective(current, returns, covariance, risk_aversion)
    best = current.copy()
    best_value = current_value
    temperature_scale = max(abs(current_value), float(np.ptp(returns)), 1e-6)
    initial_temperature = temperature_scale
    final_temperature = temperature_scale * 1e-3

    for step in range(steps):
        selected = np.flatnonzero(current)
        unselected = np.flatnonzero(1 - current)
        removed = int(rng.choice(selected))
        added = int(rng.choice(unselected))
        proposal = current.copy()
        proposal[removed] = 0
        proposal[added] = 1
        proposal_value = _candidate_objective(
            proposal, returns, covariance, risk_aversion
        )
        fraction = step / max(steps - 1, 1)
        temperature = initial_temperature * (
            final_temperature / initial_temperature
        ) ** fraction
        delta = proposal_value - current_value
        if delta < 0 or rng.random() < np.exp(-delta / temperature):
            current, current_value = proposal, proposal_value
            if current_value < best_value:
                best, best_value = current.copy(), current_value
    return _selection_string(best), best_value, steps


def _validate_positive_integer(name: str, value: int, maximum: int | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} cannot exceed {maximum}.")


def run_experiment(
    *,
    asset_count: int,
    cardinality: int,
    seed: int,
    covariance_structure: str = "mixed",
    risk_aversion: float = 1.0,
    penalty: float = 1.0,
    algorithms: tuple[str, ...] | list[str] = ("greedy", "random", "annealing", "qaoa"),
    repetitions: int = 3,
    random_samples: int = 512,
    annealing_steps: int = 2000,
    exact_candidate_limit: int = 250_000,
    qaoa_depth: int = 1,
    qaoa_optimizer_shots: int = 128,
    qaoa_final_shots: int = 512,
    qaoa_max_iterations: int = 12,
) -> dict[str, Any]:
    if isinstance(asset_count, bool) or not isinstance(asset_count, int) or asset_count not in SUPPORTED_ASSET_COUNTS:
        raise ValueError(f"asset_count must be one of {SUPPORTED_ASSET_COUNTS}.")
    if isinstance(cardinality, bool) or not isinstance(cardinality, int) or not 1 <= cardinality <= asset_count:
        raise ValueError("cardinality must be an integer from 1 to asset_count.")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative integer.")
    if isinstance(risk_aversion, bool) or not isinstance(risk_aversion, (int, float)) or not np.isfinite(risk_aversion) or risk_aversion < 0:
        raise ValueError("risk_aversion must be finite and non-negative.")
    if isinstance(penalty, bool) or not isinstance(penalty, (int, float)) or not np.isfinite(penalty) or penalty <= 0:
        raise ValueError("penalty must be finite and positive.")
    if covariance_structure not in {"independent", "correlated", "mixed"}:
        raise ValueError("covariance_structure must be independent, correlated, or mixed.")
    _validate_positive_integer("repetitions", repetitions, 20)
    _validate_positive_integer("random_samples", random_samples, 100_000)
    _validate_positive_integer("annealing_steps", annealing_steps, 1_000_000)
    _validate_positive_integer("exact_candidate_limit", exact_candidate_limit, 1_000_000)
    _validate_positive_integer("qaoa_depth", qaoa_depth, 8)
    _validate_positive_integer("qaoa_optimizer_shots", qaoa_optimizer_shots, 8192)
    _validate_positive_integer("qaoa_final_shots", qaoa_final_shots, 32768)
    _validate_positive_integer("qaoa_max_iterations", qaoa_max_iterations, 100)

    requested_algorithms = tuple(dict.fromkeys(algorithms))
    if not requested_algorithms or any(
        algorithm not in ALGORITHMS or algorithm == "exact"
        for algorithm in requested_algorithms
    ):
        raise ValueError(
            f"Choose one or more algorithms from {tuple(a for a in ALGORITHMS if a != 'exact')}."
        )
    if "qaoa" in requested_algorithms and qaoa_max_iterations < 2 * qaoa_depth + 2:
        raise ValueError(
            f"qaoa_max_iterations must be at least {2 * qaoa_depth + 2} for COBYLA."
        )
    if "qaoa" in requested_algorithms and seed + 1009 * repetitions > MAX_AER_SEED:
        raise ValueError(
            f"seed must leave room for repeated QAOA simulator seeds up to {MAX_AER_SEED}."
        )

    instance = generate_portfolio_instance(
        asset_count, cardinality, seed, covariance_structure
    )
    returns = np.asarray(instance["expected_returns"], dtype=float)
    covariance = np.asarray(instance["covariance"], dtype=float)
    assets = list(instance["assets"])
    returns, covariance = validate_portfolio_inputs(
        assets, returns, covariance, cardinality, float(risk_aversion)
    )
    exact_started = perf_counter()
    exact, exact_evaluations = _exact_search(
        returns,
        covariance,
        cardinality,
        float(risk_aversion),
        exact_candidate_limit,
    )
    exact_runtime = perf_counter() - exact_started
    linear, quadratic, _, qubo_energy = build_qubo(
        returns, covariance, cardinality, float(risk_aversion), float(penalty)
    )
    total_configurations = 1 << asset_count
    if asset_count <= 12:
        verified_configurations = verify_qubo(
            returns,
            covariance,
            cardinality,
            float(risk_aversion),
            float(penalty),
            qubo_energy,
        )
        exhaustive_verification = True
    else:
        verification_rng = np.random.default_rng(seed ^ 0x5EED)
        checks = min(512, total_configurations)
        for _ in range(checks):
            selection = verification_rng.integers(0, 2, asset_count)
            direct = _candidate_objective(
                selection, returns, covariance, float(risk_aversion)
            ) + float(penalty) * (int(selection.sum()) - cardinality) ** 2
            if not np.isclose(qubo_energy(selection), direct, rtol=1e-10, atol=1e-10):
                raise AssertionError("Sampled QUBO verification failed.")
        verified_configurations = checks
        exhaustive_verification = False

    objective_lower_bound = float(
        float(risk_aversion) * np.minimum(covariance, 0).sum()
        - np.maximum(returns, 0).sum()
    )
    penalty_threshold = max(0.0, float(exact["objective"]) - objective_lower_bound)
    penalty_certified = float(penalty) > penalty_threshold
    instance = {
        "generation_version": "synthetic-portfolio-v1",
        "assets": assets,
        "expected_returns": returns.tolist(),
        "covariance": covariance.tolist(),
        "cardinality": cardinality,
        "risk_aversion": float(risk_aversion),
        "penalty": float(penalty),
        "covariance_structure": covariance_structure,
        "seed": seed,
    }
    dataset_id = sha256(
        json.dumps(instance, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    runs: list[dict[str, Any]] = [
        {
            "algorithm": "exact",
            "run_index": 1,
            "seed": seed,
            "selection": exact["selection"],
            "objective": float(exact["objective"]),
            "objective_gap": 0.0,
            "feasible": True,
            "optimal": True,
            "runtime_seconds": exact_runtime,
            "objective_evaluations": exact_evaluations,
            "execution": "classical exact combination search",
        }
    ]

    objective_functions: dict[str, Callable[[int], tuple[str, float, int]]] = {
        "random": lambda run_seed: _random_search(
            returns, covariance, cardinality, float(risk_aversion), random_samples, run_seed
        ),
        "annealing": lambda run_seed: _annealing_search(
            returns, covariance, cardinality, float(risk_aversion), annealing_steps, run_seed
        ),
    }
    for algorithm in requested_algorithms:
        for run_index in range(1, repetitions + 1):
            run_seed = seed + 1009 * run_index
            started = perf_counter()
            if algorithm == "qaoa":
                samples, metrics = run_qaoa_portfolio(
                    linear=linear,
                    quadratic=quadratic,
                    cardinality=cardinality,
                    portfolio_objective=lambda x: _candidate_objective(
                        x, returns, covariance, float(risk_aversion)
                    ),
                    qubo_energy=qubo_energy,
                    exact_selection=str(exact["selection"]),
                    exact_objective=float(exact["objective"]),
                    depth=qaoa_depth,
                    optimizer_shots=qaoa_optimizer_shots,
                    final_shots=qaoa_final_shots,
                    max_iterations=qaoa_max_iterations,
                    seed=run_seed,
                    include_circuit=True,
                    allow_no_feasible=True,
                )
                selected = metrics["best_feasible_selection"]
                value = metrics["best_feasible_objective"]
                record: dict[str, Any] = {
                    "algorithm": algorithm,
                    "run_index": run_index,
                    "seed": run_seed,
                    "selection": selected,
                    "objective": value,
                    "objective_gap": (
                        float(value) - float(exact["objective"])
                        if value is not None
                        else None
                    ),
                    "feasible": int(metrics["feasible_shots"]) > 0,
                    "optimal": selected == exact["selection"],
                    "runtime_seconds": perf_counter() - started,
                    "objective_evaluations": int(metrics["optimizer_evaluations"]),
                    "feasibility_rate": float(metrics["feasibility_rate"]),
                    "optimal_sample_rate": float(metrics["optimal_sample_rate"]),
                    "sampled_energy_estimate": float(metrics["sampled_energy_estimate"]),
                    "circuit_depth": int(metrics["circuit_depth"]),
                    "compiled_qubits": int(metrics["compiled_qubits"]),
                    "two_qubit_gates": int(metrics["two_qubit_gates"]),
                    "compiled_gate_counts": metrics["compiled_gate_counts"],
                    "logical_circuit_depth": int(metrics["logical_circuit"]["depth"]),
                    "execution": "Qiskit Aer simulator",
                    "sample_counts": {
                        str(row["Selection"]): int(row["Shots"])
                        for row in samples.to_dict(orient="records")
                    },
                }
            elif algorithm == "greedy":
                selected, value, evaluations = _greedy_search(
                    returns, covariance, cardinality, float(risk_aversion)
                )
                record = {
                    "algorithm": algorithm,
                    "run_index": run_index,
                    "seed": run_seed,
                    "selection": selected,
                    "objective": value,
                    "objective_gap": value - float(exact["objective"]),
                    "feasible": selected.count("1") == cardinality,
                    "optimal": selected == exact["selection"],
                    "runtime_seconds": perf_counter() - started,
                    "objective_evaluations": evaluations,
                    "execution": "classical CPU",
                }
            else:
                selected, value, evaluations = objective_functions[algorithm](run_seed)
                record = {
                    "algorithm": algorithm,
                    "run_index": run_index,
                    "seed": run_seed,
                    "selection": selected,
                    "objective": value,
                    "objective_gap": value - float(exact["objective"]),
                    "feasible": selected.count("1") == cardinality,
                    "optimal": selected == exact["selection"],
                    "runtime_seconds": perf_counter() - started,
                    "objective_evaluations": evaluations,
                    "execution": "classical CPU",
                }
            runs.append(record)

    summaries = []
    for algorithm in ("exact", *requested_algorithms):
        same = [run for run in runs if run["algorithm"] == algorithm]
        objective_values = [float(run["objective"]) for run in same if run["objective"] is not None]
        gaps = [float(run["objective_gap"]) for run in same if run["objective_gap"] is not None]
        selections = [str(run["selection"]) for run in same if run["selection"] is not None]
        frequencies = Counter(selections)
        summaries.append(
            {
                "algorithm": algorithm,
                "runs": len(same),
                "mean_objective": mean(objective_values) if objective_values else None,
                "objective_stddev": pstdev(objective_values) if len(objective_values) > 1 else 0.0,
                "best_objective": min(objective_values) if objective_values else None,
                "worst_objective": max(objective_values) if objective_values else None,
                "mean_objective_gap": mean(gaps) if gaps else None,
                "objective_gap_stddev": pstdev(gaps) if len(gaps) > 1 else 0.0,
                "mean_runtime_seconds": mean(float(run["runtime_seconds"]) for run in same),
                "feasibility_rate": mean(float(run.get("feasibility_rate", run["feasible"])) for run in same),
                "optimal_run_rate": mean(float(run["optimal"]) for run in same),
                "most_common_selection": frequencies.most_common(1)[0][0] if frequencies else None,
                "selection_repeatability": (
                    frequencies.most_common(1)[0][1] / len(selections)
                    if selections
                    else 0.0
                ),
                "sampled_optimality_rate": (
                    mean(float(run["optimal_sample_rate"]) for run in same if "optimal_sample_rate" in run)
                    if any("optimal_sample_rate" in run for run in same)
                    else None
                ),
            }
        )

    return {
        "schema_version": 1,
        "environment": {
            "python": platform.python_version(),
            "qiskit": qiskit.__version__,
            "qiskit_aer": qiskit_aer.__version__,
            "scipy": scipy.__version__,
            "execution": "local CPU and Qiskit Aer simulator",
        },
        "objective_definition": (
            "risk_aversion * x.T @ covariance @ x - expected_returns @ x"
        ),
        "dataset_id": dataset_id,
        "instance": instance,
        "exact_reference": {
            **exact,
            "candidate_count": exact_evaluations,
            "method": "exact feasible combination search",
        },
        "qubo_validation": {
            "checked_configurations": verified_configurations,
            "total_configurations": total_configurations,
            "exhaustive": exhaustive_verification,
        },
        "penalty_diagnostic": {
            "certified_sufficient": penalty_certified,
            "strict_sufficient_threshold": penalty_threshold,
            "infeasible_objective_lower_bound": objective_lower_bound,
        },
        "algorithm_configuration": {
            "algorithms": ["exact", *requested_algorithms],
            "repetitions": repetitions,
            "random_samples": random_samples,
            "annealing_steps": annealing_steps,
            "exact_candidate_limit": exact_candidate_limit,
            "qaoa_depth": qaoa_depth,
            "qaoa_optimizer_shots": qaoa_optimizer_shots,
            "qaoa_final_shots": qaoa_final_shots,
            "qaoa_max_iterations": qaoa_max_iterations,
        },
        "runs": runs,
        "summaries": summaries,
    }
