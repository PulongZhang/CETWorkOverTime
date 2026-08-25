from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import app.scheduler as scheduler_module
from app.scheduler import AUTO_SUBMIT_JOB, BEIJING_TZ, FETCH_JOB, MailScheduler

PLAN_DATE = "2026-08-25"


class FakeTimer:
    created: list["FakeTimer"] = []

    def __init__(self, seconds: float, callback, args: tuple = ()) -> None:
        self.seconds = seconds
        self.callback = callback
        self.args = args
        self.daemon = False
        self.cancelled = False
        self.__class__.created.append(self)

    def start(self) -> None:
        pass

    def cancel(self) -> None:
        self.cancelled = True


class FrozenDateTime(datetime):
    current = datetime(2026, 8, 25, 20, 0, tzinfo=BEIJING_TZ)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.current
        return cls.current.astimezone(tz)


def _scheduler(schedule_time: str = "21:00") -> MailScheduler:
    with patch.object(
        scheduler_module,
        "get_settings",
        return_value=SimpleNamespace(schedule_time=schedule_time, imap_search_days=365),
    ):
        return MailScheduler()


def test_scheduler_uses_configured_fetch_time() -> None:
    scheduler = _scheduler("22:30")

    assert scheduler.status()["schedule_times"] == ["22:30", "23:55"]
    assert scheduler.jobs[FETCH_JOB] == "22:30"
    assert scheduler.jobs[AUTO_SUBMIT_JOB] == "23:55"


def test_start_after_auto_submit_time_runs_same_day_catchup() -> None:
    FakeTimer.created.clear()
    FrozenDateTime.current = datetime(2026, 8, 25, 23, 56, tzinfo=BEIJING_TZ)
    scheduler = _scheduler()

    with (
        patch.object(scheduler_module, "datetime", FrozenDateTime),
        patch.object(scheduler_module.threading, "Timer", FakeTimer),
    ):
        scheduler.start()

    auto_timer = next(timer for timer in FakeTimer.created if timer.args[0] == AUTO_SUBMIT_JOB)
    assert auto_timer.seconds == 1
    assert auto_timer.args == (AUTO_SUBMIT_JOB, PLAN_DATE)


def test_start_after_safe_deadline_skips_today_and_schedules_tomorrow() -> None:
    FakeTimer.created.clear()
    FrozenDateTime.current = datetime(2026, 8, 25, 23, 59, 1, tzinfo=BEIJING_TZ)
    scheduler = _scheduler()

    with (
        patch.object(scheduler_module, "datetime", FrozenDateTime),
        patch.object(scheduler_module.threading, "Timer", FakeTimer),
        patch.object(scheduler_module.task_actions, "notify_auto_submit_skipped") as notify,
    ):
        scheduler.start()

    auto_timer = next(timer for timer in FakeTimer.created if timer.args[0] == AUTO_SUBMIT_JOB)
    assert auto_timer.args == (AUTO_SUBMIT_JOB, "2026-08-26")
    notify.assert_called_once_with(PLAN_DATE, "服务在自动提交安全截止时间后启动")


def test_start_after_deadline_still_submits_pending_state_recovery() -> None:
    FakeTimer.created.clear()
    FrozenDateTime.current = datetime(2026, 8, 25, 23, 59, 1, tzinfo=BEIJING_TZ)
    scheduler = _scheduler()

    with (
        patch.object(scheduler_module, "datetime", FrozenDateTime),
        patch.object(scheduler_module.threading, "Timer", FakeTimer),
        patch.object(
            scheduler_module.task_actions,
            "pending_auto_submit_dates",
            return_value=[PLAN_DATE],
        ),
        patch.object(scheduler_module.task_manager, "submit", return_value={}) as submit,
        patch.object(scheduler_module.task_actions, "notify_auto_submit_skipped"),
    ):
        scheduler.start()

    submit.assert_called_once_with(
        "auto-submit-recovery",
        scheduler_module.task_actions.resume_pending_work_plans,
    )


def test_busy_auto_submit_retries_within_same_business_day() -> None:
    FakeTimer.created.clear()
    FrozenDateTime.current = datetime(2026, 8, 25, 23, 55, 1, tzinfo=BEIJING_TZ)
    scheduler = _scheduler()

    with (
        patch.object(scheduler_module, "datetime", FrozenDateTime),
        patch.object(scheduler_module.threading, "Timer", FakeTimer),
        patch.object(
            scheduler_module.task_manager,
            "submit",
            side_effect=RuntimeError("已有任务在运行中，请稍后重试"),
        ),
        patch.object(scheduler_module.task_actions, "notify_auto_submit_skipped") as notify,
    ):
        scheduler._run(AUTO_SUBMIT_JOB, PLAN_DATE)

    retry = FakeTimer.created[-1]
    assert retry.seconds == scheduler.auto_submit_retry_seconds
    assert retry.args == (AUTO_SUBMIT_JOB, PLAN_DATE)
    assert "重试" in (scheduler.last_result or "")
    notify.assert_not_called()


