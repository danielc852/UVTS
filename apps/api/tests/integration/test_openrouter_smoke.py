import os

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from uvts_api.adapters.ai.openrouter import build_openrouter_model
from uvts_api.core.config import Settings


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
