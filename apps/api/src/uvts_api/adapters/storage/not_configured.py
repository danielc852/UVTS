from pathlib import Path


class StorageNotConfiguredError(RuntimeError):
    pass


class NotConfiguredDocumentStorage:
    """Explicit placeholder until document upload is implemented."""

    async def put(self, key: str, source: Path) -> None:
        raise StorageNotConfiguredError("Document storage is not configured")

    async def delete(self, key: str) -> None:
        raise StorageNotConfiguredError("Document storage is not configured")

    async def local_path(self, key: str) -> Path:
        raise StorageNotConfiguredError("Document storage is not configured")
