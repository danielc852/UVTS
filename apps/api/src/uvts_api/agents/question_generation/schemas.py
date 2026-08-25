from enum import StrEnum

from pydantic import ConfigDict, Field

from uvts_api.schemas.workspace import ApiModel


class CoverageArea(StrEnum):
    SETUP_FIRST_USE = "setup_first_use"
    NORMAL_OPERATION = "normal_operation"
    CONTROLS_FEEDBACK = "controls_feedback"
    MAINTENANCE_STORAGE = "maintenance_storage"
    LIMITS_COMPATIBILITY = "limits_compatibility"
    TROUBLESHOOTING_RECOVERY = "troubleshooting_recovery"
    SAFETY_PRIVACY = "safety_privacy"
    OTHER = "other"


class ScenarioType(StrEnum):
    ROUTINE = "routine"
    EDGE_CASE = "edge_case"


class PlannedQuestion(ApiModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    coverage_area: CoverageArea
    scenario_type: ScenarioType


class PlannedQuestionSet(ApiModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[PlannedQuestion] = Field(min_length=1, max_length=15)
