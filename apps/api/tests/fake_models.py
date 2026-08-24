from typing import Any

from langchain_core.messages import BaseMessage
from pydantic import BaseModel


class FakeStructuredChatModel:
    """Small fake for the BaseChatModel structured-output surface used by agents."""

    def __init__(self, response: BaseModel | Exception) -> None:
        self.response = response
        self.schema: type[BaseModel] | None = None
        self.method: str | None = None
        self.strict: bool | None = None
        self.invocations: list[list[BaseMessage]] = []

    def with_structured_output(
        self,
        schema: type[BaseModel],
        *,
        method: str,
        strict: bool,
        **kwargs: Any,
    ) -> "FakeStructuredChatModel":
        del kwargs
        self.schema = schema
        self.method = method
        self.strict = strict
        return self

    async def ainvoke(self, messages: list[BaseMessage]) -> BaseModel:
        self.invocations.append(messages)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response
