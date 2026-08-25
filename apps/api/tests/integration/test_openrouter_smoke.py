import base64
import os

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from uvts_api.adapters.ai.openrouter import build_openrouter_model
from uvts_api.agents.manual_evaluation import ManualEvaluationAgent
from uvts_api.agents.question_generation import QuestionAgent
from uvts_api.core.config import Settings
from uvts_api.ports.question_generator import (
    AgentProductImage,
    QuestionDesign,
    QuestionGenerationInput,
)
from uvts_api.schemas.workspace import Question


class SmokeOutput(BaseModel):
    status: str


@pytest.mark.openrouter
@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("UVTS_RUN_OPENROUTER_SMOKE") != "1"
    or not os.environ.get("OPENROUTER_API_KEY"),
    reason="Set UVTS_RUN_OPENROUTER_SMOKE=1 and OPENROUTER_API_KEY to run this live test.",
)
async def test_openrouter_structured_output_smoke() -> None:
    settings = Settings()
    model = build_openrouter_model(settings)
    structured_model = model.with_structured_output(
        SmokeOutput, method="json_schema", strict=True
    )

    result = await structured_model.ainvoke(
        [
            SystemMessage(content="Return only the requested structured result."),
            HumanMessage(content="Set status to ready."),
        ]
    )

    assert SmokeOutput.model_validate(result).status == "ready"


@pytest.mark.openrouter
@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("UVTS_RUN_OPENROUTER_SMOKE") != "1"
    or not os.environ.get("OPENROUTER_API_KEY"),
    reason="Set UVTS_RUN_OPENROUTER_SMOKE=1 and OPENROUTER_API_KEY to run this live test.",
)
async def test_openrouter_question_and_evaluation_agents_smoke() -> None:
    model = build_openrouter_model(Settings())
    question_agent = QuestionAgent(model)
    tiny_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    questions = await question_agent.generate(
        QuestionGenerationInput(
            product_image=AgentProductImage(
                content=tiny_png,
                content_type="image/png",
                filename="sensor.png",
            ),
            product_description="A portable temperature sensor with one status light.",
            question_design=QuestionDesign(total_questions=2),
        )
    )

    assert len(questions.questions) == 2
    evaluator = ManualEvaluationAgent(model)
    result = await evaluator.evaluate_question(
        question=Question(id="q-smoke", text="How do I know when setup is complete?"),
        manual_pages=[
            {
                "page": 1,
                "text": "The status light turns green when setup is complete.",
            }
        ],
        product_description="A portable temperature sensor with one status light.",
    )

    assert result.status == "found"
    assert result.evidence
    assert result.evidence[0].page == 1
