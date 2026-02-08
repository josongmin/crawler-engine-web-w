from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


def default_retry(*, max_attempts: int) -> Callable[[Callable[..., T]], Callable[..., T]]:
    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=0.5, max=10.0),
        retry=retry_if_exception_type(Exception),
    )
