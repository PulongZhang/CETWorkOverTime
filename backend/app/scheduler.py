import threading
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.services.task_service import task_actions, task_manager

# 北京时间（UTC+8）固定时区
BEIJING_TZ = timezone(timedelta(hours=8))

# 每日任务媒点：21:00 拉取+检查；23:55 未提交则自动提交+通知
SCHEDULE_TIMES = ["21:00", "23:55"]


def parse_time(value: str) -> str:
    """校验 SCHEDULE_TIME 配置为 HH:MM，返回规范格式。"""
    try:
        hour, minute = value.split(":")
        if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
            raise ValueError
    except ValueError as error:
        raise ValueError(f"SCHEDULE_TIME 格式非法: {value!r}，应为 HH:MM（如 21:00）") from error
    return f"{int(hour):02d}:{int(minute):02d}"


def next_run_at(now: datetime, schedule: str) -> datetime:
    """返回 now 之后（严格晚于 now）的下一次调度时刻（北京时间）。

    若调度的 HH:MM 已经过去，则顺延到明天同一时刻。
    """
    hour, minute = (int(part) for part in schedule.split(":"))
    candidate = now.astimezone(BEIJING_TZ).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


class MailScheduler:
    def __init__(self) -> None:
        self.schedule_times = [parse_time(value) for value in SCHEDULE_TIMES]
        self._timers: dict[str, threading.Timer] = {}
        self.next_run: str | None = None
        self.last_run: str | None = None
        self.last_result: str | None = None

    def start(self) -> None:
        if not self._timers:
            now = datetime.now().astimezone()
            for schedule in self.schedule_times:
                target = next_run_at(now, schedule)
                seconds = max((target - now).total_seconds(), 1)
                timer = threading.Timer(seconds, self._run, args=(schedule,))
                timer.daemon = True
                timer.start()
                self._timers[schedule] = timer
            self.next_run = min(
                (next_run_at(now, s) for s in self.schedule_times)
            ).isoformat(timespec="seconds")

    def stop(self) -> None:
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()
        self.next_run = None

    def status(self) -> dict:
        return {
            "enabled": bool(self._timers),
            "schedule_times": self.schedule_times,
            "next_run": self.next_run,
            "last_run": self.last_run,
            "last_result": self.last_result,
        }

    def _run(self, schedule: str) -> None:
        self._timers.pop(schedule, None)
        self.last_run = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            if schedule == "21:00":
                settings = get_settings()
                task_manager.submit(
                    "scheduled",
                    lambda: task_actions.fetch_and_sync(settings.imap_search_days),
                )
                self.last_result = "任务已启动"
            elif schedule == "23:55":
                task_manager.submit(
                    "auto-submit",
                    lambda: task_actions.auto_submit_work_plan(),
                )
                self.last_result = "自动提交任务已启动"
        except RuntimeError as error:
            self.last_result = str(error)
        finally:
            # 重新排队下一次（次日同一时刻）
            now = datetime.now().astimezone()
            target = next_run_at(now, schedule)
            seconds = max((target - now).total_seconds(), 1)
            timer = threading.Timer(seconds, self._run, args=(schedule,))
            timer.daemon = True
            timer.start()
            self._timers[schedule] = timer
            self.next_run = min(
                (next_run_at(now, s) for s in self.schedule_times)
            ).isoformat(timespec="seconds")


mail_scheduler = MailScheduler()