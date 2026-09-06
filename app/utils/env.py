import os


def require_env(name: str) -> str:
    """Read an environment variable, raising if it is unset or empty."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value
