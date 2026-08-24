import pytest

from uvts_api.ports.question_generator import (
    QUESTION_GENERATION_INSTRUCTIONS,
    GeneratedQuestion,
    GeneratedQuestionSet,
)
from uvts_api.services.questions import validate_generated_questions


def test_generation_instructions_forbid_manual_grounding_and_answers() -> None:
    assert "product image and product description" in QUESTION_GENERATION_INSTRUCTIONS
    assert "Do not answer" in QUESTION_GENERATION_INSTRUCTIONS
    assert "manual" not in QUESTION_GENERATION_INSTRUCTIONS.casefold()


def test_application_boundary_trims_and_validates_provider_questions() -> None:
    generated = GeneratedQuestionSet(
        questions=[
            GeneratedQuestion(text="  How do I begin?  "),
            GeneratedQuestion(text="What happens at the limit?"),
        ]
    )

    assert validate_generated_questions(generated, expected_count=2) == [
        "How do I begin?",
        "What happens at the limit?",
    ]


@pytest.mark.parametrize(
    "questions",
    [
        [GeneratedQuestion(text="Only one question")],
        [
            GeneratedQuestion(text="How do I begin?"),
            GeneratedQuestion(text=" how do I BEGIN "),
        ],
    ],
)
def test_application_boundary_rejects_wrong_count_and_normalized_duplicates(
    questions: list[GeneratedQuestion],
) -> None:
    with pytest.raises(ValueError):
        validate_generated_questions(
            GeneratedQuestionSet(questions=questions),
            expected_count=2,
        )
