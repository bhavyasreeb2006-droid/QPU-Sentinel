"""Compatibility and suitability scoring for clearly simulated backend profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class BackendProfile:
    profile_id: str
    name: str
    qubits: int
    max_circuit_depth: int | None
    max_two_qubit_gates: int | None
    average_two_qubit_error: float | None
    average_readout_error: float | None
    coupling_edges: tuple[tuple[int, int], ...] | None
    profile_type: str = "SIMULATED PROFILE"
    source_note: str = "Illustrative scenario only; not a real device specification."


@dataclass(frozen=True)
class CircuitRequirements:
    qubits: int
    circuit_depth: int
    two_qubit_gates: int
    required_couplings: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class ScoredBackend:
    profile_id: str
    name: str
    profile_type: str
    compatible: bool
    score: float
    component_scores: dict[str, float]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def simulated_backend_profiles() -> tuple[BackendProfile, ...]:
    """Return fictional profiles for demonstrating the analyzer, not IBM backends."""
    return (
        BackendProfile(
            profile_id="simulated-line-5",
            name="Simulated Profile A - low-error line",
            qubits=5,
            max_circuit_depth=120,
            max_two_qubit_gates=160,
            average_two_qubit_error=0.005,
            average_readout_error=0.025,
            coupling_edges=((0, 1), (1, 2), (2, 3), (3, 4)),
        ),
        BackendProfile(
            profile_id="simulated-ring-7",
            name="Simulated Profile B - balanced ring",
            qubits=7,
            max_circuit_depth=60,
            max_two_qubit_gates=100,
            average_two_qubit_error=0.009,
            average_readout_error=0.040,
            coupling_edges=(
                (0, 1),
                (1, 2),
                (2, 3),
                (3, 0),
                (3, 4),
                (4, 5),
                (5, 6),
                (6, 0),
            ),
        ),
        BackendProfile(
            profile_id="simulated-grid-4",
            name="Simulated Profile C - compact dense",
            qubits=4,
            max_circuit_depth=18,
            max_two_qubit_gates=18,
            average_two_qubit_error=0.020,
            average_readout_error=0.060,
            coupling_edges=(
                (0, 1),
                (0, 2),
                (0, 3),
                (1, 2),
                (1, 3),
                (2, 3),
            ),
        ),
    )


def _validate_requirements(requirements: CircuitRequirements) -> None:
    if requirements.qubits < 1:
        raise ValueError("Circuit qubit count must be positive.")
    if requirements.circuit_depth < 0 or requirements.two_qubit_gates < 0:
        raise ValueError("Circuit depth and two-qubit gate count cannot be negative.")
    for left, right in requirements.required_couplings:
        if left == right or min(left, right) < 0 or max(left, right) >= requirements.qubits:
            raise ValueError("Required coupling indices must reference distinct circuit qubits.")


def _normalize_edge(edge: tuple[int, int]) -> tuple[int, int]:
    return tuple(sorted(edge))


def _graph_is_connected(
    qubit_count: int, edges: Iterable[tuple[int, int]]
) -> bool:
    if qubit_count <= 1:
        return True
    adjacency = {node: set() for node in range(qubit_count)}
    for left, right in edges:
        if left < qubit_count and right < qubit_count:
            adjacency[left].add(right)
            adjacency[right].add(left)
    visited = {0}
    frontier = [0]
    while frontier:
        for neighbor in adjacency[frontier.pop()]:
            if neighbor not in visited:
                visited.add(neighbor)
                frontier.append(neighbor)
    return len(visited) == qubit_count


def _bounded_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def score_backend(
    profile: BackendProfile, requirements: CircuitRequirements
) -> ScoredBackend:
    _validate_requirements(requirements)
    if profile.qubits < 1:
        raise ValueError("A backend profile must provide a positive qubit count.")
    if profile.max_circuit_depth is not None and profile.max_circuit_depth < 1:
        raise ValueError("A depth budget must be positive when provided.")
    if profile.max_two_qubit_gates is not None and profile.max_two_qubit_gates < 1:
        raise ValueError("A two-qubit gate budget must be positive when provided.")
    if profile.coupling_edges is not None:
        for edge in profile.coupling_edges:
            if (
                len(edge) != 2
                or edge[0] == edge[1]
                or min(edge) < 0
                or max(edge) >= profile.qubits
            ):
                raise ValueError("Profile couplers must reference distinct available qubits.")
    reasons: list[str] = []
    compatible = True

    if profile.qubits < requirements.qubits:
        compatible = False
        reasons.append(
            f"Incompatible: {requirements.qubits} circuit qubits are required, "
            f"but the profile provides {profile.qubits}."
        )
    else:
        reasons.append(
            f"Capacity: {profile.qubits} profile qubits cover "
            f"{requirements.qubits} circuit qubits."
        )

    if profile.max_circuit_depth is None:
        depth_score = 50.0
        reasons.append("Depth limit unavailable; scored neutrally.")
    else:
        depth_score = _bounded_score(
            100 * (1 - requirements.circuit_depth / profile.max_circuit_depth)
        )
        if requirements.circuit_depth > profile.max_circuit_depth:
            compatible = False
            reasons.append(
                f"Incompatible: circuit depth {requirements.circuit_depth} exceeds "
                f"profile budget {profile.max_circuit_depth}."
            )
        else:
            reasons.append(
                f"Depth: {requirements.circuit_depth} of "
                f"{profile.max_circuit_depth} profile budget units."
            )

    if profile.max_two_qubit_gates is None:
        gate_budget_score = 50.0
        reasons.append("Two-qubit gate budget unavailable; scored neutrally.")
    else:
        gate_budget_score = _bounded_score(
            100 * (1 - requirements.two_qubit_gates / profile.max_two_qubit_gates)
        )
        if requirements.two_qubit_gates > profile.max_two_qubit_gates:
            compatible = False
            reasons.append(
                f"Incompatible: {requirements.two_qubit_gates} two-qubit gates "
                f"exceed profile budget {profile.max_two_qubit_gates}."
            )
        else:
            reasons.append(
                f"Two-qubit gates: {requirements.two_qubit_gates} of "
                f"{profile.max_two_qubit_gates} profile budget units."
            )

    if profile.average_two_qubit_error is None:
        gate_error_score = 50.0
        reasons.append("Two-qubit error data unavailable; scored neutrally.")
    else:
        if (
            not isfinite(profile.average_two_qubit_error)
            or not 0 <= profile.average_two_qubit_error <= 1
        ):
            raise ValueError("Two-qubit gate error must be a probability from 0 to 1.")
        gate_error_score = _bounded_score(
            100 * (1 - profile.average_two_qubit_error / 0.05)
        )
        reasons.append(
            f"Provided average two-qubit error: "
            f"{profile.average_two_qubit_error:.3%}."
        )

    if profile.average_readout_error is None:
        readout_score = 50.0
        reasons.append("Readout error data unavailable; scored neutrally.")
    else:
        if (
            not isfinite(profile.average_readout_error)
            or not 0 <= profile.average_readout_error <= 1
        ):
            raise ValueError("Readout error must be a probability from 0 to 1.")
        readout_score = _bounded_score(
            100 * (1 - profile.average_readout_error / 0.15)
        )
        reasons.append(
            f"Provided average readout error: "
            f"{profile.average_readout_error:.3%}."
        )

    if profile.coupling_edges is None:
        connectivity_score = 50.0
        reasons.append("Connectivity data unavailable; scored neutrally.")
    else:
        normalized_edges = {_normalize_edge(edge) for edge in profile.coupling_edges}
        if not _graph_is_connected(requirements.qubits, normalized_edges):
            compatible = False
            reasons.append(
                "Incompatible: the available couplers do not connect all circuit qubits."
            )
        required = {
            _normalize_edge(edge) for edge in requirements.required_couplings
        }
        if required:
            direct = len(required & normalized_edges)
            connectivity_score = _bounded_score(100 * direct / len(required))
            reasons.append(
                f"Connectivity: {direct}/{len(required)} required interactions are "
                "direct couplers; connected non-direct pairs may need routing."
            )
        else:
            connectivity_score = 100.0
            reasons.append("No specific circuit couplers were supplied.")

    components = {
        "qubit_capacity": 100.0
        if profile.qubits >= requirements.qubits
        else _bounded_score(100 * profile.qubits / requirements.qubits),
        "circuit_depth": depth_score,
        "two_qubit_gate_budget": gate_budget_score,
        "two_qubit_gate_error": gate_error_score,
        "readout_error": readout_score,
        "connectivity": connectivity_score,
    }
    weights = {
        "qubit_capacity": 0.15,
        "circuit_depth": 0.10,
        "two_qubit_gate_budget": 0.10,
        "two_qubit_gate_error": 0.25,
        "readout_error": 0.20,
        "connectivity": 0.20,
    }
    score = round(sum(components[key] * weights[key] for key in weights), 2)
    if not compatible:
        reasons.append("Recommendation: do not target this profile without changing the circuit.")
    else:
        reasons.append("Recommendation: compatible in this simulated-profile scenario.")

    return ScoredBackend(
        profile_id=profile.profile_id,
        name=profile.name,
        profile_type=profile.profile_type,
        compatible=compatible,
        score=score,
        component_scores=components,
        reasons=tuple(reasons),
    )


def analyze_backends(
    requirements: CircuitRequirements,
    profiles: Iterable[BackendProfile] | None = None,
) -> dict[str, object]:
    candidates = tuple(profiles) if profiles is not None else simulated_backend_profiles()
    if not candidates:
        raise ValueError("At least one backend profile is required for analysis.")

    scored = [score_backend(profile, requirements) for profile in candidates]
    scored.sort(key=lambda result: (result.compatible, result.score), reverse=True)
    recommended = next((result for result in scored if result.compatible), None)
    return {
        "profiles_are_simulated": all(
            result.profile_type == "SIMULATED PROFILE" for result in scored
        ),
        "scoring_weights": {
            "qubit_capacity": 15,
            "circuit_depth": 10,
            "two_qubit_gate_budget": 10,
            "two_qubit_gate_error": 25,
            "readout_error": 20,
            "connectivity": 20,
        },
        "recommended_profile_id": recommended.profile_id if recommended else None,
        "recommendation": (
            f"{recommended.name} is the highest-scoring compatible simulated profile "
            f"({recommended.score:.2f}/100)."
            if recommended
            else "No simulated profile satisfies the supplied requirements."
        ),
        "ranked_profiles": [result.to_dict() for result in scored],
        "notice": (
            "All three candidates are fictional simulated profiles with illustrative "
            "error rates and resource budgets. They are not IBM backend listings, "
            "calibration data, or hardware measurements."
        ),
    }