def test_busy_retry_is_capped_before_safe_deadline() -> None:
    FakeTimer.created.clear()
    FrozenDateTime.current = datetime(2026, 8, 25, 23, 58, 40, tzinfo=BEIJING_TZ)
    scheduler = _scheduler()

    with (
        patch.object(scheduler_module, "datetime", FrozenDateTime),
        patch.object(scheduler_module.threading, "Timer", FakeTimer),
        patch.object(
            scheduler_module.task_manager,
            "submit",
            side_effect=RuntimeError("已有任务在运行中，请稍后重试"),
        ),
        patch.object(scheduler_module.task_actions, "notify_auto_submit_skipped") as notify,
    ):
        scheduler._run(AUTO_SUBMIT_JOB, PLAN_DATE)

    retry = FakeTimer.created[-1]
    assert retry.seconds == 19
    assert retry.args == (AUTO_SUBMIT_JOB, PLAN_DATE)
    notify.assert_not_called()


def test_expired_auto_submit_is_not_run_for_the_next_day() -> None:
    FakeTimer.created.clear()
    FrozenDateTime.current = datetime(2026, 8, 26, 0, 0, 1, tzinfo=BEIJING_TZ)
    scheduler = _scheduler()

    with (
        patch.object(scheduler_module, "datetime", FrozenDateTime),
        patch.object(scheduler_module.threading, "Timer", FakeTimer),
        patch.object(scheduler_module.task_manager, "submit") as submit,
        patch.object(scheduler_module.task_actions, "notify_auto_submit_skipped") as notify,
    ):
        scheduler._run(AUTO_SUBMIT_JOB, PLAN_DATE)

    submit.assert_not_called()
    notify.assert_called_once()
    assert notify.call_args.args[0] == PLAN_DATE
    assert "未执行" in (scheduler.last_result or "")
    next_auto = FakeTimer.created[-1]
    assert next_auto.args[0] == AUTO_SUBMIT_JOB
    assert next_auto.args[1] == "2026-08-26"


def test_fetch_action_receives_scheduled_business_date() -> None:
    FrozenDateTime.current = datetime(2026, 8, 25, 23, 59, 50, tzinfo=BEIJING_TZ)
    scheduler = _scheduler("23:59")
    captured_action = None

    def capture_submit(_task_type: str, action):
        nonlocal captured_action
        captured_action = action
        return {}

    with (
        patch.object(scheduler_module, "datetime", FrozenDateTime),
        patch.object(scheduler_module.threading, "Timer", FakeTimer),
        patch.object(scheduler_module.task_manager, "submit", side_effect=capture_submit),
        patch.object(scheduler_module.task_actions, "fetch_and_sync", return_value="完成") as fetch,
    ):
        scheduler._run(FETCH_JOB, PLAN_DATE)
        assert captured_action is not None
        captured_action()

    fetch.assert_called_once_with(365, PLAN_DATE)


def test_auto_submit_action_receives_scheduled_business_date() -> None:
    FrozenDateTime.current = datetime(2026, 8, 25, 23, 59, 50, tzinfo=BEIJING_TZ)
    scheduler = _scheduler()
    captured_action = None

    def capture_submit(_task_type: str, action):
        nonlocal captured_action
        captured_action = action
        return {}

    with (
        patch.object(scheduler_module, "datetime", FrozenDateTime),
        patch.object(scheduler_module.threading, "Timer", FakeTimer),
        patch.object(scheduler_module.task_manager, "submit", side_effect=capture_submit),
        patch.object(
            scheduler_module.task_actions, "auto_submit_work_plan", return_value="完成"
        ) as auto_submit,
    ):
        scheduler._run(AUTO_SUBMIT_JOB, PLAN_DATE)
        assert captured_action is not None
        captured_action()

    auto_submit.assert_called_once_with(PLAN_DATE)


def test_stop_cancels_all_registered_timers() -> None:
    scheduler = _scheduler()
    first = MagicMock()
    second = MagicMock()
    scheduler._timers = {FETCH_JOB: first, AUTO_SUBMIT_JOB: second}

    scheduler.stop()

    first.cancel.assert_called_once_with()
    second.cancel.assert_called_once_with()
    assert scheduler.status()["enabled"] is False
