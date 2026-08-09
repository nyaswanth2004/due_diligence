import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TaskQueue:
    """Async task execution boundary.

    Phase 1 ships an in-process thread pool so the ingestion pipeline runs
    without external infra. Swap the implementation for a Redis/Celery-backed
    queue in production without touching callers.
    """

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="ingest"
        )
        self._started = True

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        if not self._started:
            logger.warning("queue is shut down; dropping task %s", getattr(fn, "__name__", fn))
            return
        self._executor.submit(self._guard, fn, *args, **kwargs)

    def _guard(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        try:
            fn(*args, **kwargs)
        except Exception:
            logger.exception("background task failed: %s", getattr(fn, "__name__", fn))

    def shutdown(self) -> None:
        self._started = False
        self._executor.shutdown(wait=True)


_task_queue: TaskQueue | None = None


def get_task_queue() -> TaskQueue:
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue


def shutdown_task_queue() -> None:
    global _task_queue
    if _task_queue is not None:
        _task_queue.shutdown()
        _task_queue = None
