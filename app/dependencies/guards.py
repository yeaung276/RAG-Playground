from fastapi import HTTPException

from app.config import get_settings


def dev_only():
    settings = get_settings()
    if settings.ENV != "DEV":
        raise HTTPException(status_code=404)