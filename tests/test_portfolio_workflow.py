import unittest

import numpy as np

from src.hardware_suitability import CircuitRequirements, analyze_backends
from src.portfolio_workflow import (
    build_qubo,
    enumerate_classical_portfolios,
    prepare_portfolio,
    validate_portfolio_inputs,
    verify_qubo,
)
from src.webapp import DEFAULT_INPUTS, run_application_workflow


class PortfolioWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.assets = DEFAULT_INPUTS["assets"]
        self.returns, self.covariance = validate_portfolio_inputs(
            self.assets,
            DEFAULT_INPUTS["expected_returns"],
            DEFAULT_INPUTS["covariance"],
            DEFAULT_INPUTS["cardinality"],
            DEFAULT_INPUTS["risk_aversion"],
        )

    def test_classical_optimizer_preserves_verified_notebook_optimum(self):
        results = enumerate_classical_portfolios(
            self.assets, self.returns, self.covariance, 2, 2.0
        )

        self.assertEqual(len(results), 6)
        self.assertEqual(results[0]["Selection"], "0110")
        self.assertAlmostEqual(results[0]["Objective"], -0.093)
        self.assertEqual(results[0]["Assets"], ["ASSET_B", "ASSET_C"])

    def test_qubo_matches_penalized_objective_for_all_configurations(self):
        linear, quadratic, _, energy = build_qubo(
            self.returns, self.covariance, 2, 2.0, penalty=1.0
        )
        checked = verify_qubo(
            self.returns, self.covariance, 2, 2.0, 1.0, energy
        )

        self.assertEqual(checked, 16)
        np.testing.assert_allclose(linear, [-3.04, -3.055, -3.05, -3.025])
        self.assertAlmostEqual(energy(np.array([0, 1, 1, 0])), -0.093)
        self.assertEqual(quadratic.shape, (4, 4))

    def test_penalty_diagnostics_certify_default_and_flag_small_penalties(self):
        sufficient = prepare_portfolio(
            self.assets,
            self.returns,
            self.covariance,
            cardinality=2,
            risk_aversion=2.0,
            penalty=1.0,
        )["penalty_sufficiency"]
        insufficient = prepare_portfolio(
            self.assets,
            self.returns,
            self.covariance,
            cardinality=2,
            risk_aversion=2.0,
            penalty=0.1,
        )["penalty_sufficiency"]

        self.assertTrue(sufficient["guaranteed"])
        self.assertGreater(sufficient["required_penalty_exclusive"], 0)
        self.assertFalse(insufficient["guaranteed"])

    def test_portfolio_inputs_reject_invalid_covariance_and_cardinality(self):
        with self.assertRaisesRegex(ValueError, "symmetric"):
            validate_portfolio_inputs(
                ["A", "B"], [0.1, 0.2], [[0.1, 0.2], [0.0, 0.1]], 1, 1.0
            )
        with self.assertRaisesRegex(ValueError, "positive semidefinite"):
            validate_portfolio_inputs(
                ["A", "B"], [0.1, 0.2], [[1.0, 2.0], [2.0, 1.0]], 1, 1.0
            )
        with self.assertRaisesRegex(ValueError, "Cardinality"):
            validate_portfolio_inputs(
                ["A", "B"], [0.1, 0.2], [[0.1, 0.0], [0.0, 0.1]], 3, 1.0
            )

    def test_analyzer_consumes_measured_circuit_shape(self):
        problem = prepare_portfolio(
            self.assets, self.returns, self.covariance, 2, 2.0
        )
        analysis = analyze_backends(
            CircuitRequirements(
                qubits=len(self.assets),
                circuit_depth=15,
                two_qubit_gates=12,
                required_couplings=tuple(
                    (i, j)
                    for i in range(len(self.assets))
                    for j in range(i + 1, len(self.assets))
                    if problem["quadratic"][i, j] != 0
                ),
            )
        )

        self.assertTrue(analysis["profiles_are_simulated"])
        self.assertEqual(len(analysis["ranked_profiles"]), 3)
        self.assertIsNotNone(analysis["recommended_profile_id"])

    def test_application_runs_classical_qaoa_and_profile_analysis(self):
        payload = {
            **DEFAULT_INPUTS,
            "depth": 1,
            "optimizer_shots": 64,
            "final_shots": 2048,
            "max_iterations": 6,
        }
        result = run_application_workflow(payload)

        self.assertEqual(result["classical_results"][0]["Selection"], "0110")
        self.assertEqual(result["qaoa_metrics"]["final_shots"], 2048)
        self.assertGreater(result["qaoa_metrics"]["feasible_shots"], 0)
        self.assertEqual(result["input_summary"]["qubo_configurations_verified"], 16)
        self.assertTrue(result["hardware_analysis"]["profiles_are_simulated"])
        circuit = result["circuit_explorer"]
        self.assertEqual(circuit["measurement_count"], 4)
        self.assertEqual(circuit["gate_counts"]["h"], 4)
        self.assertTrue(any(op["gate"] == "rzz" for op in circuit["operations"]))


if __name__ == "__main__":
    unittest.main()
