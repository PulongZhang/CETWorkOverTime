import threading
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.services.task_service import task_actions, task_manager

# 北京时间（UTC+8）固定时区
BEIJING_TZ = timezone(timedelta(hours=8))


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
        self.schedule_time = parse_time(get_settings().schedule_time)
        self._timer: threading.Timer | None = None
        self.next_run: str | None = None
        self.last_run: str | None = None
        self.last_result: str | None = None

    def start(self) -> None:
        if self._timer is None:
            self._schedule_next()

    def stop(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self.next_run = None

    def status(self) -> dict:
        return {
            "enabled": self._timer is not None,
            "schedule_time": self.schedule_time,
            "next_run": self.next_run,
            "last_run": self.last_run,
            "last_result": self.last_result,
        }

    def _run(self) -> None:
        self._timer = None
        self.last_run = datetime.now().astimezone().isoformat(timespec="seconds")
        try:
            settings = get_settings()
            task_manager.submit(
                "scheduled",
                lambda: task_actions.fetch_and_sync(settings.imap_search_days),
            )
            self.last_result = "任务已启动"
        except RuntimeError as error:
            self.last_result = str(error)
        finally:
            self._schedule_next()

    def _schedule_next(self) -> None:
        target = next_run_at(datetime.now().astimezone(), self.schedule_time)
        seconds = max((target - datetime.now().astimezone()).total_seconds(), 1)
        self.next_run = target.isoformat(timespec="seconds")
        self._timer = threading.Timer(seconds, self._run)
        self._timer.daemon = True
        self._timer.start()


mail_scheduler = MailScheduler()