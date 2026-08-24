import os

import pytest
from pydantic import BaseModel

from uvts_api.adapters.ai.openrouter import build_model_gateway
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
    gateway = build_model_gateway(settings)

    result = await gateway.request_structured(
        agent_name="openrouter_smoke",
        system_prompt="Return only the requested structured result.",
        prompt="Set status to ready.",
        output_type=SmokeOutput,
        metadata={"test_id": "smoke"},
    )

    assert result.status == "ready"
