from collections import Counter
from collections.abc import Sequence

from uvts_api.agents.errors import EvaluatorOutputError
from uvts_api.agents.report_synthesis.schemas import (
    ReportSynthesisOutput,
    SynthesizedGap,
    SynthesizedRecommendation,
)
from uvts_api.schemas.workspace import QuestionResult

_MANUAL_WRITING_TERMS = {
    "appendix",
    "caption",
    "chapter",
    "checklist",
    "diagram",
    "detail",
    "definition",
    "document",
    "documentation",
    "example",
    "explanation",
    "faq",
    "guidance",
    "guide",
    "instruction",
    "information",
    "label",
    "manual",
    "note",
    "procedure",
    "section",
    "step",
    "table",
    "troubleshooting",
    "warning",
}


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_identity(value: str) -> str:
    return normalize_whitespace(value).casefold()


def _required(value: str, field_name: str) -> str:
    normalized = normalize_whitespace(value)
    if not normalized:
        raise EvaluatorOutputError(f"{field_name} must not be blank")
    return normalized


def _is_manual_writing_change(value: str) -> bool:
    words = {
        token.strip(".,:;!?()[]{}\"'").casefold()
        for token in normalize_whitespace(value).split()
    }
    return any(
        word in _MANUAL_WRITING_TERMS
        or word.removesuffix("s") in _MANUAL_WRITING_TERMS
        for word in words
    )


def validate_synthesis(
    output: ReportSynthesisOutput,
    eligible_results: Sequence[QuestionResult],
) -> ReportSynthesisOutput:
    eligible_ids = {result.question.id for result in eligible_results}
    if not eligible_ids:
        if output.gaps or output.recommendations or output.follow_up_questions:
            raise EvaluatorOutputError("A synthesis was returned without eligible results.")
        return output
    if not output.gaps:
        raise EvaluatorOutputError("Eligible results require at least one gap.")

    normalized_gap_keys: set[str] = set()
    covered_ids: set[str] = set()
    gaps: list[SynthesizedGap] = []
    canonical_key_by_identity: dict[str, str] = {}
    for gap_item in output.gaps:
        key = _required(gap_item.key, "gap key")
        key_identity = normalize_identity(key)
        if key_identity in normalized_gap_keys:
            raise EvaluatorOutputError("Gap keys must be unique after normalization.")
        affected_ids = [
            _required(value, "affected question ID")
            for value in gap_item.affected_question_ids
        ]
        affected_identities = [normalize_identity(value) for value in affected_ids]
        if len(affected_identities) != len(set(affected_identities)):
            raise EvaluatorOutputError("A gap must not repeat a question link.")
        if not set(affected_ids) <= eligible_ids:
            raise EvaluatorOutputError("A gap links to an unsupported question.")
        normalized_gap_keys.add(key_identity)
        canonical_key_by_identity[key_identity] = key
        covered_ids.update(affected_ids)
        gaps.append(
            gap_item.model_copy(
                update={
                    "key": key,
                    "title": _required(gap_item.title, "gap title"),
                    "why_it_matters": _required(
                        gap_item.why_it_matters, "gap explanation"
                    ),
                    "affected_question_ids": affected_ids,
                }
            )
        )
    if covered_ids != eligible_ids:
        raise EvaluatorOutputError("Every eligible question must be linked to a gap.")

    recommendations: list[SynthesizedRecommendation] = []
    recommendation_counts: Counter[str] = Counter()
    recommendation_identities: set[tuple[str, str, str]] = set()
    for item in output.recommendations:
        gap_key = _required(item.gap_key, "recommendation gap key")
        gap_identity = normalize_identity(gap_key)
        if gap_identity not in normalized_gap_keys:
            raise EvaluatorOutputError("A recommendation links to an unknown gap.")
        change = _required(item.change, "recommended change")
        reason = _required(item.reason, "recommendation reason")
        if not _is_manual_writing_change(change):
            raise EvaluatorOutputError(
                "A recommendation must describe a manual-writing change."
            )
        identity = (gap_identity, normalize_identity(change), normalize_identity(reason))
        if identity in recommendation_identities:
            raise EvaluatorOutputError("Recommendations must be unique after normalization.")
        recommendation_identities.add(identity)
        recommendation_counts[gap_identity] += 1
        recommendations.append(
            item.model_copy(
                update={
                    "change": change,
                    "reason": reason,
                    "gap_key": canonical_key_by_identity[gap_identity],
                }
            )
        )
    if any(recommendation_counts[key] == 0 for key in normalized_gap_keys):
        raise EvaluatorOutputError("Every gap must have at least one recommendation.")

    if not 1 <= len(output.follow_up_questions) <= 5:
        raise EvaluatorOutputError("A synthesis must have one to five follow-up questions.")
    follow_up_questions = [
        _required(value, "follow-up question") for value in output.follow_up_questions
    ]
    follow_up_identities = [normalize_identity(value) for value in follow_up_questions]
    if len(follow_up_identities) != len(set(follow_up_identities)):
        raise EvaluatorOutputError("Follow-up questions must be unique after normalization.")
    if any(not value.endswith("?") for value in follow_up_questions):
        raise EvaluatorOutputError("Every follow-up question must end in a question mark.")

    return output.model_copy(
        update={
            "gaps": gaps,
            "recommendations": recommendations,
            "follow_up_questions": follow_up_questions,
        }
    )
