from functools import lru_cache

from app.storage.protocol import Storage
from app.config import get_settings

from .local import LocalStorage

@lru_cache
def get_storage() -> Storage:
    return LocalStorage(path=get_settings().STORAGE_PATH)