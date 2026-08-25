"""Use relational document and evaluation facts in workspace responses."""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0005"
down_revision: str | None = "20260824_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FACTS_KEY = "relationalFactsVersion"
FACTS_VERSION = 1


def upgrade() -> None:
    connection = op.get_bind()
    tables = _Tables()
    for row in connection.execute(
        sa.select(tables.test_runs.c.id, tables.test_runs.c.state)
    ).mappings():
        state = row["state"]
        if not isinstance(state, dict):
            continue
        documents = _documents(connection, tables.documents, row["id"])
        records = _records(connection, tables.records, row["id"])
        if not _has_complete_relational_facts(state, documents, records):
            continue
        persisted = dict(state)
        persisted.pop("manual", None)
        persisted.pop("manualUpload", None)
        persisted.pop("evaluation", None)
        persisted[FACTS_KEY] = FACTS_VERSION
        connection.execute(
            tables.test_runs.update()
            .where(tables.test_runs.c.id == row["id"])
            .values(state=persisted)
        )


def downgrade() -> None:
    connection = op.get_bind()
    tables = _Tables()
    for row in connection.execute(
        sa.select(tables.test_runs.c.id, tables.test_runs.c.state)
    ).mappings():
        state = row["state"]
        if not isinstance(state, dict) or state.get(FACTS_KEY) != FACTS_VERSION:
            continue
        persisted = dict(state)
        persisted.pop(FACTS_KEY, None)
        documents = _documents(connection, tables.documents, row["id"])
        records = _records(connection, tables.records, row["id"])
        persisted["manual"] = _manual(documents.get("active"))
        persisted["manualUpload"] = _manual_upload(documents.get("pending"))
        persisted["evaluation"] = _evaluation(persisted, records)
        connection.execute(
            tables.test_runs.update()
            .where(tables.test_runs.c.id == row["id"])
            .values(state=persisted)
        )


class _Tables:
    def __init__(self) -> None:
        self.test_runs = sa.table(
            "test_runs", sa.column("id", sa.String()), sa.column("state", sa.JSON())
        )
        self.documents = sa.table(
            "documents",
            sa.column("id", sa.String()),
            sa.column("test_run_id", sa.String()),
            sa.column("role", sa.String()),
            sa.column("filename", sa.String()),
            sa.column("status", sa.String()),
            sa.column("page_count", sa.Integer()),
        )
        self.records = sa.table(
            "question_evaluation_records",
            sa.column("test_run_id", sa.String()),
            sa.column("question_id", sa.String()),
            sa.column("question_set_id", sa.String()),
            sa.column("manual_id", sa.String()),
            sa.column("status", sa.String()),
            sa.column("error", sa.String()),
        )
def _documents(
    connection: sa.Connection, documents: sa.TableClause, test_id: str
) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        sa.select(documents).where(
            documents.c.test_run_id == test_id,
            documents.c.role.in_(("active", "pending")),
        )
    ).mappings()
    return {row["role"]: dict(row) for row in rows}


def _records(
    connection: sa.Connection, records: sa.TableClause, test_id: str
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in connection.execute(
            sa.select(records).where(records.c.test_run_id == test_id)
        ).mappings()
    ]


def _has_complete_relational_facts(
    state: dict[str, Any],
    documents: dict[str, dict[str, Any]],
    records: list[dict[str, Any]],
) -> bool:
    manual = state.get("manual")
    active = documents.get("active")
    if isinstance(manual, dict) != (active is not None):
        return False
    if isinstance(manual, dict) and active is not None and active["id"] != manual.get("id"):
        return False
    upload = state.get("manualUpload")
    pending = documents.get("pending")
    if isinstance(upload, dict) != (pending is not None):
        return False
    if isinstance(upload, dict) and pending is not None and pending["id"] != upload.get("id"):
        return False
    evaluation = state.get("evaluation", [])
    if isinstance(evaluation, list):
        state_question_ids = {
            item.get("questionId") for item in evaluation if isinstance(item, dict)
        }
        source = state.get("evaluationSource")
        record_question_ids = {
            record["question_id"]
            for record in records
            if isinstance(source, dict)
            and record["question_set_id"] == source.get("questionSetId")
            and record["manual_id"] == source.get("manualId")
        }
        if state_question_ids != record_question_ids:
            return False
    return True


def _manual(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    return {
        "id": document["id"],
        "filename": document["filename"],
        "pageCount": document["page_count"],
        "status": document["status"],
    }


def _manual_upload(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    return {
        "id": document["id"],
        "filename": document["filename"],
        "status": document["status"],
    }


def _evaluation(
    state: dict[str, Any], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    source = state.get("evaluationSource")
    question_set = state.get("questionSet")
    if not isinstance(source, dict) or not isinstance(question_set, dict):
        return []
    matching = {
        record["question_id"]: record
        for record in records
        if record["question_set_id"] == source.get("questionSetId")
        and record["manual_id"] == source.get("manualId")
    }
    return [
        {
            "questionId": record["question_id"],
            "status": record["status"],
            "error": record["error"],
        }
        for item in question_set.get("items", [])
        if isinstance(item, dict)
        and (record := matching.get(item.get("id"))) is not None
    ]
