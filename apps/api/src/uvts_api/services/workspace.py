from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from uvts_api.adapters.db.models import Document, QuestionEvaluationRecord, TestRun
from uvts_api.core.errors import AppError
from uvts_api.schemas.workspace import WorkspaceState, upgrade_workspace_state

RELATIONAL_FACTS_VERSION = 1
RELATIONAL_FACTS_KEY = "relationalFactsVersion"


def new_workspace_state() -> dict[str, Any]:
    state = WorkspaceState().model_dump(mode="json", by_alias=True)
    state[RELATIONAL_FACTS_KEY] = RELATIONAL_FACTS_VERSION
    return state


async def load_workspace_state(db: AsyncSession, test: TestRun) -> WorkspaceState:
    """Build the public workspace from durable facts, with a legacy JSON fallback."""

    facts_version = test.state.get(RELATIONAL_FACTS_KEY)
    raw = upgrade_workspace_state(test.state)
    if not isinstance(raw, dict):
        return _validate_workspace(raw)

    persisted = dict(raw)
    if facts_version != RELATIONAL_FACTS_VERSION:
        return _validate_workspace(persisted)

    question_set = persisted.get("questionSet")
    questions_confirmed = (
        isinstance(question_set, dict) and question_set.get("status") == "confirmed"
    )
    documents: list[Document] = []
    if questions_confirmed:
        documents = list(
            (
                await db.scalars(
                    select(Document).where(
                        Document.test_run_id == test.id,
                        Document.role.in_(("active", "pending")),
                    )
                )
            ).all()
        )
    documents_by_role = {document.role: document for document in documents}
    active = documents_by_role.get("active")
    pending = documents_by_role.get("pending")
    persisted["manual"] = (
        {
            "id": active.id,
            "filename": active.filename,
            "pageCount": active.page_count,
            "status": active.status,
        }
        if active is not None
        else None
    )
    persisted["manualUpload"] = (
        {
            "id": pending.id,
            "filename": pending.filename,
            "status": pending.status,
        }
        if pending is not None
        else None
    )

    source = persisted.get("evaluationSource")
    persisted["evaluation"] = []
    if isinstance(source, dict):
        records = list(
            (
                await db.scalars(
                    select(QuestionEvaluationRecord).where(
                        QuestionEvaluationRecord.test_run_id == test.id,
                        QuestionEvaluationRecord.question_set_id
                        == source.get("questionSetId"),
                        QuestionEvaluationRecord.manual_id == source.get("manualId"),
                    )
                )
            ).all()
        )
        records_by_question = {record.question_id: record for record in records}
        items = question_set.get("items", []) if isinstance(question_set, dict) else []
        evaluation: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            question_id = item.get("id")
            if not isinstance(question_id, str):
                continue
            record = records_by_question.get(question_id)
            if record is not None:
                evaluation.append(
                    {
                        "questionId": record.question_id,
                        "status": record.status,
                        "error": record.error,
                    }
                )
        persisted["evaluation"] = evaluation

    return _validate_workspace(persisted)


def update_state(test: TestRun, state: WorkspaceState) -> None:
    persisted = state.model_dump(mode="json", by_alias=True)
    if test.state.get(RELATIONAL_FACTS_KEY) == RELATIONAL_FACTS_VERSION:
        persisted.pop("manual", None)
        persisted.pop("manualUpload", None)
        persisted.pop("evaluation", None)
        persisted[RELATIONAL_FACTS_KEY] = RELATIONAL_FACTS_VERSION
    test.state = persisted
    test.state_version += 1


def _validate_workspace(value: Any) -> WorkspaceState:
    try:
        return WorkspaceState.model_validate(value)
    except ValidationError as exc:
        raise AppError(
            status_code=409,
            code="workspace_state_incompatible",
            message="This saved test cannot be opened safely. Contact support before changing it.",
        ) from exc
