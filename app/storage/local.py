import os
import aiofiles
from io import BytesIO

class LocalStorage:
    def __init__(self, path: str):
        self.path = path

    def _full_path(self, key: str) -> str:
        return os.path.join(self.path, key)

    async def save(self, data: bytes, path: str) -> None:
        full_path = self._full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(data)

    async def load(self, path: str) -> BytesIO:
        async with aiofiles.open(self._full_path(path), "rb") as f:
            return BytesIO(await f.read())

    async def delete(self, path: str) -> None:
        full_path = self._full_path(path)
        if os.path.exists(full_path):
            os.remove(full_path)
