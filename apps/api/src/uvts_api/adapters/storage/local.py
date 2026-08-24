import asyncio
import shutil
from pathlib import Path


class LocalDocumentStorage:
    """Private filesystem storage addressed only by generated server keys."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key or Path(key).name != key:
            raise ValueError("Invalid document storage key")
        return self._root / key

    async def put(self, key: str, source: Path) -> None:
        destination = self._path(key)
        temporary = destination.with_suffix(".pending")

        def copy() -> None:
            shutil.copyfile(source, temporary)
            temporary.replace(destination)

        await asyncio.to_thread(copy)

    async def delete(self, key: str) -> None:
        path = self._path(key)
        await asyncio.to_thread(path.unlink, missing_ok=True)

    async def local_path(self, key: str) -> Path:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path
