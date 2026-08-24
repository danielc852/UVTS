import pytest
from pydantic import ValidationError

from uvts_api.schemas.tests import TestCreateRequest as WorkspaceCreateRequest
from uvts_api.schemas.workspace import TestConfiguration as QuestionConfiguration
from uvts_api.schemas.workspace import WorkspaceState


def test_workspace_defaults_match_browser_foundation() -> None:
    workspace = WorkspaceCreateRequest()

    body = workspace.model_dump(mode="json", by_alias=True)
    assert body["currentStage"] == "upload"
    assert body["configuration"]["totalQuestions"] == 9
    assert body["configuration"]["typeCounts"] == {
        "basic": 3,
        "crossParagraph": 3,
        "edgeCase": 3,
    }
    assert body["questions"] == []
    assert body["evaluation"] == []


def test_workspace_rejects_arbitrary_state() -> None:
    with pytest.raises(ValidationError):
        WorkspaceState.model_validate({"progress": 2})


@pytest.mark.parametrize(
    "payload",
    [
        {
            "totalQuestions": 3,
            "typeCounts": {"basic": 1, "crossParagraph": 1, "edgeCase": 0},
        },
        {
            "totalQuestions": 1,
            "typeCounts": {"basic": 0, "crossParagraph": 0, "edgeCase": 0},
        },
    ],
)
def test_configuration_rejects_an_invalid_type_split(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        QuestionConfiguration.model_validate(payload)
