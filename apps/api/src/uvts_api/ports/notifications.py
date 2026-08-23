from collections.abc import AsyncIterator
from typing import Protocol


class StateNotifications(Protocol):
    async def publish(self, test_id: str) -> None: ...

    def listen(self, test_id: str) -> AsyncIterator[None]: ...
