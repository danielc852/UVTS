import base64
import json
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.messages.content import create_image_block

from uvts_api.agents.errors import EvaluatorStructuredOutputError
from uvts_api.agents.question_generation.prompts import (
    QUESTION_GENERATION_SYSTEM_PROMPT,
    repair_prompt,
)
from uvts_api.agents.question_generation.schemas import PlannedQuestionSet
from uvts_api.agents.question_generation.validation import (
    InvalidQuestionSetError,
    validate_questions,
)
from uvts_api.agents.structured_output import invoke_structured_output
from uvts_api.ports.question_generator import GeneratedQuestionSet, QuestionGenerationInput


class QuestionAgent:
    """LangChain adapter for provider-neutral question generation."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def generate(self, request: QuestionGenerationInput) -> GeneratedQuestionSet:
        try:
            planned = await self._invoke(self._initial_messages(request))
            return self._validate(planned, request)
        except (InvalidQuestionSetError, EvaluatorStructuredOutputError):
            pass

        try:
            planned = await self._invoke(
                [
                    *self._initial_messages(request),
                    HumanMessage(
                        content=repair_prompt(
                            total_questions=request.question_design.total_questions,
                            mode=request.mode,
                        )
                    ),
                ]
            )
            return self._validate(planned, request)
        except InvalidQuestionSetError as exc:
            raise InvalidQuestionSetError(
                "The model could not produce a valid question set after one repair attempt."
            ) from exc

    async def _invoke(self, messages: list[SystemMessage | HumanMessage]) -> PlannedQuestionSet:
        return await invoke_structured_output(self._model, PlannedQuestionSet, messages)

    @staticmethod
    def _validate(
        planned: PlannedQuestionSet, request: QuestionGenerationInput
    ) -> GeneratedQuestionSet:
        return validate_questions(
            planned,
            total_questions=request.question_design.total_questions,
            existing_questions=request.existing_questions,
        )

    @staticmethod
    def _initial_messages(request: QuestionGenerationInput) -> list[SystemMessage | HumanMessage]:
        image = request.product_image
        image_block = cast(
            dict[Any, Any],
            create_image_block(
                base64=base64.b64encode(image.content).decode("ascii"),
                mime_type=image.content_type,
            ),
        )
        context = {
            "mode": request.mode.value,
            "product_description": request.product_description,
            "requested_count": request.question_design.total_questions,
            "user_direction": request.direction,
            "existing_questions": list(request.existing_questions),
        }
        return [
            SystemMessage(content=QUESTION_GENERATION_SYSTEM_PROMPT),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": "UNTRUSTED PRODUCT CONTEXT (JSON)\n" + json.dumps(context),
                    },
                    {"type": "text", "text": "UNTRUSTED PRODUCT IMAGE"},
                    image_block,
                ]
            ),
        ]
