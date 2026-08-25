import threading
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.services.task_service import task_actions, task_manager
from app.services.work_plan_checker import AUTO_SUBMIT_DEADLINE

BEIJING_TZ = timezone(timedelta(hours=8))
FETCH_JOB = "scheduled"
AUTO_SUBMIT_JOB = "auto-submit"
AUTO_SUBMIT_TIME = "23:55"
AUTO_SUBMIT_RETRY_SECONDS = 30


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
    """返回严格晚于 now 的下一次北京时间调度时刻。"""
    hour, minute = (int(part) for part in schedule.split(":"))
    candidate = now.astimezone(BEIJING_TZ).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


class MailScheduler:
    def __init__(self) -> None:
        settings = get_settings()
        self.jobs = {
            FETCH_JOB: parse_time(settings.schedule_time),
            AUTO_SUBMIT_JOB: AUTO_SUBMIT_TIME,
        }
        self.schedule_times = list(self.jobs.values())
        self.auto_submit_retry_seconds = AUTO_SUBMIT_RETRY_SECONDS
        self._timers: dict[str, threading.Timer] = {}
        self._next_runs: dict[str, datetime] = {}
        self.next_run: str | None = None
        self.last_run: str | None = None
        self.last_result: str | None = None

    def start(self) -> None:
        if self._timers:
            return

        now = datetime.now().astimezone()
        missed_auto_submit_date: str | None = None
        for job, schedule in self.jobs.items():
            if job == AUTO_SUBMIT_JOB and self._should_catch_up(now, schedule):
                target = now + timedelta(seconds=1)
                business_date = self._business_date(now)
            else:
                if job == AUTO_SUBMIT_JOB and self._is_after_deadline(now):
                    missed_auto_submit_date = self._business_date(now)
                target = next_run_at(now, schedule)
                business_date = self._business_date(target)
            self._schedule_at(job, target, business_date, now=now)

        try:
            pending_dates = task_actions.pending_auto_submit_dates()
        except RuntimeError as error:
            pending_dates = []
            self.last_result = str(error)
        if pending_dates:
            try:
                task_manager.submit(
                    "auto-submit-recovery",
                    task_actions.resume_pending_work_plans,
                )
                self.last_result = f"正在恢复 {len(pending_dates)} 个工作计划发送状态"
            except RuntimeError as error:
                self.last_result = str(error)

        if missed_auto_submit_date:
            task_actions.notify_auto_submit_skipped(
                missed_auto_submit_date,
                "服务在自动提交安全截止时间后启动",
            )

    def stop(self) -> None:
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()
        self._next_runs.clear()
        self.next_run = None

    def status(self) -> dict:
        return {
            "enabled": bool(self._timers),
            "schedule_times": self.schedule_times,
            "next_run": self.next_run,
            "last_run": self.last_run,
            "last_result": self.last_result,
        }

    def _run(self, job: str, business_date: str) -> None:
        self._timers.pop(job, None)
        self._next_runs.pop(job, None)
        now = datetime.now().astimezone()
        self.last_run = now.isoformat(timespec="seconds")

        if job == AUTO_SUBMIT_JOB and self._business_date(now) != business_date:
            reason = "调度任务延迟至下一业务日，已取消旧日期的自动提交"
            self.last_result = f"{business_date} 自动提交未执行：{reason}"
            self._schedule_next(job, now)
            task_actions.notify_auto_submit_skipped(business_date, reason)
            return

        try:
            if job == FETCH_JOB:
                settings = get_settings()
                task_manager.submit(
                    FETCH_JOB,
                    lambda: task_actions.fetch_and_sync(
                        settings.imap_search_days,
                        business_date,
                    ),
                )
                self.last_result = "任务已启动"
            elif job == AUTO_SUBMIT_JOB:
                task_manager.submit(
                    AUTO_SUBMIT_JOB,
                    lambda: task_actions.auto_submit_work_plan(business_date),
                )
                self.last_result = "自动提交任务已启动"
            else:
                raise RuntimeError(f"未知调度任务: {job}")
        except RuntimeError as error:
            if job == AUTO_SUBMIT_JOB and self._business_date(now) == business_date:
                if self._schedule_auto_submit_retry(now, business_date, str(error)):
                    return
                self._schedule_next(job, now)
                task_actions.notify_auto_submit_skipped(business_date, str(error))
                return
            self.last_result = str(error)

        self._schedule_next(job, now)

    def _schedule_auto_submit_retry(
        self,
        now: datetime,
        business_date: str,
        reason: str,
    ) -> bool:
        deadline_hour, deadline_minute = (
            int(part) for part in AUTO_SUBMIT_DEADLINE.split(":")
        )
        deadline = now.astimezone(BEIJING_TZ).replace(
            hour=deadline_hour,
            minute=deadline_minute,
            second=0,
            microsecond=0,
        )
        last_attempt = deadline - timedelta(seconds=1)
        if now >= last_attempt:
            self.last_result = f"{business_date} 自动提交未执行：{reason}"
            return False

        retry_at = min(
            now + timedelta(seconds=self.auto_submit_retry_seconds),
            last_attempt,
        )
        retry_seconds = max((retry_at - now).total_seconds(), 1)
        self.last_result = f"{reason}，将在 {retry_seconds:g} 秒后重试"
        self._schedule_at(AUTO_SUBMIT_JOB, retry_at, business_date, now=now)
        return True

    def _schedule_next(self, job: str, now: datetime) -> None:
        target = next_run_at(now, self.jobs[job])
        self._schedule_at(job, target, self._business_date(target), now=now)

    def _schedule_at(
        self,
        job: str,
        target: datetime,
        business_date: str,
        *,
        now: datetime,
    ) -> None:
        seconds = max((target - now).total_seconds(), 1)
        timer = threading.Timer(seconds, self._run, args=(job, business_date))
        timer.daemon = True
        timer.start()
        self._timers[job] = timer
        self._next_runs[job] = target
        self._refresh_next_run()

    def _refresh_next_run(self) -> None:
        self.next_run = (
            min(self._next_runs.values()).isoformat(timespec="seconds")
            if self._next_runs
            else None
        )

    @staticmethod
    def _business_date(value: datetime) -> str:
        return value.astimezone(BEIJING_TZ).strftime("%Y-%m-%d")

    @staticmethod
    def _should_catch_up(now: datetime, schedule: str) -> bool:
        beijing_now = now.astimezone(BEIJING_TZ)
        scheduled_time = datetime.strptime(schedule, "%H:%M").time()
        deadline = datetime.strptime(AUTO_SUBMIT_DEADLINE, "%H:%M").time()
        return scheduled_time <= beijing_now.time() < deadline

    @staticmethod
    def _is_after_deadline(now: datetime) -> bool:
        deadline = datetime.strptime(AUTO_SUBMIT_DEADLINE, "%H:%M").time()
        return now.astimezone(BEIJING_TZ).time() >= deadline


mail_scheduler = MailScheduler()
