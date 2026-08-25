from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any, Literal, Self
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class WorkflowStage(StrEnum):
    CONFIGURATION = "configuration"
    QUESTIONS = "questions"
    UPLOAD = "upload"
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


class ManualUploadStatus(StrEnum):
    CHECKING = "checking"
    PROCESSING = "processing"


# Accepted legacy vocabulary. New question sets contain only ID and text.
class QuestionType(StrEnum):
    BASIC = "Basic"
    CROSS_PARAGRAPH = "Cross-paragraph"
    EDGE_CASE = "Edge-case"


class Viewpoint(StrEnum):
    BEGINNER = "Beginner"
    REGULAR_USER = "Regular user"
    ADVANCED_USER = "Advanced user"


class QuestionSetStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"


class QuestionSetSource(StrEnum):
    PRODUCT_CONTEXT = "product_context_v1"
    LEGACY_MANUAL = "legacy_manual_unknown"


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


class ManualUpload(ApiModel):
    id: str
    filename: str
    status: ManualUploadStatus


class ProductImageSummary(ApiModel):
    id: str
    filename: str
    content_type: str = Field(alias="contentType", pattern=r"^image/")
    size_bytes: int = Field(alias="sizeBytes", ge=1, le=10 * 1024 * 1024)


class TestConfiguration(ApiModel):
    version: int = Field(default=0, ge=0)
    total_questions: int = Field(default=9, alias="totalQuestions", ge=1, le=15)
    product_image: ProductImageSummary | None = Field(default=None, alias="productImage")
    product_description: str = Field(default="", alias="productDescription")

    @model_validator(mode="before")
    @classmethod
    def discard_deferred_legacy_fields(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = dict(value)
            for field in ("typeCounts", "type_counts", "topics", "viewpoints"):
                value.pop(field, None)
        return value


class Question(ApiModel):
    id: str
    text: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_metadata(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = dict(value)
            for field in ("type", "topic", "viewpoint"):
                value.pop(field, None)
        return value

    @model_validator(mode="after")
    def normalize_text(self) -> Self:
        text = self.text.strip()
        if not text:
            raise ValueError("Question text must not be blank.")
        self.text = text
        return self


class QuestionSet(ApiModel):
    id: str
    status: QuestionSetStatus
    source: QuestionSetSource
    configuration_version: int | None = Field(default=None, alias="configurationVersion")
    generated_at: datetime | None = Field(default=None, alias="generatedAt")
    confirmed_at: datetime | None = Field(default=None, alias="confirmedAt")
    items: list[Question] = Field(min_length=1, max_length=15)

    @model_validator(mode="after")
    def validate_confirmation(self) -> Self:
        if self.status == QuestionSetStatus.CONFIRMED and self.confirmed_at is None:
            raise ValueError("A confirmed question set needs a confirmation time.")
        if self.status == QuestionSetStatus.DRAFT and self.confirmed_at is not None:
            raise ValueError("A draft question set cannot have a confirmation time.")
        return self


class EvaluationSource(ApiModel):
    question_set_id: str = Field(alias="questionSetId")
    manual_id: str = Field(alias="manualId")


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
    source: EvaluationSource | None = None
    is_complete: bool = Field(alias="isComplete")
    counts: CoverageCounts
    results: list[QuestionResult]
    gaps: list[Gap]
    recommendations: list[Recommendation]
    follow_up_questions: list[str] = Field(alias="followUpQuestions")


class WorkspaceError(ApiModel):
    code: str = "workflow_error"
    title: str
    message: str
    stage: WorkflowStage
    retryable: bool = False


def _legacy_question_set(raw: dict[str, Any], configuration_version: int) -> dict[str, Any] | None:
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
    confirmed = stage in {WorkflowStage.EVALUATION.value, WorkflowStage.REPORT.value}
    return {
        "id": str(uuid5(NAMESPACE_URL, f"uvts-legacy-question-set:{digest}")),
        "status": "confirmed" if confirmed else "draft",
        "source": "legacy_manual_unknown",
        "configurationVersion": configuration_version,
        "generatedAt": None,
        "confirmedAt": "1970-01-01T00:00:00Z" if confirmed else None,
        "items": normalized_questions,
    }


def upgrade_workspace_state(value: Any) -> Any:
    """Normalize persisted v1 JSON without deleting user-owned content."""

    if not isinstance(value, dict):
        return value
    raw = dict(value)
    raw.pop("relationalFactsVersion", None)
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
            configuration.get("productDescription", configuration.get("product_description", ""))
        ).strip()
    )
    configuration["version"] = int(configuration.get("version") or (1 if has_saved_setup else 0))
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

    manual = raw.get("manual")
    snake_evaluation_source = raw.pop("evaluation_source", None)
    if "evaluationSource" not in raw and snake_evaluation_source is not None:
        raw["evaluationSource"] = snake_evaluation_source
    evaluation_source = raw.get("evaluationSource")
    if is_legacy and evaluation_source is None and question_set and isinstance(manual, dict):
        if stage in {"evaluation", "report"} and manual.get("id"):
            raw["evaluationSource"] = {
                "questionSetId": question_set["id"],
                "manualId": manual.get("id"),
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


class WorkspaceState(ApiModel):
    schema_version: Literal[2] = Field(default=2, alias="schemaVersion")
    current_stage: WorkflowStage = Field(
        default=WorkflowStage.CONFIGURATION, alias="currentStage"
    )
    manual: ManualSummary | None = None
    manual_upload: ManualUpload | None = Field(default=None, alias="manualUpload")
    configuration: TestConfiguration = Field(default_factory=TestConfiguration)
    question_set: QuestionSet | None = Field(default=None, alias="questionSet")
    evaluation_source: EvaluationSource | None = Field(default=None, alias="evaluationSource")
    evaluation: list[EvaluationItem] = Field(default_factory=list)
    report: Report | None = None
    error: WorkspaceError | None = None

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_state(cls, value: Any) -> Any:
        return upgrade_workspace_state(value)

    @model_validator(mode="after")
    def validate_lineage(self) -> Self:
        question_set = self.question_set
        if question_set is not None and question_set.source == QuestionSetSource.PRODUCT_CONTEXT:
            if question_set.configuration_version is None:
                raise ValueError(
                    "A product-context question set needs a configuration version."
                )
            if (
                question_set.status == QuestionSetStatus.DRAFT
                and question_set.configuration_version == self.configuration.version
                and len(question_set.items) != self.configuration.total_questions
            ):
                raise ValueError(
                    "A product-context question set must match the configured question count."
                )
            if (
                question_set.status == QuestionSetStatus.CONFIRMED
                and question_set.configuration_version != self.configuration.version
            ):
                raise ValueError(
                    "A confirmed question set must match the saved Product setup version."
                )

        source = self.evaluation_source
        if source is not None:
            if (
                question_set is None
                or question_set.status != QuestionSetStatus.CONFIRMED
                or source.question_set_id != question_set.id
            ):
                raise ValueError(
                    "Evaluation must use the current confirmed question set."
                )
            if (
                self.manual is None
                or self.manual.status != ManualStatus.READY
                or source.manual_id != self.manual.id
            ):
                raise ValueError("Evaluation must use the current ready manual.")

        if self.evaluation:
            if source is None:
                raise ValueError("Evaluation progress needs a persisted evaluation source.")
            question_ids = [item.question_id for item in self.evaluation]
            if len(question_ids) != len(set(question_ids)):
                raise ValueError("Evaluation progress cannot repeat a question.")
            current_ids = {item.id for item in question_set.items} if question_set else set()
            if not set(question_ids) <= current_ids:
                raise ValueError("Evaluation progress contains an unknown question.")

        if self.report is not None and self.report.source is not None:
            if source is None or self.report.source != source:
                raise ValueError("The report source must match the evaluation source.")
        return self

    @property
    def questions(self) -> list[Question]:
        return self.question_set.items if self.question_set is not None else []


class TestWorkspace(WorkspaceState):
    id: str
