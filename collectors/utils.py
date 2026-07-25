import asyncio
import logging
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    **kwargs: Any
) -> Any:
    """
    Executes an async function with exponential backoff retry logic.
    """
    delay = initial_delay
    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if attempt == retries - 1:
                logger.error(
                    f"All {retries} retry attempts failed for {func.__name__} due to: {e}"
                )
                raise e
            logger.warning(
                f"Attempt {attempt + 1}/{retries} failed for {func.__name__} due to: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)
            delay *= backoff_factor
