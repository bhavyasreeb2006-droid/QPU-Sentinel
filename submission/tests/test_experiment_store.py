import tempfile
import unittest
from pathlib import Path

from src.experiment_store import ExperimentStore


class ExperimentStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary_directory.name) / "experiments.sqlite3"
        self.store = ExperimentStore(self.database)
        self.specification = {
            "asset_count": 3,
            "cardinality": 1,
            "seed": 42,
            "algorithms": ["greedy"],
        }

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_completed_experiment_persists_specification_and_result(self):
        experiment_id = self.store.create_job(self.specification)
        self.store.update_status(experiment_id, "running")
        result = {"dataset_id": "dataset-1", "runs": [{"selection": "100"}]}
        self.store.complete(experiment_id, result)

        reopened = ExperimentStore(self.database)
        record = reopened.get(experiment_id)
        self.assertEqual(record["status"], "completed")
        self.assertEqual(record["specification"], self.specification)
        self.assertEqual(record["result"], result)
        self.assertEqual(reopened.list()[0]["experiment_id"], experiment_id)

    def test_failed_experiment_is_persisted_without_a_success_result(self):
        experiment_id = self.store.create_job(self.specification)
        self.store.update_status(experiment_id, "running")
        self.store.fail(experiment_id, "simulator failure")

        record = self.store.get(experiment_id)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["error"], "simulator failure")
        self.assertNotIn("result", record)

    def test_pagination_validation(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            self.store.list(limit=0)
        with self.assertRaisesRegex(ValueError, "offset"):
            self.store.list(offset=-1)


if __name__ == "__main__":
    unittest.main()
