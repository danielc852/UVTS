from collections import defaultdict, deque
from typing import cast

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from uvts_api.agents.evaluator import EvaluatorAgent, EvaluatorOutputError
from uvts_api.agents.schemas import (
    QuestionEvaluationOutput,
    ReportSynthesisOutput,
)
from uvts_api.ports.question_generator import AgentProductImage
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


def question(question_id: str = "q1") -> Question:
    return Question(
        id=question_id,
        text="How is setup completed?",
    )


async def test_evaluates_with_page_labels_and_normalizes_valid_evidence() -> None:
    model = FakeChatModel()
    model.responses[QuestionEvaluationOutput].append(
        {
            "status": "found",
            "information_needed": "  setup   steps ",
            "information_found": " steps are   present ",
            "information_missing": None,
            "evidence": [{"page": 2, "extract": "Connect   the device."}],
        }
    )

    result = await EvaluatorAgent(cast(BaseChatModel, model)).evaluate_question(
        question=question(),
        manual_pages=[
            {"page": 1, "text": "Introduction"},
            {"page": 2, "text": "Connect \n the device. Then continue."},
        ],
    )

    assert result.information_needed == "setup steps"
    assert result.information_found == "steps are present"
    assert result.evidence[0].extract == "Connect the device."
    messages = model.calls[0][1]
    assert "[PAGE 1]" in str(messages[1].content)
    assert "[PAGE 2]" in str(messages[1].content)
    assert "answer" in str(messages[0].content).lower()


async def test_product_context_is_labelled_interpretation_only_and_manual_is_evidence() -> None:
    model = FakeChatModel()
    model.responses[QuestionEvaluationOutput].append(
        {
            "status": "not_found",
            "information_needed": "setup steps",
            "information_found": None,
            "information_missing": "all setup steps",
            "evidence": [],
        }
    )

    await EvaluatorAgent(cast(BaseChatModel, model)).evaluate_question(
        question=question(),
        manual_pages=[{"page": 1, "text": "No setup instructions are included."}],
        product_image=AgentProductImage(
            content=b"private-product-image",
            content_type="image/png",
            filename="product.png",
        ),
        product_description="A product description that mentions setup.",
    )

    messages = model.calls[0][1]
    system = str(messages[0].content).casefold()
    human = str(messages[1].content)
    assert "interpretation-only" in system
    assert "must never count as evidence" in system
    assert "INTERPRETATION-ONLY PRODUCT CONTEXT" in human
    assert "MANUAL EVIDENCE SOURCE" in human
    assert "image" in human


@pytest.mark.parametrize(
    "output",
    [
        {
            "status": "found",
            "information_needed": "steps",
            "information_found": "present",
            "information_missing": "recovery",
            "evidence": [{"page": 1, "extract": "Setup steps"}],
        },
        {
            "status": "partly_found",
            "information_needed": "steps",
            "information_found": "present",
            "information_missing": None,
            "evidence": [{"page": 1, "extract": "Setup steps"}],
        },
        {
            "status": "not_found",
            "information_needed": "steps",
            "information_found": None,
            "information_missing": "all steps",
            "evidence": [{"page": 1, "extract": "Setup steps"}],
        },
    ],
)
async def test_rejects_status_field_invariant_violations(output: object) -> None:
    model = FakeChatModel()
    model.responses[QuestionEvaluationOutput].append(output)

    with pytest.raises(EvaluatorOutputError, match="coverage status"):
        await EvaluatorAgent(cast(BaseChatModel, model)).evaluate(
            question=question(),
            manual_pages=[{"page": 1, "text": "Setup steps"}],
        )


@pytest.mark.parametrize(
    ("page", "extract", "message"),
    [
        (2, "Setup steps", "outside the manual"),
        (1, "A made-up extract", "not an exact extract"),
    ],
)
async def test_rejects_unverified_evidence(page: int, extract: str, message: str) -> None:
    model = FakeChatModel()
    model.responses[QuestionEvaluationOutput].append(
        QuestionEvaluationOutput(
            status="found",
            information_needed="steps",
            information_found="present",
            information_missing=None,
            evidence=[{"page": page, "extract": extract}],
        )
    )

    with pytest.raises(EvaluatorOutputError, match=message):
        await EvaluatorAgent(cast(BaseChatModel, model)).evaluate(
            question=question(),
            manual_pages=[{"page": 1, "text": "Setup steps"}],
        )


async def test_synthesis_normalizes_and_validates_links() -> None:
    model = FakeChatModel()
    model.responses[ReportSynthesisOutput].append(
        {
            "gaps": [
                {
                    "key": " recovery ",
                    "title": " Missing   recovery ",
                    "why_it_matters": " Users can get stuck. ",
                    "affected_question_ids": ["q1"],
                    "kind": "missing",
                }
            ],
            "recommendations": [
                {
                    "priority": "High",
                    "change": " Add recovery steps. ",
                    "reason": " The steps are absent. ",
                    "gap_key": " recovery ",
                }
            ],
            "follow_up_questions": [" Can setup resume? "],
        }
    )
    result = await EvaluatorAgent(cast(BaseChatModel, model)).synthesize_report(
        results=[not_found_result()],
    )

    assert result.gaps[0].key == "recovery"
    assert result.gaps[0].title == "Missing recovery"
    assert result.recommendations[0].gap_key == "recovery"
    assert result.follow_up_questions == ["Can setup resume?"]


@pytest.mark.parametrize(
    "synthesis",
    [
        {
            "gaps": [
                {
                    "key": "gap",
                    "title": "Gap",
                    "why_it_matters": "It matters",
                    "affected_question_ids": ["unknown"],
                    "kind": "missing",
                }
            ],
            "recommendations": [],
            "follow_up_questions": [],
        },
        {
            "gaps": [],
            "recommendations": [
                {
                    "priority": "High",
                    "change": "Add steps",
                    "reason": "They are absent",
                    "gap_key": "unknown",
                }
            ],
            "follow_up_questions": [],
        },
    ],
)
async def test_rejects_broken_synthesis_links(synthesis: object) -> None:
    model = FakeChatModel()
    model.responses[ReportSynthesisOutput].append(
        ReportSynthesisOutput.model_validate(synthesis)
    )

    with pytest.raises(EvaluatorOutputError):
        await EvaluatorAgent(cast(BaseChatModel, model)).synthesize(
            results=[not_found_result()]
        )


def not_found_result() -> QuestionResult:
    return QuestionResult(
        question=question(),
        status="not_found",
        information_needed="Recovery steps",
        information_found=None,
        information_missing="All recovery steps",
        evidence=[],
    )
