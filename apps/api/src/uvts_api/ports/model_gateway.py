from collections.abc import Mapping
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

ModelOutput = TypeVar("ModelOutput", bound=BaseModel)


class ModelGateway(Protocol):
    async def request_structured(
        self,
        *,
        prompt: str,
        output_type: type[ModelOutput],
        metadata: Mapping[str, Any],
    ) -> ModelOutput: ...
