from __future__ import annotations

from itertools import product
from typing import Callable

import numpy as np


def validate_portfolio_inputs(
    assets: list[str],
    expected_returns: list[float] | np.ndarray,
    covariance: list[list[float]] | np.ndarray,
    cardinality: int,
    risk_aversion: float,
) -> tuple[np.ndarray, np.ndarray]:
    if not assets or any(not isinstance(asset, str) or not asset.strip() for asset in assets):
        raise ValueError("Provide at least one non-empty asset name.")
    if len(set(assets)) != len(assets):
        raise ValueError("Asset names must be unique.")

    returns = np.asarray(expected_returns, dtype=float)
    covariance_matrix = np.asarray(covariance, dtype=float)
    size = len(assets)
    if returns.shape != (size,) or covariance_matrix.shape != (size, size):
        raise ValueError("Asset, return, and covariance dimensions must match.")
    if not np.all(np.isfinite(returns)) or not np.all(np.isfinite(covariance_matrix)):
        raise ValueError("Portfolio inputs must contain only finite numbers.")
    if not np.allclose(covariance_matrix, covariance_matrix.T, atol=1e-10):
        raise ValueError("Covariance matrix must be symmetric.")
    if np.any(np.linalg.eigvalsh(covariance_matrix) < -1e-10):
        raise ValueError("Covariance matrix must be positive semidefinite.")
    if isinstance(cardinality, bool) or not isinstance(cardinality, (int, np.integer)):
        raise ValueError("Cardinality must be an integer.")
    if not 1 <= cardinality <= size:
        raise ValueError("Cardinality must be between 1 and the number of assets.")
    if not np.isfinite(risk_aversion) or risk_aversion < 0:
        raise ValueError("Risk aversion must be a finite, non-negative number.")
    return returns, covariance_matrix


def make_portfolio_objective(
    expected_returns: np.ndarray,
    covariance: np.ndarray,
    risk_aversion: float,
) -> Callable[[np.ndarray], float]:
    def objective(selection: np.ndarray) -> float:
        risk = selection @ covariance @ selection
        returns = expected_returns @ selection
        return float(risk_aversion * risk - returns)

    return objective


def enumerate_classical_portfolios(
    assets: list[str],
    expected_returns: np.ndarray,
    covariance: np.ndarray,
    cardinality: int,
    risk_aversion: float,
) -> list[dict[str, object]]:
    objective = make_portfolio_objective(expected_returns, covariance, risk_aversion)
    rows = []
    for bits in product([0, 1], repeat=len(assets)):
        selection = np.asarray(bits, dtype=int)
        if int(np.sum(selection)) != cardinality:
            continue
        variance = float(selection @ covariance @ selection)
        returns = float(expected_returns @ selection)
        rows.append(
            {
                "Selection": "".join(map(str, bits)),
                "Assets": [
                    assets[index]
                    for index, included in enumerate(selection)
                    if included
                ],
                "Expected Return": returns,
                "Portfolio Variance": variance,
                "Objective": objective(selection),
            }
        )
    return sorted(rows, key=lambda row: float(row["Objective"]))


def build_qubo(
    expected_returns: np.ndarray,
    covariance: np.ndarray,
    cardinality: int,
    risk_aversion: float,
    penalty: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, float, Callable[[np.ndarray], float]]:
    size = len(expected_returns)
    if covariance.shape != (size, size):
        raise ValueError("Expected returns and covariance dimensions must match.")
    if not np.isfinite(penalty) or penalty <= 0:
        raise ValueError("QUBO penalty must be a finite, positive number.")

    linear = np.zeros(size)
    quadratic = np.zeros((size, size))
    for index in range(size):
        linear[index] = (
            risk_aversion * covariance[index, index]
            - expected_returns[index]
            + penalty * (1 - 2 * cardinality)
        )
    for left in range(size):
        for right in range(left + 1, size):
            quadratic[left, right] = (
                2 * risk_aversion * covariance[left, right] + 2 * penalty
            )
    constant = float(penalty * cardinality**2)

    def qubo_energy(selection: np.ndarray) -> float:
        energy = constant + float(np.dot(linear, selection))
        for left in range(size):
            for right in range(left + 1, size):
                energy += quadratic[left, right] * selection[left] * selection[right]
        return float(energy)

    return linear, quadratic, constant, qubo_energy


def _penalty_sufficiency_diagnostics(
    expected_returns: np.ndarray,
    covariance: np.ndarray,
    risk_aversion: float,
    penalty: float,
    feasible_objective: float,
) -> dict[str, object]:
    lower_bound = float(
        risk_aversion * np.minimum(covariance, 0).sum()
        - np.maximum(expected_returns, 0).sum()
    )
    if not np.isfinite(lower_bound) or not np.isfinite(feasible_objective):
        return {
            "guaranteed": False,
            "required_penalty_exclusive": None,
            "infeasible_objective_lower_bound": None,
        }

    required_penalty = max(0.0, feasible_objective - lower_bound)
    return {
        "guaranteed": bool(penalty > required_penalty),
        "required_penalty_exclusive": float(required_penalty),
        "infeasible_objective_lower_bound": lower_bound,
    }


def verify_qubo(
    expected_returns: np.ndarray,
    covariance: np.ndarray,
    cardinality: int,
    risk_aversion: float,
    penalty: float,
    qubo_energy: Callable[[np.ndarray], float],
) -> int:
    objective = make_portfolio_objective(expected_returns, covariance, risk_aversion)
    size = len(expected_returns)
    checked = 0
    for bits in product([0, 1], repeat=size):
        selection = np.asarray(bits, dtype=int)
        expected = objective(selection) + penalty * (
            int(np.sum(selection)) - cardinality
        ) ** 2
        if not np.isclose(qubo_energy(selection), expected):
            raise AssertionError(f"QUBO mismatch for selection {bits}.")
        checked += 1
    return checked


def prepare_portfolio(
    assets: list[str],
    expected_returns: list[float] | np.ndarray,
    covariance: list[list[float]] | np.ndarray,
    cardinality: int,
    risk_aversion: float,
    penalty: float = 1.0,
) -> dict[str, object]:
    returns, covariance_matrix = validate_portfolio_inputs(
        assets, expected_returns, covariance, cardinality, risk_aversion
    )
    objective = make_portfolio_objective(returns, covariance_matrix, risk_aversion)
    benchmark = enumerate_classical_portfolios(
        assets, returns, covariance_matrix, cardinality, risk_aversion
    )
    penalty_sufficiency = _penalty_sufficiency_diagnostics(
        returns,
        covariance_matrix,
        risk_aversion,
        penalty,
        float(benchmark[0]["Objective"]),
    )
    linear, quadratic, constant, qubo_energy = build_qubo(
        returns, covariance_matrix, cardinality, risk_aversion, penalty
    )
    verified_configurations = verify_qubo(
        returns,
        covariance_matrix,
        cardinality,
        risk_aversion,
        penalty,
        qubo_energy,
    )
    return {
        "assets": assets,
        "expected_returns": returns,
        "covariance": covariance_matrix,
        "cardinality": cardinality,
        "risk_aversion": risk_aversion,
        "penalty": penalty,
        "penalty_sufficiency": penalty_sufficiency,
        "objective": objective,
        "benchmark": benchmark,
        "linear": linear,
        "quadratic": quadratic,
        "constant": constant,
        "qubo_energy": qubo_energy,
        "verified_configurations": verified_configurations,
    }
