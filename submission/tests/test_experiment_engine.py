import unittest

import numpy as np

from src.experiment_engine import (
    SUPPORTED_ASSET_COUNTS,
    generate_portfolio_instance,
    run_experiment,
)
from src.qaoa_portfolio import selection_from_count


class ExperimentEngineTests(unittest.TestCase):
    def test_qiskit_count_keys_are_mapped_to_asset_order(self):
        self.assertEqual(selection_from_count("001"), "100")
        self.assertEqual(selection_from_count("100"), "001")
        self.assertEqual(selection_from_count("1 01"), "101")
        with self.assertRaisesRegex(ValueError, "binary digits"):
            selection_from_count("02")

    def test_supported_sizes_and_cardinalities_generate_psd_instances(self):
        self.assertEqual(
            SUPPORTED_ASSET_COUNTS,
            (3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20),
        )
        for size in SUPPORTED_ASSET_COUNTS:
            for cardinality in {1, size // 2, size}:
                case = generate_portfolio_instance(size, cardinality, seed=size)
                covariance = np.asarray(case["covariance"])
                self.assertEqual(covariance.shape, (size, size))
                self.assertGreaterEqual(
                    float(np.linalg.eigvalsh(covariance).min()), -1e-10
                )
                self.assertEqual(case["cardinality"], cardinality)

    def test_matched_classical_algorithms_are_feasible_and_repeatable(self):
        options = {
            "asset_count": 5,
            "cardinality": 2,
            "seed": 2026,
            "algorithms": ("greedy", "random", "annealing"),
            "repetitions": 3,
            "random_samples": 64,
            "annealing_steps": 200,
        }
        first = run_experiment(**options)
        second = run_experiment(**options)

        self.assertEqual(first["dataset_id"], second["dataset_id"])
        self.assertEqual(first["exact_reference"], second["exact_reference"])
        self.assertEqual(
            [(row["algorithm"], row["selection"], row["objective"]) for row in first["runs"]],
            [(row["algorithm"], row["selection"], row["objective"]) for row in second["runs"]],
        )
        self.assertTrue(all(row["feasible"] for row in first["runs"]))
        self.assertEqual(first["qubo_validation"]["checked_configurations"], 32)
        self.assertTrue(first["qubo_validation"]["exhaustive"])
        self.assertEqual(first["exact_reference"]["candidate_count"], 10)
        self.assertEqual(
            {row["algorithm"] for row in first["summaries"]},
            {"exact", "greedy", "random", "annealing"},
        )

    def test_twenty_asset_case_uses_bounded_combination_search(self):
        result = run_experiment(
            asset_count=20,
            cardinality=10,
            seed=2026,
            algorithms=("greedy", "random", "annealing"),
            repetitions=2,
            random_samples=32,
            annealing_steps=100,
        )

        self.assertEqual(result["exact_reference"]["candidate_count"], 184756)
        self.assertEqual(result["qubo_validation"]["checked_configurations"], 512)
        self.assertFalse(result["qubo_validation"]["exhaustive"])
        self.assertTrue(all(run["feasible"] for run in result["runs"]))
        self.assertEqual(
            result["algorithm_configuration"]["algorithms"],
            ["exact", "greedy", "random", "annealing"],
        )

    def test_qaoa_reports_measured_quality_and_resources(self):
        result = run_experiment(
            asset_count=3,
            cardinality=2,
            seed=7,
            algorithms=("qaoa",),
            repetitions=1,
            qaoa_optimizer_shots=32,
            qaoa_final_shots=128,
            qaoa_max_iterations=4,
        )
        run = next(run for run in result["runs"] if run["algorithm"] == "qaoa")

        self.assertEqual(run["execution"], "Qiskit Aer simulator")
        self.assertGreater(run["runtime_seconds"], 0)
        self.assertGreater(run["circuit_depth"], 0)
        self.assertGreater(run["two_qubit_gates"], 0)
        self.assertGreaterEqual(run["feasibility_rate"], 0)
        self.assertLessEqual(run["feasibility_rate"], 1)
        self.assertEqual(sum(run["sample_counts"].values()), 128)

    def test_exact_search_budget_and_invalid_algorithms_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceeding"):
            run_experiment(
                asset_count=6,
                cardinality=3,
                seed=1,
                algorithms=("greedy",),
                exact_candidate_limit=10,
            )
        with self.assertRaisesRegex(ValueError, "Choose one or more algorithms"):
            run_experiment(
                asset_count=3,
                cardinality=1,
                seed=1,
                algorithms=("not-an-algorithm",),
            )


if __name__ == "__main__":
    unittest.main()
