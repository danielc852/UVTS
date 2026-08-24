from typing import cast

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from tests.fake_models import FakeStructuredChatModel
from uvts_api.agents.question_agent import InvalidQuestionSetError, QuestionAgent
from uvts_api.ports.question_generator import (
    AgentProductImage,
    GeneratedQuestion,
    GeneratedQuestionSet,
    QuestionDesign,
    QuestionGenerationInput,
)


def request() -> QuestionGenerationInput:
    return QuestionGenerationInput(
        product_image=AgentProductImage(
            content=b"private-image-bytes",
            content_type="image/png",
            filename="product.png",
        ),
        product_description="A portable weather sensor.",
        question_design=QuestionDesign(total_questions=3),
    )


def valid_set() -> GeneratedQuestionSet:
    return GeneratedQuestionSet(
        questions=[
            GeneratedQuestion(text="  How do I start setup?  "),
            GeneratedQuestion(text="Where can I review setup requirements?"),
            GeneratedQuestion(text="What happens at the device limit?"),
        ]
    )


async def test_generates_a_multimodal_product_only_question_request() -> None:
    model = FakeStructuredChatModel(valid_set())
    agent = QuestionAgent(cast(BaseChatModel, model))

    generated = await agent.generate(request())

    assert generated.questions[0].text == "How do I start setup?"
    assert model.schema is GeneratedQuestionSet
    assert model.method == "json_schema"
    assert model.strict is True
    messages = model.invocations[0]
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    rendered = str(messages[1].content)
    assert "A portable weather sensor." in rendered
    assert "QUESTION COUNT\\n3" in rendered
    assert "image" in rendered
    assert "manual" not in rendered.casefold()


@pytest.mark.parametrize(
    ("question_set", "message"),
    [
        (GeneratedQuestionSet(questions=valid_set().questions[:2]), "generated total"),
        (
            GeneratedQuestionSet(
                questions=[
                    valid_set().questions[0],
                    GeneratedQuestion(text=" how do I START setup "),
                    valid_set().questions[2],
                ]
            ),
            "not unique",
        ),
        (
            GeneratedQuestionSet(
                questions=[
                    GeneratedQuestion.model_construct(text="   "),
                    *valid_set().questions[1:],
                ]
            ),
            "empty",
        ),
    ],
)
async def test_rejects_invalid_model_question_sets(
    question_set: GeneratedQuestionSet, message: str
) -> None:
    model = FakeStructuredChatModel(question_set)
    with pytest.raises(InvalidQuestionSetError, match=message):
        await QuestionAgent(cast(BaseChatModel, model)).generate(request())
