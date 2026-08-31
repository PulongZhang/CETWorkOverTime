import json
from datetime import date
from pathlib import Path

import pytest

from app.services.work_calendar import WorkCalendar


def _calendar(tmp_path: Path, config: dict | None = None) -> WorkCalendar:
    path = tmp_path / "work_calendar.json"
    if config is not None:
        path.write_text(json.dumps(config), encoding="utf-8")
    return WorkCalendar(path)


def test_default_calendar_distinguishes_holiday_makeup_day_and_weekend(
    tmp_path: Path,
) -> None:
    calendar = _calendar(tmp_path)

    assert calendar.decision("2026-10-01").reason == "法定节假日"
    assert calendar.decision("2026-10-01").required is False
    assert calendar.decision("2026-10-10").reason == "调休工作日"
    assert calendar.decision("2026-10-10").required is True
    assert calendar.decision("2026-08-29").reason == "周末"
    assert calendar.decision("2026-08-29").required is False


def test_leave_range_only_records_dates_that_would_be_workdays(tmp_path: Path) -> None:
    calendar = _calendar(
        tmp_path,
        {
            "holidays": ["2026-09-07"],
            "makeup_workdays": ["2026-09-05"],
            "leave_dates": [],
        },
    )

    config = calendar.add_leave_range(date(2026, 9, 4), date(2026, 9, 7))

    assert config["leave_dates"] == ["2026-09-04", "2026-09-05"]
    assert calendar.decision("2026-09-05").reason == "个人请假"


def test_remove_leave_restores_normal_workday(tmp_path: Path) -> None:
    calendar = _calendar(
        tmp_path,
        {"holidays": [], "makeup_workdays": [], "leave_dates": ["2026-08-31"]},
    )

    calendar.remove_leave(date(2026, 8, 31))

    assert calendar.decision("2026-08-31").required is True


def test_reversed_leave_range_is_rejected(tmp_path: Path) -> None:
    calendar = _calendar(tmp_path)

    with pytest.raises(ValueError, match="结束日期"):
        calendar.add_leave_range(date(2026, 9, 2), date(2026, 9, 1))


def test_invalid_json_is_reported_instead_of_falling_back_to_workday(tmp_path: Path) -> None:
    path = tmp_path / "work_calendar.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(RuntimeError, match="无法读取工作日历配置"):
        WorkCalendar(path).decision("2026-08-31")
