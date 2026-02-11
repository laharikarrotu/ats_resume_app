"""Tests for the async task queue."""

import asyncio
import pytest
from src.tasks.queue import TaskQueue, TaskStatus


@pytest.fixture()
def queue():
    """Fresh task queue for each test."""
    return TaskQueue(max_concurrency=2, result_ttl_seconds=60)


@pytest.mark.asyncio
class TestTaskQueue:
    async def test_submit_and_complete(self, queue):
        async def add(a, b):
            return a + b

        task_id = await queue.submit(add, 3, 4)
        # Give it time to complete
        await asyncio.sleep(0.1)

        result = queue.get_result(task_id)
        assert result is not None
        assert result.status == TaskStatus.COMPLETED
        assert result.result == 7
        assert result.duration_seconds >= 0

    async def test_submit_custom_id(self, queue):
        async def noop():
            pass

        task_id = await queue.submit(noop, task_id="custom-123")
        assert task_id == "custom-123"
        await asyncio.sleep(0.1)
        assert queue.get_status(task_id) == TaskStatus.COMPLETED

    async def test_failed_task(self, queue):
        async def failing():
            raise ValueError("Something went wrong")

        task_id = await queue.submit(failing)
        await asyncio.sleep(0.1)

        result = queue.get_result(task_id)
        assert result.status == TaskStatus.FAILED
        assert "ValueError" in result.error

    async def test_concurrency_limit(self, queue):
        results = []

        async def slow_task(n):
            await asyncio.sleep(0.05)
            results.append(n)
            return n

        # Submit 4 tasks with concurrency=2
        ids = []
        for i in range(4):
            tid = await queue.submit(slow_task, i)
            ids.append(tid)

        # Wait for all to complete (4 tasks, 2 concurrent, 0.05s each = ~0.1s + margin)
        await asyncio.sleep(0.5)

        for tid in ids:
            assert queue.get_status(tid) == TaskStatus.COMPLETED
        assert len(results) == 4

    async def test_list_tasks(self, queue):
        async def noop():
            pass

        await queue.submit(noop)
        await queue.submit(noop)
        await asyncio.sleep(0.1)

        tasks = queue.list_tasks()
        assert len(tasks) == 2

    async def test_list_tasks_by_status(self, queue):
        async def noop():
            pass

        await queue.submit(noop)
        await asyncio.sleep(0.1)

        completed = queue.list_tasks(status=TaskStatus.COMPLETED)
        assert len(completed) >= 1
        pending = queue.list_tasks(status=TaskStatus.PENDING)
        assert len(pending) == 0

    async def test_stats(self, queue):
        async def noop():
            pass

        await queue.submit(noop)
        await asyncio.sleep(0.1)

        stats = queue.stats
        assert stats["total_tasks"] == 1
        assert stats["max_concurrency"] == 2
        assert "completed" in stats["by_status"]

    async def test_get_nonexistent(self, queue):
        assert queue.get_status("nope") is None
        assert queue.get_result("nope") is None

    async def test_cleanup(self, queue):
        queue._result_ttl = 0  # Expire immediately

        async def noop():
            pass

        await queue.submit(noop)
        await asyncio.sleep(0.1)

        removed = queue.cleanup_old_tasks()
        assert removed >= 1
        assert queue.stats["total_tasks"] == 0

    async def test_cancel(self, queue):
        async def long_task():
            await asyncio.sleep(10)

        task_id = await queue.submit(long_task)
        await asyncio.sleep(0.05)  # Let it start

        cancelled = await queue.cancel(task_id)
        assert cancelled is True
        await asyncio.sleep(0.1)

        status = queue.get_status(task_id)
        assert status == TaskStatus.CANCELLED
