import unittest

import numpy as np

from src.benchmark_workflow import (
    ASSET_COUNTS,
    BENCHMARK_TYPES,
    benchmark_specs,
    generate_benchmark_case,
    run_benchmark_case,
    select_benchmark_specs,
)


class BenchmarkWorkflowTests(unittest.TestCase):
    def test_planned_catalog_is_filtered_without_generating_results(self):
        specs = list(benchmark_specs())

        self.assertEqual(len(specs), 60)
        self.assertEqual(len(select_benchmark_specs(4, "correlated")), 5)
        self.assertEqual(len(select_benchmark_specs(6)), 15)
        self.assertEqual(len(select_benchmark_specs(problem_type="mixed")), 20)
        self.assertEqual(set(ASSET_COUNTS), {3, 4, 5, 6})
        self.assertEqual(len(BENCHMARK_TYPES), 3)

    def test_generated_case_is_reproducible_and_positive_semidefinite(self):
        spec = select_benchmark_specs(5, "mixed")[0]
        first = generate_benchmark_case(spec)
        second = generate_benchmark_case(spec)

        self.assertEqual(first, second)
        covariance = np.asarray(first["covariance"])
        np.testing.assert_allclose(covariance, covariance.T)
        self.assertGreaterEqual(float(np.linalg.eigvalsh(covariance).min()), -1e-10)

    def test_case_runs_qaoa_and_returns_measured_metrics(self):
        spec = select_benchmark_specs(3, "independent")[0]
        result = run_benchmark_case(spec)

        self.assertEqual(result["case_id"], spec["case_id"])
        self.assertEqual(result["execution"], "Qiskit Aer simulator")
        self.assertIn("penalty_sufficiency_guaranteed", result)
        self.assertGreaterEqual(result["required_penalty_exclusive"], 0)
        self.assertGreaterEqual(result["feasibility_rate"], 0)
        self.assertLessEqual(result["feasibility_rate"], 1)
        self.assertGreater(result["runtime_seconds"], 0)
        self.assertGreater(result["circuit_depth"], 0)
        self.assertGreater(result["final_shots"], 0)


if __name__ == "__main__":
    unittest.main()
