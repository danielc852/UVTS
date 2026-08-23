from collections.abc import Mapping
from typing import Any

from uvts_api.ports.model_gateway import ModelOutput


class ModelGatewayNotConfiguredError(RuntimeError):
    pass


class NotConfiguredModelGateway:
    """Prevents accidental external model calls in the foundation application."""

    async def request_structured(
        self,
        *,
        prompt: str,
        output_type: type[ModelOutput],
        metadata: Mapping[str, Any],
    ) -> ModelOutput:
        del prompt, output_type, metadata
        raise ModelGatewayNotConfiguredError("OpenRouter integration is not configured")
