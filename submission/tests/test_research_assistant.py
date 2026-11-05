import os
import unittest
from unittest.mock import patch

from src.research_assistant import (
    answer_experiment_question,
    build_experiment_context,
    configured_provider,
)


class FakeProvider:
    def __init__(self):
        self.question = None
        self.context = None

    def status(self):
        return {"configured": True, "provider": "test fixture"}

    def answer(self, question, context):
        self.question = question
        self.context = context
        return "Exact result cited from [exact_reference.objective]."


class ResearchAssistantTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "experiment_id": "exp-123",
            "status": "completed",
            "asset_count": 3,
            "cardinality": 1,
            "seed": 2026,
            "result": {
                "dataset_id": "dataset-abc",
                "instance": {
                    "covariance_structure": "mixed",
                    "risk_aversion": 1.0,
                    "penalty": 1.0,
                    "covariance": [[0.1]],
                },
                "exact_reference": {"selection": "100", "objective": -0.1},
                "penalty_diagnostic": {"certified_sufficient": True},
                "qubo_validation": {"checked_configurations": 8, "exhaustive": True},
                "algorithm_configuration": {"algorithms": ["exact", "qaoa"]},
                "summaries": [{"algorithm": "qaoa", "feasibility_rate": 0.75}],
                "runs": [
                    {
                        "algorithm": "qaoa",
                        "selection": "100",
                        "objective": -0.1,
                        "sample_counts": {"100": 3},
                    }
                ],
            },
        }

    def test_context_is_bounded_to_selected_record_and_omits_raw_covariance(self):
        context = build_experiment_context(self.record)

        self.assertEqual(context["experiment_id"], "exp-123")
        self.assertEqual(context["exact_reference"]["selection"], "100")
        self.assertNotIn("covariance", context["instance"])
        self.assertNotIn("sample_counts", context["runs"][0])

    def test_provider_only_receives_context_after_explicit_consent(self):
        provider = FakeProvider()
        answer = answer_experiment_question(
            self.record,
            "Compare QAOA with exact search.",
            provider,
            external_data_consent=True,
        )

        self.assertIn("[exact_reference.objective]", answer["answer"])
        self.assertEqual(provider.context["dataset_id"], "dataset-abc")
        self.assertEqual(provider.question, "Compare QAOA with exact search.")
        self.assertEqual(answer["experiment_id"], "exp-123")

    def test_consent_and_question_validation(self):
        provider = FakeProvider()
        with self.assertRaisesRegex(ValueError, "consent"):
            answer_experiment_question(
                self.record, "Explain", provider, external_data_consent=False
            )
        with self.assertRaisesRegex(ValueError, "empty"):
            answer_experiment_question(
                self.record, "  ", provider, external_data_consent=True
            )
        with self.assertRaisesRegex(ValueError, "2,000"):
            answer_experiment_question(
                self.record, "x" * 2001, provider, external_data_consent=True
            )

    def test_unconfigured_provider_does_not_fabricate_an_answer(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(configured_provider())


if __name__ == "__main__":
    unittest.main()
