from typing import Protocol
from io import BytesIO

class Storage(Protocol):
    async def save(self, data, path):
        ...

    async def load(self, path) -> BytesIO:
        ...

    async def delete(self, path) -> None:
        ...
