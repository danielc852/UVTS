from typing import cast

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from tests.fake_models import FakeStructuredChatModel
from uvts_api.agents.question_agent import InvalidQuestionSetError, QuestionAgent
from uvts_api.agents.schemas import GeneratedQuestion, GeneratedQuestionSet
from uvts_api.schemas.workspace import (
    QuestionType,
    QuestionTypeCounts,
    Viewpoint,
)
from uvts_api.schemas.workspace import TestConfiguration as QuestionConfiguration


def configuration() -> QuestionConfiguration:
    return QuestionConfiguration(
        total_questions=3,
        type_counts=QuestionTypeCounts(basic=2, cross_paragraph=0, edge_case=1),
        topics=["Setup", "Limits"],
        viewpoints=[Viewpoint.BEGINNER.value, Viewpoint.ADVANCED_USER.value],
    )


def valid_set() -> GeneratedQuestionSet:
    return GeneratedQuestionSet(
        questions=[
            GeneratedQuestion(
                text="  How do I start setup?  ",
                type=QuestionType.BASIC,
                topic="Setup",
                viewpoint=Viewpoint.BEGINNER,
            ),
            GeneratedQuestion(
                text="Where can I review setup requirements?",
                type=QuestionType.BASIC,
                topic="Setup",
                viewpoint=Viewpoint.ADVANCED_USER,
            ),
            GeneratedQuestion(
                text="What happens at the device limit?",
                type=QuestionType.EDGE_CASE,
                topic="Limits",
                viewpoint=Viewpoint.ADVANCED_USER,
            ),
        ]
    )


def question_agent(
    model: FakeStructuredChatModel, *, ids: list[str] | None = None
) -> QuestionAgent:
    id_values = iter(ids) if ids is not None else None
    return QuestionAgent(
        cast(BaseChatModel, model),
        id_factory=(lambda: next(id_values)) if id_values is not None else None,
    )


async def test_generates_structured_questions_and_assigns_ids_server_side() -> None:
    model = FakeStructuredChatModel(valid_set())
    agent = question_agent(
        model,
        ids=["question-1", "question-2", "question-3"],
    )

    questions = await agent.generate(
        manual_text="[Page 1]\nSetup instructions.\n\n[Page 2]\nDevice limits.",
        configuration=configuration(),
    )

    assert [question.id for question in questions] == [
        "question-1",
        "question-2",
        "question-3",
    ]
    assert questions[0].text == "How do I start setup?"
    assert model.schema is GeneratedQuestionSet
    assert model.method == "json_schema"
    assert model.strict is True
    messages = model.invocations[0]
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert '"Basic":2' in str(messages[1].content)
    assert "[Page 2]\nDevice limits." in str(messages[1].content)
    assert "Do not answer the questions" in str(messages[0].content)


@pytest.mark.parametrize(
    ("question_set", "message"),
    [
        (GeneratedQuestionSet(questions=valid_set().questions[:2]), "generated total"),
        (
            GeneratedQuestionSet(
                questions=[
                    valid_set().questions[0],
                    valid_set().questions[1],
                    valid_set().questions[1].model_copy(
                        update={"text": "Can I repeat setup?"}
                    ),
                ]
            ),
            "type counts",
        ),
        (
            valid_set().model_copy(
                update={
                    "questions": [
                        valid_set().questions[0].model_copy(update={"topic": "Privacy"}),
                        *valid_set().questions[1:],
                    ]
                }
            ),
            "unselected topic",
        ),
        (
            valid_set().model_copy(
                update={
                    "questions": [
                        valid_set().questions[0].model_copy(
                            update={"viewpoint": Viewpoint.REGULAR_USER}
                        ),
                        *valid_set().questions[1:],
                    ]
                }
            ),
            "unselected viewpoint",
        ),
        (
            valid_set().model_copy(
                update={
                    "questions": [
                        valid_set().questions[0],
                        valid_set().questions[1].model_copy(
                            update={"text": " how do I START setup "}
                        ),
                        valid_set().questions[2],
                    ]
                }
            ),
            "not unique",
        ),
        (
            valid_set().model_copy(
                update={
                    "questions": [
                        valid_set().questions[0].model_copy(update={"text": "   "}),
                        *valid_set().questions[1:],
                    ]
                }
            ),
            "empty",
        ),
    ],
)
async def test_rejects_model_output_that_breaks_generation_rules(
    question_set: GeneratedQuestionSet, message: str
) -> None:
    model = FakeStructuredChatModel(question_set)

    with pytest.raises(InvalidQuestionSetError, match=message):
        await question_agent(model).generate(
            manual_text="[Page 1]\nManual content",
            configuration=configuration(),
        )


async def test_rejects_empty_manual_before_calling_model() -> None:
    model = FakeStructuredChatModel(valid_set())

    with pytest.raises(InvalidQuestionSetError, match="manual text is empty"):
        await question_agent(model).generate(
            manual_text=" \n ",
            configuration=configuration(),
        )

    assert model.invocations == []
