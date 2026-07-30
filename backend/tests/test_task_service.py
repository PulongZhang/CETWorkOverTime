import threading
import time

import pytest

from app.services.task_service import TaskManager


def test_task_manager_allows_only_one_task_and_records_result() -> None:
    started = threading.Event()
    release = threading.Event()
    manager = TaskManager()

    def action() -> str:
        started.set()
        release.wait(timeout=2)
        return "完成"

    manager.submit("test", action)
    assert started.wait(timeout=2)

    with pytest.raises(RuntimeError, match="已有任务"):
        manager.submit("second", lambda: "不应执行")

    release.set()
    deadline = time.monotonic() + 2
    while manager.status()["running"] and time.monotonic() < deadline:
        time.sleep(0.01)

    assert manager.status()["message"] == "完成"
    assert manager.status()["finished_at"] is not None
    manager.shutdown()
