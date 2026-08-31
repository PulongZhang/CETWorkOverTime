"""轻量工作日历：周末规则、法定节假日、调休补班和个人请假。"""

import json
import threading
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

from app.core.config import get_settings

CONFIG_FILENAME = "work_calendar.json"
DEFAULT_CONFIG_PATH = Path(__file__).with_name("work_calendar.default.json")
CONFIG_KEYS = ("holidays", "makeup_workdays", "leave_dates")
MAX_LEAVE_RANGE_DAYS = 366


@dataclass(frozen=True)
class WorkdayDecision:
    date: str
    required: bool
    kind: str
    reason: str


class WorkCalendar:
    """从 OUTPUT_DIR 下的 JSON 文件读取工作日历并维护个人请假。"""

    def __init__(self, path: Path | None = None) -> None:
        self._configured_path = path
        self._lock = threading.RLock()

    @property
    def path(self) -> Path:
        return self._configured_path or get_settings().output_dir / CONFIG_FILENAME

    def snapshot(self, today: date | None = None) -> dict:
        config = self.load()
        current = today or date.today()
        return {
            **config,
            "today": asdict(self._decide(current, config)),
        }

    def load(self) -> dict[str, list[str]]:
        with self._lock:
            return self._load_unlocked()

    def decision(self, value: str | date) -> WorkdayDecision:
        target = date.fromisoformat(value) if isinstance(value, str) else value
        with self._lock:
            return self._decide(target, self._load_unlocked())

    def add_leave_range(self, start: date, end: date) -> dict[str, list[str]]:
        if end < start:
            raise ValueError("请假结束日期不能早于开始日期")
        days = (end - start).days + 1
        if days > MAX_LEAVE_RANGE_DAYS:
            raise ValueError(f"一次最多添加 {MAX_LEAVE_RANGE_DAYS} 天请假")

        with self._lock:
            config = self._load_unlocked()
            leave_dates = set(config["leave_dates"])
            current = start
            while current <= end:
                # 周末和法定假日本就无需提交；调休补班日仍可登记请假。
                base_config = {**config, "leave_dates": []}
                if self._decide(current, base_config).required:
                    leave_dates.add(current.isoformat())
                current += timedelta(days=1)
            config["leave_dates"] = sorted(leave_dates)
            self._write_unlocked(config)
            return config

    def remove_leave(self, leave_date: date) -> dict[str, list[str]]:
        with self._lock:
            config = self._load_unlocked()
            config["leave_dates"] = [
                value for value in config["leave_dates"] if value != leave_date.isoformat()
            ]
            self._write_unlocked(config)
            return config

    def _load_unlocked(self) -> dict[str, list[str]]:
        path = self.path
        if not path.exists():
            config = self._read_config(DEFAULT_CONFIG_PATH)
            self._write_unlocked(config)
            return config
        return self._read_config(path)

    @staticmethod
    def _read_config(path: Path) -> dict[str, list[str]]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"无法读取工作日历配置 {path.name}: {error}") from error
        if not isinstance(raw, dict):
            raise RuntimeError(f"工作日历配置 {path.name} 必须是 JSON 对象")

        config: dict[str, list[str]] = {}
        for key in CONFIG_KEYS:
            values = raw.get(key, [])
            if not isinstance(values, list):
                raise RuntimeError(f"工作日历配置项 {key} 必须是日期数组")
            normalized = []
            for value in values:
                if not isinstance(value, str):
                    raise RuntimeError(f"工作日历配置项 {key} 包含非字符串日期")
                try:
                    normalized.append(date.fromisoformat(value).isoformat())
                except ValueError as error:
                    raise RuntimeError(f"工作日历配置项 {key} 包含无效日期: {value}") from error
            config[key] = sorted(set(normalized))
        return config

    def _write_unlocked(self, config: dict[str, list[str]]) -> None:
        path = self.path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        try:
            temporary.write_text(
                json.dumps(config, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as error:
            raise RuntimeError(f"无法写入工作日历配置 {path.name}: {error}") from error

    @staticmethod
    def _decide(target: date, config: dict[str, list[str]]) -> WorkdayDecision:
        date_str = target.isoformat()
        if date_str in config["leave_dates"]:
            return WorkdayDecision(date_str, False, "leave", "个人请假")
        if date_str in config["makeup_workdays"]:
            return WorkdayDecision(date_str, True, "makeup_workday", "调休工作日")
        if date_str in config["holidays"]:
            return WorkdayDecision(date_str, False, "holiday", "法定节假日")
        if target.weekday() >= 5:
            return WorkdayDecision(date_str, False, "weekend", "周末")
        return WorkdayDecision(date_str, True, "workday", "工作日")


work_calendar = WorkCalendar()
