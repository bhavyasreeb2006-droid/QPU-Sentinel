"""SQLite persistence for reproducible experiment specifications and results."""

from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from collections.abc import Generator
from typing import Any
import uuid


DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / "results" / "experiments.sqlite3"


class ExperimentStore:
    def __init__(self, database: str | Path = DEFAULT_DATABASE) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('queued', 'running', 'completed', 'failed')
                    ),
                    dataset_id TEXT,
                    asset_count INTEGER NOT NULL,
                    cardinality INTEGER NOT NULL,
                    seed INTEGER NOT NULL,
                    specification_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS experiments_created_at_idx
                ON experiments(created_at DESC)
                """
            )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _record(row: sqlite3.Row, include_result: bool) -> dict[str, Any]:
        record: dict[str, Any] = {
            "experiment_id": row["experiment_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "status": row["status"],
            "dataset_id": row["dataset_id"],
            "asset_count": row["asset_count"],
            "cardinality": row["cardinality"],
            "seed": row["seed"],
            "specification": json.loads(row["specification_json"]),
            "error": row["error"],
        }
        if include_result and row["result_json"] is not None:
            record["result"] = json.loads(row["result_json"])
        return record

    def create_job(self, specification: dict[str, Any]) -> str:
        experiment_id = uuid.uuid4().hex
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO experiments (
                    experiment_id, created_at, updated_at, status, asset_count,
                    cardinality, seed, specification_json
                ) VALUES (?, ?, ?, 'queued', ?, ?, ?, ?)
                """,
                (
                    experiment_id,
                    now,
                    now,
                    specification["asset_count"],
                    specification["cardinality"],
                    specification["seed"],
                    json.dumps(specification, sort_keys=True, allow_nan=False),
                ),
            )
        return experiment_id

    def update_status(self, experiment_id: str, status: str) -> None:
        if status not in {"running", "failed"}:
            raise ValueError(f"Unsupported experiment status: {status}.")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE experiments SET status = ?, updated_at = ?
                WHERE experiment_id = ? AND status IN ('queued', 'running')
                """,
                (status, self._now(), experiment_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Experiment {experiment_id} is not in an active state.")

    def complete(self, experiment_id: str, result: dict[str, Any]) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE experiments
                SET status = 'completed', updated_at = ?, dataset_id = ?,
                    result_json = ?, error = NULL
                WHERE experiment_id = ? AND status = 'running'
                """,
                (
                    self._now(),
                    result["dataset_id"],
                    json.dumps(result, sort_keys=True, allow_nan=False),
                    experiment_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Experiment {experiment_id} is not running.")

    def fail(self, experiment_id: str, error: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE experiments SET status = 'failed', updated_at = ?, error = ?
                WHERE experiment_id = ? AND status IN ('queued', 'running')
                """,
                (self._now(), error, experiment_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Experiment {experiment_id} is not in an active state.")

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM experiments WHERE experiment_id = ?",
                (experiment_id,),
            ).fetchone()
        return self._record(row, include_result=True) if row is not None else None

    def list(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer from 1 to 100.")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer.")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM experiments
                ORDER BY created_at DESC, experiment_id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._record(row, include_result=False) for row in rows]
