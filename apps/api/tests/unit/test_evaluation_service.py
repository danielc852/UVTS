from uvts_api.adapters.db.models import QuestionEvaluationRecord
from uvts_api.agents.schemas import ReportSynthesisOutput
from uvts_api.schemas.workspace import Question, QuestionResult
from uvts_api.services.evaluation import (
    FAILED_INFORMATION_NEEDED,
    build_coverage_counts,
    build_question_results,
    build_report,
)


def make_question(question_id: str) -> Question:
    return Question(
        id=question_id,
        text=f"Question {question_id}?",
        type="Basic",
        topic="Setup and requirements",
        viewpoint="Beginner",
    )


def test_builds_deterministic_counts_and_failed_placeholders_in_question_order() -> None:
    questions = [make_question("q1"), make_question("q2"), make_question("q3")]
    complete = QuestionResult(
        question=questions[1],
        status="partly_found",
        information_needed="Steps and recovery",
        information_found="Steps",
        information_missing="Recovery",
        evidence=[{"page": 1, "extract": "Follow the steps."}],
    )
    records = [
        QuestionEvaluationRecord(
            test_run_id="test-1",
            question_id="q2",
            status="complete",
            result=complete.model_dump(mode="json", by_alias=True),
            attempt=1,
        ),
        QuestionEvaluationRecord(
            test_run_id="test-1",
            question_id="q1",
            status="failed",
            error="private failure detail",
            attempt=1,
        ),
    ]

    results = build_question_results(questions, records)
    counts = build_coverage_counts(results)

    assert [result.question.id for result in results] == ["q1", "q2", "q3"]
    assert results[0].information_needed == FAILED_INFORMATION_NEEDED
    assert results[0].information_found is None
    assert results[0].evidence == []
    assert counts.model_dump() == {
        "found": 0,
        "partly_found": 1,
        "not_found": 0,
        "failed": 2,
    }


def test_assigns_stable_gap_and_recommendation_ids() -> None:
    result = QuestionResult(
        question=make_question("q1"),
        status="not_found",
        information_needed="Recovery",
        information_found=None,
        information_missing="Recovery",
        evidence=[],
    )
    counts = build_coverage_counts([result])
    synthesis = ReportSynthesisOutput.model_validate(
        {
            "gaps": [
                {
                    "key": "recovery",
                    "title": "Recovery",
                    "why_it_matters": "Users can get stuck.",
                    "affected_question_ids": ["q1"],
                    "kind": "missing",
                }
            ],
            "recommendations": [
                {
                    "priority": "High",
                    "change": "Add recovery steps.",
                    "reason": "They are absent.",
                    "gap_key": "recovery",
                }
            ],
            "follow_up_questions": ["Can setup resume?"],
        }
    )

    report = build_report(results=[result], counts=counts, synthesis=synthesis)

    assert report.gaps[0].id == "gap-1"
    assert report.recommendations[0].id == "recommendation-1"
    assert report.recommendations[0].gap_id == "gap-1"
