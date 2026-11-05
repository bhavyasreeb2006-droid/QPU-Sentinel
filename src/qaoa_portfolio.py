from collections import Counter
from collections.abc import Callable

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import ParameterVector
from qiskit_aer import AerSimulator
from scipy.optimize import minimize

MAX_AER_SEED = (1 << 32) - 1 - 100_000


def _validate_positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")


def selection_from_count(bitstring: str) -> str:
    compact = bitstring.replace(" ", "")
    if not compact or any(bit not in "01" for bit in compact):
        raise ValueError("Measured count key must contain binary digits.")
    return compact[::-1]


def run_qaoa_portfolio(
    *,
    linear: np.ndarray,
    quadratic: np.ndarray,
    cardinality: int,
    portfolio_objective: Callable[[np.ndarray], float],
    qubo_energy: Callable[[np.ndarray], float],
    exact_selection: str,
    exact_objective: float,
    depth: int = 2,
    optimizer_shots: int = 1024,
    final_shots: int = 8192,
    max_iterations: int = 80,
    seed: int = 42,
    include_circuit: bool = False,
    allow_no_feasible: bool = False,
) -> tuple[pd.DataFrame, dict[str, object]]:
    linear = np.asarray(linear, dtype=float)
    quadratic = np.asarray(quadratic, dtype=float)
    n = len(linear)
    if n < 1 or linear.shape != (n,) or quadratic.shape != (n, n):
        raise ValueError("QUBO coefficient arrays have incompatible dimensions.")
    if not np.all(np.isfinite(linear)) or not np.all(np.isfinite(quadratic)):
        raise ValueError("QUBO coefficients must be finite.")
    if np.any(np.tril(quadratic) != 0):
        raise ValueError("QUBO pair coefficients must use the upper triangle.")
    _validate_positive_integer("depth", depth)
    _validate_positive_integer("optimizer_shots", optimizer_shots)
    _validate_positive_integer("final_shots", final_shots)
    _validate_positive_integer("max_iterations", max_iterations)
    if (
        isinstance(seed, bool)
        or not isinstance(seed, (int, np.integer))
        or not 0 <= seed <= MAX_AER_SEED
    ):
        raise ValueError(f"seed must be an integer from 0 to {MAX_AER_SEED}.")
    if not isinstance(exact_selection, str) or len(exact_selection) != n:
        raise ValueError("exact_selection must contain one bit per QUBO variable.")
    if any(bit not in "01" for bit in exact_selection):
        raise ValueError("exact_selection must contain only binary digits.")
    if not np.isfinite(exact_objective):
        raise ValueError("exact_objective must be finite.")

    z_linear = -linear / 2
    zz_coefficients = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            pair_coefficient = quadratic[i, j] / 4
            z_linear[i] -= pair_coefficient
            z_linear[j] -= pair_coefficient
            zz_coefficients[i, j] = pair_coefficient

    gamma_parameters = ParameterVector("gamma", depth)
    beta_parameters = ParameterVector("beta", depth)
    parameters = list(gamma_parameters) + list(beta_parameters)
    if max_iterations < len(parameters) + 2:
        raise ValueError(
            f"max_iterations must be at least {len(parameters) + 2} for COBYLA."
        )
    circuit = QuantumCircuit(n)
    circuit.h(range(n))

    for layer in range(depth):
        gamma = gamma_parameters[layer]
        beta = beta_parameters[layer]
        for i in range(n):
            circuit.rz(2 * gamma * z_linear[i], i)
        for i in range(n):
            for j in range(i + 1, n):
                if zz_coefficients[i, j] != 0:
                    circuit.rzz(2 * gamma * zz_coefficients[i, j], i, j)
        for i in range(n):
            circuit.rx(2 * beta, i)

    circuit.measure_all()
    simulator = AerSimulator()
    compiled_circuit = transpile(
        circuit, simulator, optimization_level=1, seed_transpiler=seed
    )
    evaluation_number = 0

    def sampled_energy(values: np.ndarray) -> float:
        nonlocal evaluation_number
        evaluation_number += 1
        bound_circuit = compiled_circuit.assign_parameters(
            dict(zip(parameters, values)), inplace=False
        )
        counts = simulator.run(
            bound_circuit,
            shots=optimizer_shots,
            seed_simulator=seed + evaluation_number,
        ).result().get_counts()
        return sum(
            count
            * qubo_energy(
                np.fromiter(map(int, selection_from_count(bits)), dtype=int)
            )
            for bits, count in counts.items()
        ) / optimizer_shots

    optimization = minimize(
        sampled_energy,
        np.array([0.5] * depth + [0.3] * depth),
        method="COBYLA",
        options={"maxiter": max_iterations, "rhobeg": 0.5, "tol": 1e-3},
    )
    final_circuit = compiled_circuit.assign_parameters(
        dict(zip(parameters, optimization.x)), inplace=False
    )
    counts = simulator.run(
        final_circuit,
        shots=final_shots,
        seed_simulator=seed + 100_000,
    ).result().get_counts()

    rows = []
    for measured_bits, count in counts.items():
        selection = selection_from_count(measured_bits)
        sample = np.fromiter(map(int, selection), dtype=int)
        rows.append(
            {
                "Selection": selection,
                "Shots": count,
                "Probability": count / final_shots,
                "Feasible": int(np.sum(sample)) == cardinality,
                "Objective": portfolio_objective(sample),
                "QUBO Energy": qubo_energy(sample),
            }
        )

    results = pd.DataFrame(rows).sort_values(
        ["Feasible", "Shots"], ascending=[False, False]
    ).reset_index(drop=True)
    feasible = results[results["Feasible"]]
    if feasible.empty and not allow_no_feasible:
        raise RuntimeError(
            "QAOA produced no feasible samples; increase final_shots or optimize further."
        )

    best_feasible = (
        feasible.sort_values("Objective").iloc[0] if not feasible.empty else None
    )
    feasible_shots = int(sum(row["Shots"] for row in rows if row["Feasible"]))
    optimal_shots = int(
        sum(row["Shots"] for row in rows if row["Selection"] == exact_selection)
    )
    metrics: dict[str, object] = {
        "depth_p": depth,
        "optimizer_success": bool(optimization.success),
        "optimizer_evaluations": evaluation_number,
        "sampled_energy_estimate": float(optimization.fun),
        "circuit_depth": int(compiled_circuit.depth()),
        "compiled_qubits": int(compiled_circuit.num_qubits),
        "two_qubit_gates": int(
            sum(
                instruction.operation.num_qubits == 2
                for instruction in compiled_circuit.data
            )
        ),
        "compiled_gate_counts": dict(Counter(
            instruction.operation.name
            for instruction in compiled_circuit.data
            if instruction.operation.name not in {"barrier"}
        )),
        "final_shots": final_shots,
        "feasible_shots": feasible_shots,
        "feasibility_rate": feasible_shots / final_shots,
        "exact_selection": exact_selection,
        "exact_objective": float(exact_objective),
        "best_feasible_selection": (
            str(best_feasible["Selection"]) if best_feasible is not None else None
        ),
        "best_feasible_objective": (
            float(best_feasible["Objective"]) if best_feasible is not None else None
        ),
        "optimal_shots": optimal_shots,
        "optimal_sample_rate": optimal_shots / final_shots,
    }
    if include_circuit:
        logical_final_circuit = circuit.assign_parameters(
            dict(zip(parameters, optimization.x)), inplace=False
        )
        metrics["logical_circuit"] = {
            "depth": int(logical_final_circuit.depth()),
            "gate_counts": dict(Counter(
                instruction.operation.name
                for instruction in logical_final_circuit.data
                if instruction.operation.name not in {"barrier", "measure"}
            )),
            "measurement_count": int(logical_final_circuit.num_clbits),
            "operations": [
                {
                    "gate": instruction.operation.name,
                    "qubits": [
                        logical_final_circuit.find_bit(qubit).index
                        for qubit in instruction.qubits
                    ],
                    "classical_bits": [
                        logical_final_circuit.find_bit(bit).index
                        for bit in instruction.clbits
                    ],
                    "parameters": [
                        float(parameter) if isinstance(parameter, (int, float)) else str(parameter)
                        for parameter in instruction.operation.params
                    ],
                }
                for instruction in logical_final_circuit.data
                if instruction.operation.name != "barrier"
            ],
        }
    return results, metrics
