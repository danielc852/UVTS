from enum import StrEnum


class TestStatus(StrEnum):
    DRAFT = "draft"
    GENERATING = "generating"
    QUESTIONS_READY = "questions_ready"
    QUESTIONS_CONFIRMED = "questions_confirmed"
    READY = "ready"
    EVALUATING = "evaluating"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
