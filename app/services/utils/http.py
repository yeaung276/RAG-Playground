import logging

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
RETRY_BACKOFF = 1.0


def is_retryable(exc: BaseException) -> bool:
    """Transient HTTP failures worth retrying: 429/5xx responses and transport errors."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRY_STATUS
    return isinstance(exc, httpx.TransportError)


def http_retry(logger: logging.Logger):
    """Shared tenacity policy for httpx calls: exponential backoff on transient failures."""
    return retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_BACKOFF, max=30),
        retry=retry_if_exception(is_retryable),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
