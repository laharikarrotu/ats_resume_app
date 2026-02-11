"""
Lightweight async task queue for background processing.

Uses asyncio — no Redis/Celery dependency for simple deployments.
Upgrade path: swap TaskQueue with a Celery/ARQ adapter when needed.
"""

from .queue import task_queue, TaskStatus, TaskResult

__all__ = ["task_queue", "TaskStatus", "TaskResult"]
