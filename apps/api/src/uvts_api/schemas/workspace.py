from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class WorkflowStage(StrEnum):
    UPLOAD = "upload"
    CONFIGURATION = "configuration"
    QUESTIONS = "questions"
    EVALUATION = "evaluation"
    REPORT = "report"


class CoverageStatus(StrEnum):
    FOUND = "found"
    PARTLY_FOUND = "partly_found"
    NOT_FOUND = "not_found"
    FAILED = "failed"


class EvaluationStatus(StrEnum):
    WAITING = "waiting"
    CHECKING = "checking"
    COMPLETE = "complete"
    FAILED = "failed"


class ManualStatus(StrEnum):
    CHECKING = "checking"
    READY = "ready"
    INVALID = "invalid"


class QuestionType(StrEnum):
    BASIC = "Basic"
    CROSS_PARAGRAPH = "Cross-paragraph"
    EDGE_CASE = "Edge-case"


class Viewpoint(StrEnum):
    BEGINNER = "Beginner"
    REGULAR_USER = "Regular user"
    ADVANCED_USER = "Advanced user"


class GapKind(StrEnum):
    MISSING = "missing"
    INCOMPLETE = "incomplete"


class RecommendationPriority(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ManualSummary(ApiModel):
    id: str
    filename: str
    page_count: int = Field(alias="pageCount", ge=1, le=20)
    status: ManualStatus


class QuestionTypeCounts(ApiModel):
    basic: int = Field(ge=0, le=15)
    cross_paragraph: int = Field(alias="crossParagraph", ge=0, le=15)
    edge_case: int = Field(alias="edgeCase", ge=0, le=15)


def default_type_counts() -> QuestionTypeCounts:
    return QuestionTypeCounts(basic=3, cross_paragraph=3, edge_case=3)


def default_topics() -> list[str]:
    return [
        "Setup and requirements",
        "Main product tasks",
        "Settings and customization",
        "Troubleshooting and recovery",
        "Limits and unusual situations",
        "Safety, privacy, and data handling",
    ]


def default_viewpoints() -> list[str]:
    return [viewpoint.value for viewpoint in Viewpoint]


class TestConfiguration(ApiModel):
    total_questions: int = Field(default=9, alias="totalQuestions", ge=1, le=15)
    type_counts: QuestionTypeCounts = Field(default_factory=default_type_counts, alias="typeCounts")
    topics: list[str] = Field(default_factory=default_topics, min_length=1)
    viewpoints: list[str] = Field(default_factory=default_viewpoints, min_length=1)


class Question(ApiModel):
    id: str
    text: str
    type: QuestionType
    topic: str
    viewpoint: Viewpoint


class EvaluationItem(ApiModel):
    question_id: str = Field(alias="questionId")
    status: EvaluationStatus
    error: str | None = None


class Evidence(ApiModel):
    page: int = Field(ge=1)
    extract: str


class QuestionResult(ApiModel):
    question: Question
    status: CoverageStatus
    information_needed: str = Field(alias="informationNeeded")
    information_found: str | None = Field(default=None, alias="informationFound")
    information_missing: str | None = Field(default=None, alias="informationMissing")
    evidence: list[Evidence] = Field(default_factory=list)


class Gap(ApiModel):
    id: str
    title: str
    why_it_matters: str = Field(alias="whyItMatters")
    affected_question_ids: list[str] = Field(alias="affectedQuestionIds")
    kind: GapKind


class Recommendation(ApiModel):
    id: str
    priority: RecommendationPriority
    change: str
    reason: str
    gap_id: str = Field(alias="gapId")


class CoverageCounts(ApiModel):
    found: int = Field(ge=0)
    partly_found: int = Field(alias="partly_found", ge=0)
    not_found: int = Field(alias="not_found", ge=0)
    failed: int = Field(ge=0)


class Report(ApiModel):
    is_complete: bool = Field(alias="isComplete")
    counts: CoverageCounts
    results: list[QuestionResult]
    gaps: list[Gap]
    recommendations: list[Recommendation]
    follow_up_questions: list[str] = Field(alias="followUpQuestions")


class WorkspaceError(ApiModel):
    title: str
    message: str
    stage: WorkflowStage


class WorkspaceState(ApiModel):
    current_stage: WorkflowStage = Field(alias="currentStage")
    manual: ManualSummary | None = None
    configuration: TestConfiguration
    questions: list[Question]
    evaluation: list[EvaluationItem]
    report: Report | None = None
    error: WorkspaceError | None = None


class TestWorkspace(WorkspaceState):
    id: str
