"""Safe Celery task enqueue — avoids crashing HTTP requests when Redis is down."""

from __future__ import annotations

import logging
from typing import Any, Callable

from ai_engine.services.generation_mode import MODE_MANUAL

logger = logging.getLogger(__name__)


def safe_delay(
    task,
    *args,
    on_failure: Callable[[Exception], None] | None = None,
    **kwargs,
) -> Any | None:
    """
    Enqueue a Celery task without raising broker connection errors to the caller.

    Returns the AsyncResult when queued, or None when enqueue failed.
    """
    try:
        return task.delay(*args, **kwargs)
    except Exception as exc:
        task_name = getattr(task, "name", repr(task))
        logger.warning(
            "Could not enqueue Celery task %s: %s",
            task_name,
            exc,
            exc_info=True,
        )
        if on_failure:
            on_failure(exc)
        return None


def run_or_enqueue(
    task,
    *args,
    mode: str = "celery",
    on_failure: Callable[[Exception], None] | None = None,
    **kwargs,
) -> bool:
    """
    Run a task synchronously in manual mode, or enqueue via Celery otherwise.

    Returns True when the task ran or was queued successfully.
    """
    if mode == MODE_MANUAL:
        try:
            task.run(*args, **kwargs)
            return True
        except AttributeError:
            task(*args, **kwargs)
            return True
        except Exception as exc:
            logger.exception("Manual task execution failed: %s", exc)
            if on_failure:
                on_failure(exc)
            return False

    result = safe_delay(task, *args, on_failure=on_failure, **kwargs)
    return result is not None
