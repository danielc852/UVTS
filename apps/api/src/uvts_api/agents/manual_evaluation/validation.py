from collections.abc import Mapping, Sequence
from typing import Literal

from uvts_api.agents.errors import EvaluatorOutputError
from uvts_api.agents.manual_evaluation.schemas import (
    AtomicEvaluationOutput,
    RequirementEvidence,
)
from uvts_api.agents.schemas import AgentEvidence, QuestionEvaluationOutput

type ManualPage = Mapping[str, object]


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_pages(manual_pages: Sequence[ManualPage]) -> dict[int, str]:
    pages: dict[int, str] = {}
    for item in manual_pages:
        page = item.get("page")
        text = item.get("text")
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise ValueError("Manual pages must have positive integer page numbers.")
        if not isinstance(text, str):
            raise ValueError("Manual pages must contain text.")
        if page in pages:
            raise ValueError("Manual page numbers must be unique.")
        pages[page] = normalize_whitespace(text)
    if not pages:
        raise ValueError("The manual does not contain any pages.")
    return pages


def validate_and_fold_evaluation(
    output: AtomicEvaluationOutput,
    pages: Mapping[int, str],
) -> QuestionEvaluationOutput:
    requirements: list[str] = []
    found_descriptions: list[str] = []
    missing_descriptions: list[str] = []
    seen_requirements: set[str] = set()
    evidence: list[AgentEvidence] = []
    seen_evidence: set[tuple[int, str]] = set()

    for assessment in output.requirements:
        requirement = _required(assessment.requirement, "requirement")
        requirement_key = requirement.casefold()
        if requirement_key in seen_requirements:
            raise EvaluatorOutputError("Atomic requirements must be unique.")
        seen_requirements.add(requirement_key)
        requirements.append(requirement)

        finding = _optional(assessment.finding, "finding")
        checked_evidence = _validate_evidence(assessment.evidence, pages)
        if assessment.status == "found":
            if finding is None or not checked_evidence:
                raise EvaluatorOutputError(
                    "A found requirement must include a finding and evidence."
                )
            found_descriptions.append(finding)
            for item in checked_evidence:
                key = (item.page, item.extract)
                if key not in seen_evidence:
                    seen_evidence.add(key)
                    evidence.append(AgentEvidence(page=item.page, extract=item.extract))
        else:
            if finding is not None or checked_evidence:
                raise EvaluatorOutputError(
                    "A not_found requirement cannot include a finding or evidence."
                )
            missing_descriptions.append(requirement)

    status: Literal["found", "partly_found", "not_found"]
    if not missing_descriptions:
        status = "found"
    elif found_descriptions:
        status = "partly_found"
    else:
        status = "not_found"

    return QuestionEvaluationOutput(
        status=status,
        information_needed=_join(requirements),
        information_found=_join(found_descriptions) if found_descriptions else None,
        information_missing=_join(missing_descriptions) if missing_descriptions else None,
        evidence=evidence,
    )


def _validate_evidence(
    items: Sequence[RequirementEvidence],
    pages: Mapping[int, str],
) -> list[RequirementEvidence]:
    checked: list[RequirementEvidence] = []
    seen: set[tuple[int, str]] = set()
    for item in items:
        extract = _required(item.extract, "evidence extract")
        page_text = pages.get(item.page)
        if page_text is None:
            raise EvaluatorOutputError("Evidence refers to a page outside the manual.")
        if extract not in page_text:
            raise EvaluatorOutputError("Evidence is not an exact extract from its page.")
        key = (item.page, extract)
        if key not in seen:
            seen.add(key)
            checked.append(RequirementEvidence(page=item.page, extract=extract))
    return checked


def _required(value: str, field_name: str) -> str:
    normalized = normalize_whitespace(value)
    if not normalized:
        raise EvaluatorOutputError(f"{field_name} must not be blank")
    return normalized


def _optional(value: str | None, field_name: str) -> str | None:
    return None if value is None else _required(value, field_name)


def _join(values: Sequence[str]) -> str:
    return "; ".join(values)
