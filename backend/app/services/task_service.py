import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Callable

from app import legacy_config as config
from app.services.email_fetcher import EmailFetcher
from app.services.email_processor import EmailProcessor
from app.services.work_plan_checker import work_plan_checker


class TaskActions:
    def fetch_and_sync(self, days: int) -> str:
        fetcher = EmailFetcher(save_dir=config.WORK_SUMMARY_DIR)
        if not fetcher.connect():
            raise RuntimeError("连接邮箱失败，请检查 IMAP 配置")
        try:
            downloaded = fetcher.fetch_emails(days=days)
        finally:
            fetcher.disconnect()

        stats = EmailProcessor(config.WORK_SUMMARY_DIR).sync_to_db()
        cleaned = self._cleanup_eml_files()
        result = (
            f"下载 {downloaded} 封，入库 {stats.get('saved', 0)} 封，"
            f"清理 {cleaned} 个文件"
        )

        # 检查当天是否提交了工作计划（未提交时自动发提醒）
        plan = work_plan_checker.check_today()
        return f"{result}；工作计划：{plan['message']}"

    def process(self, force: bool = False) -> str:
        processor = EmailProcessor(config.WORK_SUMMARY_DIR)
        if force:
            cache_path = config.OUTPUT_DIR / config.CACHE_FILENAME
            if cache_path.exists():
                cache_path.unlink()
        if not processor.process_emails_for_months(None, incremental=not force):
            raise RuntimeError("报告生成失败，请查看服务日志")
        return "报告生成完成"

    @staticmethod
    def _cleanup_eml_files() -> int:
        if not config.CLEANUP_EML_AFTER_SYNC:
            return 0
        files = list(config.WORK_SUMMARY_DIR.glob(f"*{config.EMAIL_FILE_EXTENSION}"))
        for file in files:
            file.unlink()
        return len(files)


class TaskManager:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mail-task")
        self._lock = threading.Lock()
        self._status = self._empty_status()

    def submit(self, task_type: str, action: Callable[[], str]) -> dict:
        with self._lock:
            if self._status["running"]:
                raise RuntimeError("已有任务在运行中，请稍后重试")
            self._status = {
                "running": True,
                "type": task_type,
                "message": "任务已启动",
                "started_at": self._now(),
                "finished_at": None,
            }
        self._executor.submit(self._execute, action)
        return self.status()

    def status(self) -> dict:
        with self._lock:
            return dict(self._status)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _execute(self, action: Callable[[], str]) -> None:
        try:
            message = action()
        except Exception as error:
            message = f"任务失败: {error}"
        with self._lock:
            self._status["running"] = False
            self._status["message"] = message
            self._status["finished_at"] = self._now()

    @staticmethod
    def _empty_status() -> dict:
        return {
            "running": False,
            "type": None,
            "message": "",
            "started_at": None,
            "finished_at": None,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")


task_actions = TaskActions()
task_manager = TaskManager()
