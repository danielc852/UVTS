from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import Field

from uvts_api.schemas.workspace import ApiModel


class GenerationMode(StrEnum):
    GENERATION = "generation"
    SUGGESTION = "suggestion"


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
    mode: GenerationMode = GenerationMode.GENERATION
    direction: str | None = None
    existing_questions: tuple[str, ...] = ()


class GeneratedQuestion(ApiModel):
    text: str = Field(min_length=1)


class GeneratedQuestionSet(ApiModel):
    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=15)


class QuestionGenerator(Protocol):
    async def generate(self, request: QuestionGenerationInput) -> GeneratedQuestionSet: ...
