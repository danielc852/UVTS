import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from uvts_api.core.config import get_settings


def _alembic_config(database_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    # Alembic's environment reads the application settings, so point it at an
    # isolated database before importing each migration revision.
    monkeypatch.setenv("UVTS_DATABASE_URL", f"sqlite+aiosqlite:///{database_path}")
    get_settings.cache_clear()
    config = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    config.set_main_option(
        "script_location", str(Path(__file__).parents[2] / "migrations")
    )
    return config


def test_manual_independent_migration_upgrades_state_and_evaluation_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "migration.db"
    config = _alembic_config(database_path, monkeypatch)
    command.upgrade(config, "20260824_0003")

    now = datetime.now(UTC).isoformat()
    legacy_state = {
        "currentStage": "report",
        "manual": {
            "id": "manual-1",
            "filename": "legacy.pdf",
            "pageCount": 1,
            "status": "ready",
        },
        "configuration": {
            "totalQuestions": 1,
            "productDescription": "A retained legacy product description.",
            "topics": ["Setup"],
        },
        "questions": [
            {
                "id": "q1",
                "text": "How do I begin?",
                "type": "Basic",
                "topic": "Setup",
                "viewpoint": "Beginner",
            }
        ],
        "evaluation": [{"questionId": "q1", "status": "complete", "error": None}],
        "report": {
            "isComplete": True,
            "counts": {"found": 0, "partly_found": 0, "not_found": 1, "failed": 0},
            "results": [],
            "gaps": [],
            "recommendations": [],
            "followUpQuestions": [],
        },
        "error": None,
    }
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO anonymous_sessions "
            "(id, token_hash, created_at, last_seen_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            ("owner-1", "token", now, now, now),
        )
        connection.execute(
            "INSERT INTO test_runs "
            "(id, owner_session_id, status, state_version, state, active_operation_id, "
            "agent_settings, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "test-1",
                "owner-1",
                "complete",
                1,
                json.dumps(legacy_state),
                None,
                "{}",
                now,
                now,
            ),
        )
        connection.execute(
            "INSERT INTO question_evaluation_records "
            "(id, test_run_id, question_id, status, result, error, attempt, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("record-1", "test-1", "q1", "complete", "{}", None, 1, now, now),
        )
        connection.commit()

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        stored_state = json.loads(
            connection.execute(
                "SELECT state FROM test_runs WHERE id = 'test-1'"
            ).fetchone()[0]
        )
        source_ids = connection.execute(
            "SELECT question_set_id, manual_id FROM question_evaluation_records "
            "WHERE id = 'record-1'"
        ).fetchone()

    question_set = stored_state["questionSet"]
    assert stored_state["schemaVersion"] == 2
    assert stored_state["currentStage"] == "report"
    assert stored_state["configuration"]["version"] == 1
    assert "topics" not in stored_state["configuration"]
    assert question_set["status"] == "confirmed"
    assert question_set["source"] == "legacy_manual_unknown"
    assert question_set["items"] == [{"id": "q1", "text": "How do I begin?"}]
    assert stored_state["evaluationSource"] == {
        "questionSetId": question_set["id"],
        "manualId": "manual-1",
    }
    assert stored_state["report"]["source"] == stored_state["evaluationSource"]
    assert source_ids == (question_set["id"], "manual-1")

    get_settings.cache_clear()
