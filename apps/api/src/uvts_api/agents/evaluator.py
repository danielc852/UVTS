import base64
import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.content import create_image_block
from pydantic import ValidationError

from uvts_api.agents.errors import (
    EvaluatorModelInvocationError,
    EvaluatorOutputError,
    EvaluatorStructuredOutputError,
)
from uvts_api.agents.schemas import (
    AgentEvidence,
    QuestionEvaluationOutput,
    ReportSynthesisOutput,
    SynthesizedGap,
    SynthesizedRecommendation,
)
from uvts_api.ports.question_generator import AgentProductImage
from uvts_api.schemas.workspace import CoverageStatus, Question, QuestionResult

type ManualPage = Mapping[str, object]

_EVALUATION_SYSTEM_PROMPT = """You check only whether a product manual contains the
information needed by one supplied question. Use only the page-labelled manual text. Do not
answer the question, add outside knowledge, or treat plausible information as present. Return
short, plain-language descriptions of information needed, found, and missing. Every evidence
extract must be copied exactly from one supplied page. Use found only when all needed information
is present, partly_found when some is present, and not_found when none is present. The product
image and description are interpretation-only context: they must never count as evidence."""

_REPORT_SYSTEM_PROMPT = """You turn persisted manual-coverage results into writing gaps,
recommendations, and follow-up test questions. Use only the supplied results. Do not answer any
test question and do not recommend product changes. Each gap must link to one or more supplied
question IDs with partly_found or not_found status. Each recommendation must link to a gap key
from your own output. Keep wording concise and understandable to a non-technical writer."""


