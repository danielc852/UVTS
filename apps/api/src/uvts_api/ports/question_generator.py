from dataclasses import dataclass
from typing import Protocol

from pydantic import Field

from uvts_api.schemas.workspace import ApiModel

QUESTION_GENERATION_INSTRUCTIONS = """\
Create the exact requested number of distinct, realistic questions that a person may ask about
the pictured and described product. Use only the supplied product image and product description.
Do not answer the questions, add category metadata, or assume facts that are absent from the
supplied product context. Return only the structured question list.
"""


@dataclass(frozen=True)
class AgentProductImage:
    content: bytes
    content_type: str
    filename: str


@dataclass(frozen=True)
class QuestionDesign:
    total_questions: int


@dataclass(frozen=True)
class QuestionGenerationInput:
    product_image: AgentProductImage
    product_description: str
    question_design: QuestionDesign
    instructions: str = QUESTION_GENERATION_INSTRUCTIONS


class GeneratedQuestion(ApiModel):
    text: str = Field(min_length=1)


class GeneratedQuestionSet(ApiModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=15)


class QuestionGenerator(Protocol):
    async def generate(self, request: QuestionGenerationInput) -> GeneratedQuestionSet: ...
