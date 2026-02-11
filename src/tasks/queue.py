"""
Async Task Queue — background task processing with Supabase persistence.

Tasks are executed in-process via asyncio, but their state (status, result,
errors) is persisted to Supabase so it survives server restarts.

On startup, any tasks that were 'running' or 'pending' are marked as 'failed'
(the server crashed before they could finish).

Usage:
    from src.tasks import task_queue

    # Submit a task
    task_id = await task_queue.submit(my_async_func, arg1, arg2)

    # Check status (checks memory first, falls back to Supabase)
    status = task_queue.get_status(task_id)

    # Get result
    result = task_queue.get_result(task_id)
"""

import asyncio
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import uuid4

from ..logger import logger


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """Result of a completed (or failed) task."""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    created_at: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_seconds: float = 0.0


@dataclass
class _TaskEntry:
    """Internal task tracking entry."""
    task_id: str
    func: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    completed_at: float = 0.0
    asyncio_task: Optional[asyncio.Task] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskQueue:
    """
    Async task queue with Supabase persistence.

    - Tasks run in-process via asyncio
    - State is persisted to Supabase `tasks` table
    - On cache miss, falls back to Supabase lookup
    - On startup, stale tasks are marked as failed
    """

    def __init__(self, max_concurrency: int = 3, result_ttl_seconds: int = 3600):
        self._tasks: Dict[str, _TaskEntry] = {}
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._max_concurrency = max_concurrency
        self._result_ttl = result_ttl_seconds

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Lazily create semaphore in the current event loop."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrency)
        return self._semaphore

    def _persist_new(self, task_id: str, func_name: str) -> None:
        """Persist a new task to Supabase (fire-and-forget)."""
        try:
            from ..db import save_task
            save_task(task_id=task_id, func_name=func_name, status="pending")
        except Exception:
            pass  # DB persistence is best-effort

    def _persist_update(self, entry: _TaskEntry) -> None:
        """Persist task status update to Supabase (fire-and-forget)."""
        try:
            from ..db import update_task
            update_task(
                task_id=entry.task_id,
                status=entry.status.value,
                result=entry.result if entry.status == TaskStatus.COMPLETED else None,
                error=entry.error,
                started_at=datetime.fromtimestamp(entry.started_at, tz=timezone.utc).isoformat() if entry.started_at else None,
                completed_at=datetime.fromtimestamp(entry.completed_at, tz=timezone.utc).isoformat() if entry.completed_at else None,
            )
        except Exception:
            pass  # DB persistence is best-effort

    async def submit(
        self,
        func: Callable[..., Coroutine],
        *args: Any,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Submit an async function for background execution.

        Returns:
            Task ID string
        """
        if task_id is None:
            task_id = f"task_{uuid4().hex[:12]}"

        entry = _TaskEntry(
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs,
        )
        self._tasks[task_id] = entry

        # Persist to Supabase
        self._persist_new(task_id, func.__name__)

        # Schedule execution
        entry.asyncio_task = asyncio.create_task(self._execute(entry))

        logger.info("Task submitted: %s (%s)", task_id, func.__name__)
        return task_id

    async def _execute(self, entry: _TaskEntry) -> None:
        """Execute a task with concurrency control."""
        async with self._get_semaphore():
            entry.status = TaskStatus.RUNNING
            entry.started_at = time.time()
            self._persist_update(entry)

            try:
                entry.result = await entry.func(*entry.args, **entry.kwargs)
                entry.status = TaskStatus.COMPLETED
                logger.info(
                    "Task completed: %s (%.2fs)",
                    entry.task_id,
                    time.time() - entry.started_at,
                )
            except asyncio.CancelledError:
                entry.status = TaskStatus.CANCELLED
                logger.warning("Task cancelled: %s", entry.task_id)
            except Exception as exc:
                entry.status = TaskStatus.FAILED
                entry.error = f"{type(exc).__name__}: {exc}"
                logger.error(
                    "Task failed: %s — %s",
                    entry.task_id,
                    entry.error,
                    exc_info=True,
                )
            finally:
                entry.completed_at = time.time()
                self._persist_update(entry)

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the current status of a task (memory first, then Supabase)."""
        # Check in-memory first
        entry = self._tasks.get(task_id)
        if entry:
            return entry.status

        # Fall back to Supabase
        try:
            from ..db import get_task_db
            row = get_task_db(task_id)
            if row:
                return TaskStatus(row["status"])
        except Exception:
            pass

        return None

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """Get the full result of a task (memory first, then Supabase)."""
        # Check in-memory first
        entry = self._tasks.get(task_id)
        if entry:
            return TaskResult(
                task_id=entry.task_id,
                status=entry.status,
                result=entry.result if entry.status == TaskStatus.COMPLETED else None,
                error=entry.error,
                created_at=entry.created_at,
                started_at=entry.started_at,
                completed_at=entry.completed_at,
                duration_seconds=round(
                    (entry.completed_at - entry.started_at) if entry.completed_at else 0, 3
                ),
            )

        # Fall back to Supabase
        try:
            from ..db import get_task_db
            row = get_task_db(task_id)
            if row:
                return TaskResult(
                    task_id=row["task_id"],
                    status=TaskStatus(row["status"]),
                    result=row.get("result"),
                    error=row.get("error"),
                    created_at=0,  # Timestamps are ISO strings in DB
                    started_at=0,
                    completed_at=0,
                    duration_seconds=0,
                )
        except Exception:
            pass

        return None

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running or pending task."""
        entry = self._tasks.get(task_id)
        if not entry:
            return False

        if entry.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            if entry.asyncio_task:
                entry.asyncio_task.cancel()
            entry.status = TaskStatus.CANCELLED
            entry.completed_at = time.time()
            self._persist_update(entry)
            return True

        return False

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
    ) -> List[TaskResult]:
        """List tasks from memory. For historical tasks, use list_tasks_from_db()."""
        entries = list(self._tasks.values())
        if status:
            entries = [e for e in entries if e.status == status]

        # Sort by created_at descending
        entries.sort(key=lambda e: e.created_at, reverse=True)
        entries = entries[:limit]

        return [
            TaskResult(
                task_id=e.task_id,
                status=e.status,
                result=None,  # Don't include large results in listing
                error=e.error,
                created_at=e.created_at,
                started_at=e.started_at,
                completed_at=e.completed_at,
                duration_seconds=round(
                    (e.completed_at - e.started_at) if e.completed_at else 0, 3
                ),
            )
            for e in entries
        ]

    def list_tasks_from_db(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """List tasks from Supabase (includes historical tasks from previous server runs)."""
        try:
            from ..db import list_tasks_db
            return list_tasks_db(status=status, limit=limit)
        except Exception:
            return []

    def cleanup_old_tasks(self) -> int:
        """Remove completed/failed tasks older than TTL from memory."""
        now = time.time()
        to_remove = []

        for task_id, entry in self._tasks.items():
            if entry.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                if entry.completed_at and (now - entry.completed_at) > self._result_ttl:
                    to_remove.append(task_id)

        for task_id in to_remove:
            del self._tasks[task_id]

        return len(to_remove)

    def startup_cleanup(self) -> None:
        """Mark stale tasks from previous server run as failed. Call on app startup."""
        try:
            from ..db import mark_stale_tasks_failed
            mark_stale_tasks_failed()
        except Exception as exc:
            logger.warning("Task startup cleanup failed: %s", exc)

    @property
    def stats(self) -> dict:
        """Get queue statistics."""
        statuses = {}
        for entry in self._tasks.values():
            statuses[entry.status.value] = statuses.get(entry.status.value, 0) + 1

        return {
            "total_tasks": len(self._tasks),
            "max_concurrency": self._max_concurrency,
            "by_status": statuses,
        }


# ── Module-level singleton ──

task_queue = TaskQueue(max_concurrency=3, result_ttl_seconds=3600)
