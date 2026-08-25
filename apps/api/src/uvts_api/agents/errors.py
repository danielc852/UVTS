import re
from dataclasses import dataclass
from enum import StrEnum


class EvaluatorFailureStage(StrEnum):
    """Safe, high-level stages for evaluator failures."""

    MODEL_INVOCATION = "model_invocation"
    STRUCTURED_OUTPUT = "structured_output"
    SEMANTIC_VALIDATION = "semantic_validation"
    UNEXPECTED = "unexpected"


@dataclass(frozen=True, slots=True)
class EvaluatorFailureDetails:
    """Allowlisted diagnostic fields that are safe to send to application logs."""

    stage: EvaluatorFailureStage
    error_type: str
    message: str


class EvaluatorModelInvocationError(RuntimeError):
    """The model request failed before a usable structured response was returned."""

    stage = EvaluatorFailureStage.MODEL_INVOCATION
    safe_message = "The evaluator model request failed."
    safe_for_logging = True

    def __init__(self, source_error_type: str) -> None:
        self.source_error_type = _safe_error_type(source_error_type)
        super().__init__(self.safe_message)


class EvaluatorStructuredOutputError(ValueError):
    """The model response could not be parsed or validated against the schema."""

    stage = EvaluatorFailureStage.STRUCTURED_OUTPUT
    safe_message = "The evaluator returned an invalid structured response."
    safe_for_logging = True

    def __init__(self, source_error_type: str) -> None:
        self.source_error_type = _safe_error_type(source_error_type)
        super().__init__(self.safe_message)


class EvaluatorOutputError(ValueError):
    """The parsed response violates UVTS evaluation rules."""

    stage = EvaluatorFailureStage.SEMANTIC_VALIDATION
    safe_message = "The evaluator response failed semantic validation."
    safe_for_logging = True


def describe_evaluator_failure(error: Exception) -> EvaluatorFailureDetails:
    """Classify an evaluator error without copying provider or model-response content."""

    if isinstance(error, EvaluatorModelInvocationError):
        return EvaluatorFailureDetails(
            stage=error.stage,
            error_type=error.source_error_type,
            message=error.safe_message,
        )
    if isinstance(error, EvaluatorStructuredOutputError):
        return EvaluatorFailureDetails(
            stage=error.stage,
            error_type=error.source_error_type,
            message=error.safe_message,
        )
    if isinstance(error, EvaluatorOutputError):
        return EvaluatorFailureDetails(
            stage=error.stage,
            error_type=type(error).__name__,
            message=error.safe_message,
        )
    return EvaluatorFailureDetails(
        stage=EvaluatorFailureStage.UNEXPECTED,
        error_type=_safe_error_type(type(error).__name__),
        message="The evaluator failed unexpectedly.",
    )


def _safe_error_type(value: str) -> str:
    """Keep only a short class-like name so arbitrary exception text never reaches logs."""

    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,99}", value):
        return value
    return "UnknownError"
