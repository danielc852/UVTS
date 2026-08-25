from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ManualEvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RequirementEvidence(ManualEvaluationModel):
    page: int = Field(ge=1)
    extract: str = Field(min_length=1)


class AtomicRequirementAssessment(ManualEvaluationModel):
    requirement: str = Field(
        min_length=1,
        description="One concise, atomic description of information needed by the question",
    )
    status: Literal["found", "not_found"]
    finding: Annotated[str, Field(min_length=1)] | None = Field(
        description="Grounded information for found, otherwise null"
    )
    evidence: list[RequirementEvidence] = Field(
        description="Exact page extracts for found, otherwise an empty list"
    )

    @field_validator("finding", mode="before")
    @classmethod
    def normalize_blank_finding(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class AtomicEvaluationOutput(ManualEvaluationModel):
    requirements: list[AtomicRequirementAssessment] = Field(min_length=1, max_length=8)
