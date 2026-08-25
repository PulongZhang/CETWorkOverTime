import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.task_service import TaskActions, TaskManager


def test_fetch_and_sync_checks_scheduled_business_date() -> None:
    fetcher = MagicMock()
    fetcher.connect.return_value = True
    fetcher.fetch_emails.return_value = 0
    processor = MagicMock()
    processor.sync_to_db.return_value = {"saved": 0}

    with (
        patch("app.services.task_service.EmailFetcher", return_value=fetcher),
        patch("app.services.task_service.EmailProcessor", return_value=processor),
        patch.object(TaskActions, "_cleanup_eml_files", return_value=0),
        patch("app.services.task_service.work_plan_checker.check_for_date") as check,
    ):
        check.return_value = {"message": "已提交"}
        result = TaskActions().fetch_and_sync(365, "2026-08-25")

    check.assert_called_once_with("2026-08-25")
    assert "工作计划：已提交" in result


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
