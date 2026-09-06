from fastapi import HTTPException


class NotFoundError(HTTPException):
    """Requested entity does not exist."""

    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(status_code=404, detail=detail)


class ConflictError(HTTPException):
    """Request conflicts with the current state."""

    def __init__(self, detail: str = "Conflict") -> None:
        super().__init__(status_code=409, detail=detail)
