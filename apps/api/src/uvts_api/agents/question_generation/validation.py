import re
import unicodedata

from uvts_api.agents.question_generation.schemas import PlannedQuestionSet, ScenarioType
from uvts_api.ports.question_generator import GeneratedQuestion, GeneratedQuestionSet


class InvalidQuestionSetError(ValueError):
    """The model returned a structured question set that violates the request."""


def normalize_question(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(part for part in re.split(r"[^\w]+", normalized) if part)


def validate_questions(
    generated: PlannedQuestionSet,
    *,
    total_questions: int,
    existing_questions: tuple[str, ...],
) -> GeneratedQuestionSet:
    if len(generated.questions) != total_questions:
        raise InvalidQuestionSetError("The generated total does not match the request.")

    existing = {normalize_question(question) for question in existing_questions if question.strip()}
    normalized_questions: set[str] = set()
    questions: list[GeneratedQuestion] = []
    coverage_areas = set()
    has_edge_case = False

    for item in generated.questions:
        text = item.text.strip()
        if not text:
            raise InvalidQuestionSetError("A generated question is empty.")
        normalized = normalize_question(text)
        if not normalized or normalized in normalized_questions:
            raise InvalidQuestionSetError("The generated questions are not unique.")
        if normalized in existing:
            raise InvalidQuestionSetError("A generated question duplicates an existing question.")
        normalized_questions.add(normalized)
        coverage_areas.add(item.coverage_area)
        has_edge_case = has_edge_case or item.scenario_type is ScenarioType.EDGE_CASE
        questions.append(GeneratedQuestion(text=text))

    if 2 <= total_questions <= 3 and len(coverage_areas) < 2:
        raise InvalidQuestionSetError("The generated questions lack coverage diversity.")
    if total_questions >= 4 and len(coverage_areas) < 4:
        raise InvalidQuestionSetError("The generated questions lack coverage diversity.")
    if total_questions >= 4 and not has_edge_case:
        raise InvalidQuestionSetError("The generated questions lack an edge-case scenario.")

    return GeneratedQuestionSet(questions=questions)
