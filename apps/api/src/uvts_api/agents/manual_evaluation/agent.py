import base64
import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.content import create_image_block

from uvts_api.agents.errors import (
    EvaluatorOutputError,
    EvaluatorStructuredOutputError,
)
from uvts_api.agents.manual_evaluation.prompts import (
    EVALUATION_CORRECTION_PROMPT,
    EVALUATION_SYSTEM_PROMPT,
)
from uvts_api.agents.manual_evaluation.schemas import AtomicEvaluationOutput
from uvts_api.agents.manual_evaluation.validation import (
    ManualPage,
    normalize_pages,
    validate_and_fold_evaluation,
)
from uvts_api.agents.schemas import QuestionEvaluationOutput
from uvts_api.agents.structured_output import invoke_structured_output
from uvts_api.ports.question_generator import AgentProductImage
from uvts_api.schemas.workspace import Question


class ManualEvaluationAgent:
    """Evaluate one question using atomic, evidence-grounded requirements."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def evaluate(
        self,
        *,
        question: Question,
        manual_pages: Sequence[ManualPage],
        product_image: AgentProductImage | None = None,
        product_description: str = "",
    ) -> QuestionEvaluationOutput:
        pages = normalize_pages(manual_pages)
        messages = _messages(question, pages, product_description, product_image)
        try:
            output = await self._request(messages)
            return validate_and_fold_evaluation(output, pages)
        except (EvaluatorStructuredOutputError, EvaluatorOutputError):
            repaired = await self._request(
                [*messages, HumanMessage(content=EVALUATION_CORRECTION_PROMPT)]
            )
            return validate_and_fold_evaluation(repaired, pages)

    async def evaluate_question(
        self,
        *,
        question: Question,
        manual_pages: Sequence[ManualPage],
        product_image: AgentProductImage | None = None,
        product_description: str = "",
    ) -> QuestionEvaluationOutput:
        return await self.evaluate(
            question=question,
            manual_pages=manual_pages,
            product_image=product_image,
            product_description=product_description,
        )

    async def _request(self, messages: list[BaseMessage]) -> AtomicEvaluationOutput:
        return await invoke_structured_output(
            self._model,
            AtomicEvaluationOutput,
            messages,
        )


def _messages(
    question: Question,
    pages: Mapping[int, str],
    product_description: str,
    product_image: AgentProductImage | None,
) -> list[BaseMessage]:
    content: list[str | dict[Any, Any]] = [
        {"type": "text", "text": _evaluation_prompt(question, pages, product_description)}
    ]
    if product_image is not None:
        content.append(
            cast(
                dict[Any, Any],
                create_image_block(
                    base64=base64.b64encode(product_image.content).decode("ascii"),
                    mime_type=product_image.content_type,
                ),
            )
        )
    return [
        SystemMessage(content=EVALUATION_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ]


def _evaluation_prompt(
    question: Question,
    pages: Mapping[int, str],
    product_description: str,
) -> str:
    question_json = json.dumps(
        question.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    labelled_pages = "\n\n".join(
        f"[PAGE {page}]\n{text}\n[/PAGE {page}]" for page, text in sorted(pages.items())
    )
    return (
        "UNTRUSTED INTERPRETATION-ONLY PRODUCT CONTEXT (NOT EVIDENCE)\n"
        f"{product_description}\n\n"
        f"UNTRUSTED QUESTION RECORD\n{question_json}\n\n"
        f"UNTRUSTED MANUAL EVIDENCE SOURCE\n{labelled_pages}"
    )
