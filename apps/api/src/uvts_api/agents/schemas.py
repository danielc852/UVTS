from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from uvts_api.schemas.workspace import GapKind, RecommendationPriority


class AgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentEvidence(AgentModel):
    page: int = Field(ge=1)
    extract: str = Field(min_length=1)


class QuestionEvaluationOutput(AgentModel):
    status: Literal["found", "partly_found", "not_found"] = Field(
        description=(
            "found when all needed information is evidenced; partly_found when only some is "
            "evidenced; not_found when none is evidenced"
        )
    )
    information_needed: str = Field(
        min_length=1,
        description="A non-blank description of all information required by the question",
    )
    information_found: Annotated[str, Field(min_length=1)] | None = Field(
        description=(
            "Non-blank information supported by evidence for found and partly_found; "
            "null for not_found"
        )
    )
    information_missing: Annotated[str, Field(min_length=1)] | None = Field(
        description=(
            "null for found; non-blank missing information for partly_found and not_found"
        )
    )
    evidence: list[AgentEvidence] = Field(
        description=(
            "One or more exact manual extracts for found and partly_found; empty for not_found"
        )
    )

    @field_validator("information_found", "information_missing", mode="before")
    @classmethod
    def normalize_blank_optional_strings(cls, value: object) -> object:
        """Treat model-produced blank optional values as absent values."""

        if isinstance(value, str) and not value.strip():
            return None
        return value


class SynthesizedGap(AgentModel):
    key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    affected_question_ids: list[str] = Field(min_length=1)
    kind: GapKind


class SynthesizedRecommendation(AgentModel):
    priority: RecommendationPriority
    change: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    gap_key: str = Field(min_length=1)


class ReportSynthesisOutput(AgentModel):
    gaps: list[SynthesizedGap]
    recommendations: list[SynthesizedRecommendation]
    follow_up_questions: list[str]