class EvaluatorAgent:
    """Typed model operations for evidence checking and report synthesis."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def evaluate(
        self,
        *,
        question: Question,
        manual_pages: Sequence[ManualPage],
        product_image: AgentProductImage | None = None,
        product_description: str = "",
    ) -> QuestionEvaluationOutput:
        pages = _normalise_pages(manual_pages)
        prompt = _evaluation_prompt(question, pages, product_description)
        content: list[str | dict[Any, Any]] = [{"type": "text", "text": prompt}]
        if product_image is not None:
            content.append(
                cast(
                    dict[Any, Any],
                    create_image_block(
                        base64=base64.b64encode(product_image.content).decode("ascii"),
                        mime_type=product_image.content_type,
                    ),
                )
            )
        try:
            structured_model = self._model.with_structured_output(
                QuestionEvaluationOutput,
                method="json_schema",
                strict=True,
            )
            raw_output = await structured_model.ainvoke(
                [
                    SystemMessage(content=_EVALUATION_SYSTEM_PROMPT),
                    HumanMessage(content=content),
                ]
            )
        except (OutputParserException, ValidationError) as error:
            raise EvaluatorStructuredOutputError(type(error).__name__) from None
        except Exception as error:
            raise EvaluatorModelInvocationError(type(error).__name__) from None
        try:
            output = QuestionEvaluationOutput.model_validate(raw_output)
        except ValidationError as error:
            raise EvaluatorStructuredOutputError(type(error).__name__) from None
        return _validate_evaluation(output, pages)

    async def evaluate_question(
        self,
        *,
        question: Question,
        manual_pages: Sequence[ManualPage],
        product_image: AgentProductImage | None = None,
        product_description: str = "",
    ) -> QuestionEvaluationOutput:
        """Descriptive alias used by application services and tests."""

        return await self.evaluate(
            question=question,
            manual_pages=manual_pages,
            product_image=product_image,
            product_description=product_description,
        )

    async def synthesize(
        self,
        *,
        results: Sequence[QuestionResult],
    ) -> ReportSynthesisOutput:
        eligible_results = [
            result
            for result in results
            if result.status in {CoverageStatus.PARTLY_FOUND, CoverageStatus.NOT_FOUND}
        ]
        if not eligible_results:
            return ReportSynthesisOutput(
                gaps=[], recommendations=[], follow_up_questions=[]
            )
        try:
            structured_model = self._model.with_structured_output(
                ReportSynthesisOutput,
                method="json_schema",
                strict=True,
            )
            raw_output = await structured_model.ainvoke(
                [
                    SystemMessage(content=_REPORT_SYSTEM_PROMPT),
                    HumanMessage(content=_synthesis_prompt(results)),
                ]
            )
        except (OutputParserException, ValidationError) as error:
            raise EvaluatorStructuredOutputError(type(error).__name__) from None
        except Exception as error:
            raise EvaluatorModelInvocationError(type(error).__name__) from None
        try:
            output = ReportSynthesisOutput.model_validate(raw_output)
        except ValidationError as error:
            raise EvaluatorStructuredOutputError(type(error).__name__) from None
        return _validate_synthesis(output, eligible_results)

    async def synthesize_report(
        self,
        *,
        results: Sequence[QuestionResult],
    ) -> ReportSynthesisOutput:
        """Descriptive alias used by application services and tests."""

        return await self.synthesize(results=results)


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalise_required(value: str, field_name: str) -> str:
    normalised = normalize_whitespace(value)
    if not normalised:
        raise EvaluatorOutputError(f"{field_name} must not be blank")
    return normalised


def _normalise_optional(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _normalise_required(value, field_name)


def _normalise_pages(manual_pages: Sequence[ManualPage]) -> dict[int, str]:
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


def _evaluation_prompt(
    question: Question,
    pages: Mapping[int, str],
    product_description: str = "",
) -> str:
    question_json = json.dumps(
        question.model_dump(mode="json", by_alias=True), ensure_ascii=False, separators=(",", ":")
    )
    labelled_pages = "\n\n".join(
        f"[PAGE {page}]\n{text}\n[/PAGE {page}]" for page, text in sorted(pages.items())
    )
    return (
        "INTERPRETATION-ONLY PRODUCT CONTEXT (NOT EVIDENCE)\n"
        f"{product_description}\n\n"
        f"QUESTION RECORD\n{question_json}\n\n"
        f"MANUAL EVIDENCE SOURCE\n{labelled_pages}"
    )


def _synthesis_prompt(results: Sequence[QuestionResult]) -> str:
    persisted = [result.model_dump(mode="json", by_alias=True) for result in results]
    return "Persisted question results:\n" + json.dumps(
        persisted, ensure_ascii=False, separators=(",", ":")
    )


def _validate_evaluation(
    output: QuestionEvaluationOutput,
    pages: Mapping[int, str],
) -> QuestionEvaluationOutput:
    needed = _normalise_required(output.information_needed, "information_needed")
    found = _normalise_optional(output.information_found, "information_found")
    missing = _normalise_optional(output.information_missing, "information_missing")
    evidence: list[AgentEvidence] = []
    for item in output.evidence:
        extract = _normalise_required(item.extract, "evidence extract")
        page_text = pages.get(item.page)
        if page_text is None:
            raise EvaluatorOutputError("Evidence refers to a page outside the manual.")
        if extract not in page_text:
            raise EvaluatorOutputError("Evidence is not an exact extract from its page.")
        evidence.append(AgentEvidence(page=item.page, extract=extract))

    if output.status == CoverageStatus.FOUND:
        valid = found is not None and missing is None and bool(evidence)
    elif output.status == CoverageStatus.PARTLY_FOUND:
        valid = found is not None and missing is not None and bool(evidence)
    elif output.status == CoverageStatus.NOT_FOUND:
        valid = found is None and missing is not None and not evidence
    else:  # The Pydantic schema should make this unreachable.
        valid = False
    if not valid:
        raise EvaluatorOutputError(
            "The coverage status does not match the found, missing, and evidence fields."
        )
    return output.model_copy(
        update={
            "information_needed": needed,
            "information_found": found,
            "information_missing": missing,
            "evidence": evidence,
        }
    )


def _validate_synthesis(
    output: ReportSynthesisOutput,
    eligible_results: Sequence[QuestionResult],
) -> ReportSynthesisOutput:
    eligible_ids = {result.question.id for result in eligible_results}
    gap_keys: set[str] = set()
    gaps: list[SynthesizedGap] = []
    for gap_item in output.gaps:
        key = _normalise_required(gap_item.key, "gap key")
        affected_ids = [
            _normalise_required(value, "affected question ID")
            for value in gap_item.affected_question_ids
        ]
        if key in gap_keys:
            raise EvaluatorOutputError("Gap keys must be unique.")
        if len(affected_ids) != len(set(affected_ids)):
            raise EvaluatorOutputError("A gap must not repeat a question link.")
        if not set(affected_ids) <= eligible_ids:
            raise EvaluatorOutputError("A gap links to an unsupported question.")
        gap_keys.add(key)
        gaps.append(
            gap_item.model_copy(
                update={
                    "key": key,
                    "title": _normalise_required(gap_item.title, "gap title"),
                    "why_it_matters": _normalise_required(
                        gap_item.why_it_matters, "gap explanation"
                    ),
                    "affected_question_ids": affected_ids,
                }
            )
    )

    recommendations: list[SynthesizedRecommendation] = []
    for recommendation_item in output.recommendations:
        gap_key = _normalise_required(
            recommendation_item.gap_key, "recommendation gap key"
        )
        if gap_key not in gap_keys:
            raise EvaluatorOutputError("A recommendation links to an unknown gap.")
        recommendations.append(
            recommendation_item.model_copy(
                update={
                    "change": _normalise_required(
                        recommendation_item.change, "recommended change"
                    ),
                    "reason": _normalise_required(
                        recommendation_item.reason, "recommendation reason"
                    ),
                    "gap_key": gap_key,
                }
            )
        )
    follow_up_questions = [
        _normalise_required(item, "follow-up question") for item in output.follow_up_questions
    ]
    return output.model_copy(
        update={
            "gaps": gaps,
            "recommendations": recommendations,
            "follow_up_questions": follow_up_questions,
        }
    )
