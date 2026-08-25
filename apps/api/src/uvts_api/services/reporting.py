"""Pure builders for evaluation results and reports."""

from collections.abc import Sequence
from typing import Protocol

from uvts_api.agents.schemas import ReportSynthesisOutput
from uvts_api.schemas.workspace import (
    CoverageCounts,
    CoverageStatus,
    EvaluationSource,
    EvaluationStatus,
    Gap,
    Question,
    QuestionResult,
    Recommendation,
    Report,
    WorkflowStage,
    WorkspaceError,
)

FAILED_INFORMATION_NEEDED = "This question could not be checked."


class EvaluationRecord(Protocol):
    """The small read-only part of a stored evaluation used by report builders."""

    @property
    def question_id(self) -> str: ...

    @property
    def status(self) -> str: ...

    @property
    def result(self) -> object | None: ...


def build_question_results(
    questions: Sequence[Question],
    records: Sequence[EvaluationRecord],
) -> list[QuestionResult]:
    """Build ordered public results, replacing unusable records with safe failures."""
    records_by_id = {record.question_id: record for record in records}
    results: list[QuestionResult] = []
    for question in questions:
        record = records_by_id.get(question.id)
        if (
            record is not None
            and record.status == EvaluationStatus.COMPLETE.value
            and record.result is not None
        ):
            try:
                result = QuestionResult.model_validate(record.result)
            except ValueError:
                result = _failed_result(question)
            if result.question.id != question.id:
                result = _failed_result(question)
            results.append(result)
        else:
            results.append(_failed_result(question))
    return results


def build_coverage_counts(results: Sequence[QuestionResult]) -> CoverageCounts:
    """Count each coverage outcome in a result set."""
    return CoverageCounts(
        found=sum(result.status == CoverageStatus.FOUND for result in results),
        partly_found=sum(result.status == CoverageStatus.PARTLY_FOUND for result in results),
        not_found=sum(result.status == CoverageStatus.NOT_FOUND for result in results),
        failed=sum(result.status == CoverageStatus.FAILED for result in results),
    )


def build_report(
    *,
    source: EvaluationSource,
    results: list[QuestionResult],
    counts: CoverageCounts,
    synthesis: ReportSynthesisOutput,
) -> Report:
    """Combine deterministic evaluation data with the synthesized report content."""
    gap_ids = {gap.key: f"gap-{index}" for index, gap in enumerate(synthesis.gaps, start=1)}
    gaps = [
        Gap(
            id=gap_ids[item.key],
            title=item.title,
            why_it_matters=item.why_it_matters,
            affected_question_ids=item.affected_question_ids,
            kind=item.kind,
        )
        for item in synthesis.gaps
    ]
    recommendations = [
        Recommendation(
            id=f"recommendation-{index}",
            priority=item.priority,
            change=item.change,
            reason=item.reason,
            gap_id=gap_ids[item.gap_key],
        )
        for index, item in enumerate(synthesis.recommendations, start=1)
    ]
    return Report(
        source=source,
        is_complete=counts.failed == 0,
        counts=counts,
        results=results,
        gaps=gaps,
        recommendations=recommendations,
        follow_up_questions=synthesis.follow_up_questions,
    )


def build_incomplete_report(
    source: EvaluationSource | None,
    results: list[QuestionResult],
    counts: CoverageCounts,
) -> Report:
    """Build a usable partial report when synthesis could not finish."""
    return Report(
        source=source,
        is_complete=False,
        counts=counts,
        results=results,
        gaps=[],
        recommendations=[],
        follow_up_questions=[],
    )


def build_report_synthesis_error() -> WorkspaceError:
    """Build the public retryable error for an unfinished report synthesis."""
    return WorkspaceError(
        code="report_synthesis_failed",
        title="The report is incomplete",
        message=(
            "Question results were saved, but UVTS could not finish the report. "
            "Try finishing the report again."
        ),
        stage=WorkflowStage.REPORT,
        retryable=True,
    )


def _failed_result(question: Question) -> QuestionResult:
    return QuestionResult(
        question=question,
        status=CoverageStatus.FAILED,
        information_needed=FAILED_INFORMATION_NEEDED,
        information_found=None,
        information_missing=None,
        evidence=[],
    )
