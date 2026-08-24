from pydantic import BaseModel, ConfigDict, Field

from uvts_api.schemas.workspace import GapKind, QuestionType, RecommendationPriority, Viewpoint


class AgentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeneratedQuestion(AgentModel):
    text: str = Field(min_length=1)
    type: QuestionType
    topic: str = Field(min_length=1)
    viewpoint: Viewpoint


class GeneratedQuestionSet(AgentModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=15)


class AgentEvidence(AgentModel):
    page: int = Field(ge=1)
    extract: str = Field(min_length=1)


class QuestionEvaluationOutput(AgentModel):
    status: str = Field(pattern="^(found|partly_found|not_found)$")
    information_needed: str = Field(min_length=1)
    information_found: str | None
    information_missing: str | None
    evidence: list[AgentEvidence]


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
