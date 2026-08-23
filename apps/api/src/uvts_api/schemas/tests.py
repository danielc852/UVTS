from datetime import datetime

from pydantic import Field

from uvts_api.domain.enums import TestStatus
from uvts_api.schemas.workspace import (
    EvaluationItem,
    Question,
    TestConfiguration,
    TestWorkspace,
    WorkflowStage,
    WorkspaceState,
)


class TestCreateRequest(WorkspaceState):
    current_stage: WorkflowStage = Field(default=WorkflowStage.UPLOAD, alias="currentStage")
    configuration: TestConfiguration = Field(default_factory=TestConfiguration)
    questions: list[Question] = Field(default_factory=list)
    evaluation: list[EvaluationItem] = Field(default_factory=list)


class TestResponse(TestWorkspace):
    status: TestStatus
    state_version: int = Field(alias="stateVersion", ge=1)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
