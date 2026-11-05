import unittest

from src.hardware_suitability import (
    BackendProfile,
    CircuitRequirements,
    analyze_backends,
    score_backend,
    simulated_backend_profiles,
)


class HardwareSuitabilityTests(unittest.TestCase):
    def setUp(self):
        self.requirements = CircuitRequirements(
            qubits=4,
            circuit_depth=15,
            two_qubit_gates=12,
            required_couplings=(
                (0, 1),
                (0, 2),
                (0, 3),
                (1, 2),
                (1, 3),
                (2, 3),
            ),
        )

    def test_profiles_are_explicitly_simulated_and_ranked(self):
        profiles = simulated_backend_profiles()
        analysis = analyze_backends(self.requirements, profiles)

        self.assertEqual(len(profiles), 3)
        self.assertTrue(
            all(profile.profile_type == "SIMULATED PROFILE" for profile in profiles)
        )
        self.assertTrue(analysis["profiles_are_simulated"])
        self.assertEqual(len(analysis["ranked_profiles"]), 3)
        scores = [item["score"] for item in analysis["ranked_profiles"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertIn("fictional", analysis["notice"].lower())

    def test_capacity_shortfall_is_incompatible(self):
        profile = BackendProfile(
            profile_id="tiny",
            name="Tiny simulated profile",
            qubits=2,
            max_circuit_depth=40,
            max_two_qubit_gates=30,
            average_two_qubit_error=0.01,
            average_readout_error=0.03,
            coupling_edges=((0, 1),),
        )
        scored = score_backend(profile, self.requirements)

        self.assertFalse(scored.compatible)
        self.assertEqual(scored.component_scores["qubit_capacity"], 50.0)
        self.assertTrue(any("qubits are required" in reason for reason in scored.reasons))

    def test_depth_gate_budget_and_disconnected_graph_are_incompatible(self):
        profile = BackendProfile(
            profile_id="limited",
            name="Limited simulated profile",
            qubits=4,
            max_circuit_depth=10,
            max_two_qubit_gates=4,
            average_two_qubit_error=0.01,
            average_readout_error=0.03,
            coupling_edges=((0, 1), (2, 3)),
        )
        scored = score_backend(profile, self.requirements)

        self.assertFalse(scored.compatible)
        self.assertTrue(any("circuit depth" in reason for reason in scored.reasons))
        self.assertTrue(any("two-qubit gates" in reason for reason in scored.reasons))
        self.assertTrue(any("do not connect" in reason for reason in scored.reasons))

    def test_connectivity_component_uses_direct_required_couplers(self):
        profile = simulated_backend_profiles()[0]
        scored = score_backend(profile, self.requirements)

        self.assertEqual(scored.component_scores["connectivity"], 50.0)
        self.assertTrue(any("3/6 required interactions" in reason for reason in scored.reasons))
        self.assertTrue(scored.compatible)

    def test_missing_error_and_connectivity_data_are_scored_neutrally(self):
        profile = BackendProfile(
            profile_id="partial",
            name="Partial simulated profile",
            qubits=4,
            max_circuit_depth=None,
            max_two_qubit_gates=None,
            average_two_qubit_error=None,
            average_readout_error=None,
            coupling_edges=None,
        )
        scored = score_backend(profile, self.requirements)

        self.assertTrue(scored.compatible)
        self.assertEqual(scored.component_scores["circuit_depth"], 50.0)
        self.assertEqual(scored.component_scores["two_qubit_gate_error"], 50.0)
        self.assertEqual(scored.component_scores["readout_error"], 50.0)
        self.assertEqual(scored.component_scores["connectivity"], 50.0)

    def test_rejects_invalid_circuit_requirements(self):
        with self.assertRaisesRegex(ValueError, "distinct circuit qubits"):
            score_backend(
                simulated_backend_profiles()[0],
                CircuitRequirements(4, 10, 4, ((1, 1),)),
            )

    def test_rejects_error_rate_outside_probability_range(self):
        profile = BackendProfile(
            profile_id="invalid-error",
            name="Invalid simulated profile",
            qubits=4,
            max_circuit_depth=40,
            max_two_qubit_gates=30,
            average_two_qubit_error=1.2,
            average_readout_error=0.03,
            coupling_edges=((0, 1), (1, 2), (2, 3)),
        )
        with self.assertRaisesRegex(ValueError, "probability from 0 to 1"):
            score_backend(profile, self.requirements)


if __name__ == "__main__":
    unittest.main()
