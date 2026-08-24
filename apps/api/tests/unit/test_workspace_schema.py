from typing import Any

import pytest
from pydantic import ValidationError

from uvts_api.schemas.workspace import (
    EvaluationSource,
    QuestionSet,
    QuestionSetSource,
    QuestionSetStatus,
    WorkspaceState,
    upgrade_workspace_state,
)
from uvts_api.schemas.workspace import TestConfiguration as WorkspaceConfiguration


def test_workspace_defaults_begin_at_product_configuration() -> None:
    body = WorkspaceState().model_dump(mode="json", by_alias=True, exclude_none=True)

    assert body["schemaVersion"] == 2
    assert body["currentStage"] == "configuration"
    assert body["configuration"] == {
        "version": 0,
        "totalQuestions": 9,
        "productDescription": "",
    }
    assert "questionSet" not in body
    assert body["evaluation"] == []


def test_upgrader_preserves_legacy_question_text_but_removes_obsolete_metadata() -> None:
    upgraded = upgrade_workspace_state(
        {
            "currentStage": "questions",
            "configuration": {
                "totalQuestions": 1,
                "productDescription": "A portable sensor",
                "typeCounts": {"basic": 1, "crossParagraph": 0, "edgeCase": 0},
                "topics": ["Setup"],
                "viewpoints": ["Beginner"],
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
            "evaluation": [],
        },
    )
    state = WorkspaceState.model_validate(upgraded)

    assert state.schema_version == 2
    assert state.configuration.version == 1
    assert state.question_set is not None
    assert state.question_set.source == QuestionSetSource.LEGACY_MANUAL
    assert state.question_set.status == QuestionSetStatus.DRAFT
    assert state.question_set.items[0].model_dump() == {
        "id": "q1",
        "text": "How do I begin?",
    }


def test_upgrader_moves_an_empty_upload_draft_to_configuration() -> None:
    upgraded = upgrade_workspace_state(
        {"currentStage": "upload", "configuration": {}, "evaluation": []},
    )
    assert upgraded["currentStage"] == "configuration"


def test_v2_explicit_null_lineage_is_not_recreated_from_old_manual_data() -> None:
    upgraded = upgrade_workspace_state(
        {
            "schemaVersion": 2,
            "currentStage": "evaluation",
            "manual": {
                "id": "new-manual",
                "filename": "replacement.pdf",
                "pageCount": 1,
                "status": "ready",
            },
            "questionSet": {
                "id": "confirmed-set",
                "status": "confirmed",
                "source": "legacy_manual_unknown",
                "configurationVersion": None,
                "confirmedAt": "2026-08-25T00:00:00Z",
                "items": [{"id": "q1", "text": "How do I start?"}],
            },
            "evaluationSource": None,
            "evaluation": [],
            "report": None,
        }
    )

    assert upgraded["evaluationSource"] is None
    assert WorkspaceState.model_validate(upgraded).evaluation_source is None


def test_workspace_rejects_arbitrary_state() -> None:
    with pytest.raises(ValidationError):
        WorkspaceState.model_validate({"progress": 2})


@pytest.mark.parametrize("count", [0, 16])
def test_configuration_rejects_question_counts_outside_supported_range(count: int) -> None:
    with pytest.raises(ValidationError):
        WorkspaceConfiguration(total_questions=count)


def test_confirmed_question_set_requires_a_confirmation_time() -> None:
    with pytest.raises(ValidationError):
        QuestionSet(
            id="set-1",
            status=QuestionSetStatus.CONFIRMED,
            source=QuestionSetSource.PRODUCT_CONTEXT,
            configuration_version=1,
            items=[{"id": "q1", "text": "How do I start?"}],
        )


def test_upgrader_is_idempotent_and_uses_a_stable_legacy_set_id() -> None:
    legacy = {
        "currentStage": "questions",
        "configuration": {"totalQuestions": 1},
        "questions": [{"text": "  How do I start?  ", "id": "q1"}],
    }

    first = upgrade_workspace_state(legacy)
    second = upgrade_workspace_state(first)

    assert second == first
    assert first["questionSet"]["id"] == second["questionSet"]["id"]
    assert WorkspaceState.model_validate(first).questions[0].text == "How do I start?"


def test_workspace_rejects_an_unknown_schema_version() -> None:
    with pytest.raises(ValidationError):
        WorkspaceState.model_validate({"schemaVersion": 3})


def test_product_draft_may_be_stale_but_a_confirmed_set_must_match_setup() -> None:
    stale_draft: dict[str, Any] = {
        "schemaVersion": 2,
        "currentStage": "questions",
        "configuration": {
            "version": 2,
            "totalQuestions": 2,
            "productImage": {
                "id": "image-1",
                "filename": "product.png",
                "contentType": "image/png",
                "sizeBytes": 10,
            },
            "productDescription": "A sensor",
        },
        "questionSet": {
            "id": "set-1",
            "status": "draft",
            "source": "product_context_v1",
            "configurationVersion": 1,
            "items": [{"id": "q1", "text": "How is it set up?"}],
        },
    }
    assert WorkspaceState.model_validate(stale_draft).question_set is not None

    stale_draft["questionSet"].update(
        {"status": "confirmed", "confirmedAt": "2026-08-25T00:00:00Z"}
    )
    with pytest.raises(ValidationError, match="saved Product setup version"):
        WorkspaceState.model_validate(stale_draft)


def test_evaluation_lineage_must_match_confirmed_questions_and_ready_manual() -> None:
    valid: dict[str, Any] = {
        "schemaVersion": 2,
        "currentStage": "evaluation",
        "manual": {
            "id": "manual-1",
            "filename": "manual.pdf",
            "pageCount": 1,
            "status": "ready",
        },
        "questionSet": {
            "id": "set-1",
            "status": "confirmed",
            "source": "legacy_manual_unknown",
            "configurationVersion": None,
            "confirmedAt": "2026-08-25T00:00:00Z",
            "items": [{"id": "q1", "text": "How is it set up?"}],
        },
        "evaluationSource": EvaluationSource(
            question_set_id="set-1", manual_id="manual-1"
        ).model_dump(mode="json", by_alias=True),
        "evaluation": [{"questionId": "q1", "status": "waiting"}],
    }
    assert WorkspaceState.model_validate(valid).evaluation_source is not None

    valid["evaluationSource"]["manualId"] = "different-manual"
    with pytest.raises(ValidationError, match="current ready manual"):
        WorkspaceState.model_validate(valid)
