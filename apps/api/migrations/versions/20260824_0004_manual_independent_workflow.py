"""Version workspace state and bind evaluation records to their sources."""

import json
from collections.abc import Sequence
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "20260824_0004"
down_revision: str | None = "20260824_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _legacy_question_set(
    raw: dict[str, Any], configuration_version: int
) -> dict[str, Any] | None:
    questions = raw.pop("questions", None)
    if not isinstance(questions, list) or not questions:
        return None
    normalized_questions = [
        {"id": item.get("id"), "text": item.get("text")}
        if isinstance(item, dict)
        else item
        for item in questions
    ]
    digest = sha256(
        json.dumps(
            normalized_questions,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    stage = raw.get("currentStage", raw.get("current_stage"))
    confirmed = stage in {"evaluation", "report"}
    return {
        "id": str(uuid5(NAMESPACE_URL, f"uvts-legacy-question-set:{digest}")),
        "status": "confirmed" if confirmed else "draft",
        "source": "legacy_manual_unknown",
        "configurationVersion": configuration_version,
        "generatedAt": None,
        "confirmedAt": "1970-01-01T00:00:00Z" if confirmed else None,
        "items": normalized_questions,
    }


def _upgrade_workspace_state(value: Any) -> Any:
    """Frozen v1-to-v2 transform; migrations must not depend on live app schemas."""

    if not isinstance(value, dict):
        return value
    raw = dict(value)
    declared_version = raw.get("schemaVersion", raw.get("schema_version"))
    if declared_version not in {None, 1, 2}:
        return raw
    is_legacy = declared_version in {None, 1}

    configuration = dict(raw.get("configuration") or {})
    for field in ("typeCounts", "type_counts", "topics", "viewpoints"):
        configuration.pop(field, None)
    has_saved_setup = bool(
        configuration.get("productImage", configuration.get("product_image"))
        or str(
            configuration.get(
                "productDescription", configuration.get("product_description", "")
            )
        ).strip()
    )
    configuration["version"] = int(
        configuration.get("version") or (1 if has_saved_setup else 0)
    )
    raw["configuration"] = configuration

    question_set = raw.get("questionSet", raw.get("question_set"))
    if question_set is None:
        question_set = _legacy_question_set(raw, configuration["version"])
    else:
        raw.pop("questions", None)
        if isinstance(question_set, dict) and isinstance(question_set.get("items"), list):
            question_set = dict(question_set)
            question_set["items"] = [
                {"id": item.get("id"), "text": item.get("text")}
                if isinstance(item, dict)
                else item
                for item in question_set["items"]
            ]
    raw["questionSet"] = question_set

    stage = raw.get("currentStage", raw.get("current_stage", "configuration"))
    if stage == "upload" and question_set is None:
        stage = "configuration"
    raw["currentStage"] = stage

    snake_evaluation_source = raw.pop("evaluation_source", None)
    if "evaluationSource" not in raw and snake_evaluation_source is not None:
        raw["evaluationSource"] = snake_evaluation_source
    evaluation_source = raw.get("evaluationSource")
    manual = raw.get("manual")
    if is_legacy and evaluation_source is None and question_set and isinstance(manual, dict):
        if stage in {"evaluation", "report"} and manual.get("id"):
            raw["evaluationSource"] = {
                "questionSetId": question_set["id"],
                "manualId": manual["id"],
            }
    report = raw.get("report")
    if (
        is_legacy
        and isinstance(report, dict)
        and report.get("source") is None
        and raw.get("evaluationSource")
    ):
        raw["report"] = {**report, "source": raw["evaluationSource"]}

    raw["schemaVersion"] = 2
    raw.pop("schema_version", None)
    raw.pop("current_stage", None)
    raw.pop("question_set", None)
    manual_upload = raw.pop("manual_upload", None)
    if "manualUpload" not in raw and manual_upload is not None:
        raw["manualUpload"] = manual_upload
    return raw


def upgrade() -> None:
    op.add_column(
        "question_evaluation_records",
        sa.Column("question_set_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "question_evaluation_records",
        sa.Column("manual_id", sa.String(length=36), nullable=True),
    )

    connection = op.get_bind()
    test_runs = sa.table(
        "test_runs",
        sa.column("id", sa.String()),
        sa.column("state", sa.JSON()),
    )
    records = sa.table(
        "question_evaluation_records",
        sa.column("test_run_id", sa.String()),
        sa.column("question_set_id", sa.String()),
        sa.column("manual_id", sa.String()),
    )
    for row in connection.execute(sa.select(test_runs.c.id, test_runs.c.state)).mappings():
        upgraded = _upgrade_workspace_state(row["state"])
        connection.execute(
            test_runs.update().where(test_runs.c.id == row["id"]).values(state=upgraded)
        )
        source = upgraded.get("evaluationSource") if isinstance(upgraded, dict) else None
        if isinstance(source, dict):
            connection.execute(
                records.update()
                .where(records.c.test_run_id == row["id"])
                .values(
                    question_set_id=source.get("questionSetId"),
                    manual_id=source.get("manualId"),
                )
            )


def downgrade() -> None:
    op.drop_column("question_evaluation_records", "manual_id")
    op.drop_column("question_evaluation_records", "question_set_id")
