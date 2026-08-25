from collections import defaultdict, deque
from typing import cast

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from uvts_api.agents.errors import (
    EvaluatorOutputError,
    EvaluatorRateLimitError,
    EvaluatorStructuredOutputError,
)
from uvts_api.agents.report_synthesis import ReportSynthesisAgent
from uvts_api.agents.report_synthesis.schemas import ReportSynthesisOutput
from uvts_api.schemas.workspace import Question, QuestionResult


class FakeStructuredModel:
    def __init__(self, model: "FakeChatModel", schema: type[BaseModel]) -> None:
        self.model = model
        self.schema = schema

    async def ainvoke(self, messages: list[BaseMessage]) -> object:
        self.model.calls.append((self.schema, messages))
        value = self.model.responses[self.schema].popleft()
        if isinstance(value, Exception):
            raise value
        return value


class FakeChatModel:
    def __init__(self) -> None:
        self.responses: defaultdict[type[BaseModel], deque[object]] = defaultdict(deque)
        self.calls: list[tuple[type[BaseModel], list[BaseMessage]]] = []

    def with_structured_output(
        self,
        schema: type[BaseModel],
        *,
        method: str,
        strict: bool,
    ) -> FakeStructuredModel:
        assert method == "json_schema"
        assert strict is True
        return FakeStructuredModel(self, schema)


class FakeRateLimitError(RuntimeError):
    status_code = 429
    headers = {"Retry-After": "7"}


def result(question_id: str, status: str = "not_found") -> QuestionResult:
    return QuestionResult(
        question=Question(id=question_id, text=f"Question {question_id}?"),
        status=status,
        information_needed=f"Need {question_id}",
        information_found="Present" if status in {"found", "partly_found"} else None,
        information_missing=None if status == "found" else f"Missing {question_id}",
        evidence=[],
    )


def valid_output(*question_ids: str) -> dict[str, object]:
    return {
        "gaps": [
            {
                "key": " recovery ",
                "title": " Missing   recovery guidance ",
                "why_it_matters": " Users can get stuck. ",
                "affected_question_ids": list(question_ids),
                "kind": "missing",
            }
        ],
        "recommendations": [
            {
                "priority": "High",
                "change": " Add recovery steps. ",
                "reason": " The procedure is absent. ",
                "gap_key": " RECOVERY ",
            }
        ],
        "follow_up_questions": [" Can setup resume? "],
    }


async def test_sends_only_eligible_results_and_normalizes_output() -> None:
    model = FakeChatModel()
    model.responses[ReportSynthesisOutput].append(valid_output("q-part", "q-missing"))

    synthesis = await ReportSynthesisAgent(cast(BaseChatModel, model)).synthesize_report(
        results=[
            result("q-found", "found"),
            result("q-part", "partly_found"),
            result("q-missing"),
        ]
    )

    human_prompt = str(model.calls[0][1][1].content)
    assert "q-found" not in human_prompt
    assert "q-part" in human_prompt
    assert "q-missing" in human_prompt
    assert synthesis.gaps[0].key == "recovery"
    assert synthesis.recommendations[0].gap_key == "recovery"
    assert synthesis.follow_up_questions == ["Can setup resume?"]


async def test_returns_empty_without_calling_model_when_nothing_is_eligible() -> None:
    model = FakeChatModel()

    synthesis = await ReportSynthesisAgent(cast(BaseChatModel, model)).synthesize_report(
        results=[result("q-found", "found")]
    )

    assert synthesis == ReportSynthesisOutput(
        gaps=[], recommendations=[], follow_up_questions=[]
    )
    assert model.calls == []


@pytest.mark.parametrize(
    "invalid",
    [
        # An eligible question is not covered.
        valid_output("q1"),
        # A gap has no recommendation.
        {
            **valid_output("q1", "q2"),
            "recommendations": [],
        },
        # A recommendation proposes an implementation rather than manual writing.
        {
            **valid_output("q1", "q2"),
            "recommendations": [
                {
                    "priority": "High",
                    "change": "Redesign the device firmware.",
                    "reason": "Users get stuck.",
                    "gap_key": "recovery",
                }
            ],
        },
        # Follow-ups are duplicates after normalization.
        {
            **valid_output("q1", "q2"),
            "follow_up_questions": ["Can setup resume?", " can setup resume? "],
        },
        # Follow-up lacks question punctuation.
        {
            **valid_output("q1", "q2"),
            "follow_up_questions": ["Explain setup recovery"],
        },
    ],
)
async def test_rejects_invalid_synthesis_after_one_repair(invalid: object) -> None:
    model = FakeChatModel()
    model.responses[ReportSynthesisOutput].extend([invalid, invalid])

    with pytest.raises(EvaluatorOutputError):
        await ReportSynthesisAgent(cast(BaseChatModel, model)).synthesize_report(
            results=[result("q1"), result("q2")]
        )

    assert len(model.calls) == 2


async def test_repairs_once_with_fixed_prompt_that_does_not_echo_private_data() -> None:
    model = FakeChatModel()
    model.responses[ReportSynthesisOutput].extend(
        [valid_output("q1"), valid_output("q1", "q-private")]
    )

    synthesis = await ReportSynthesisAgent(cast(BaseChatModel, model)).synthesize_report(
        results=[result("q1"), result("q-private")]
    )

    assert synthesis.gaps[0].affected_question_ids == ["q1", "q-private"]
    repair_text = str(model.calls[1][1][-1].content)
    assert "q-private" not in repair_text
    assert "Need q-private" not in repair_text
    assert len(model.calls) == 2


async def test_retries_a_structured_output_error_once() -> None:
    model = FakeChatModel()
    model.responses[ReportSynthesisOutput].extend(
        [{"not": "the schema"}, {"still": "invalid"}]
    )

    with pytest.raises(EvaluatorStructuredOutputError):
        await ReportSynthesisAgent(cast(BaseChatModel, model)).synthesize_report(
            results=[result("q1")]
        )

    assert len(model.calls) == 2


async def test_classifies_rate_limit_without_repairing() -> None:
    model = FakeChatModel()
    model.responses[ReportSynthesisOutput].append(
        FakeRateLimitError("private provider detail")
    )

    with pytest.raises(EvaluatorRateLimitError) as raised:
        await ReportSynthesisAgent(cast(BaseChatModel, model)).synthesize_report(
            results=[result("q1")]
        )

    assert raised.value.retry_after_seconds == 7
    assert "private provider detail" not in str(raised.value)
    assert len(model.calls) == 1
