from pathlib import Path
from typing import Protocol


class DocumentStorage(Protocol):
    async def put(self, key: str, source: Path) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def local_path(self, key: str) -> Path: ...
