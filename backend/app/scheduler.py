import threading
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.services.task_service import task_actions, task_manager


class MailScheduler:
    def __init__(self) -> None:
        self.interval_hours = get_settings().schedule_interval_hours
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
            "interval_hours": self.interval_hours,
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
        seconds = self.interval_hours * 60 * 60
        self.next_run = (
            datetime.now().astimezone() + timedelta(seconds=seconds)
        ).isoformat(timespec="seconds")
        self._timer = threading.Timer(seconds, self._run)
        self._timer.daemon = True
        self._timer.start()


mail_scheduler = MailScheduler()
