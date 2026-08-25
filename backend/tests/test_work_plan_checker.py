from unittest.mock import MagicMock, patch

from app.services.work_plan_checker import _decode_subject, _subject_matches

PLAN_SUBJECT = "工作计划"
PLAN_DATE = "2026-08-25"
PLAN_TITLE = f"张蒲龙--{PLAN_SUBJECT}[{PLAN_DATE}]--[提交成功]"


def test_subject_matches_plan_with_name_prefix() -> None:
    assert _subject_matches(PLAN_TITLE, PLAN_SUBJECT, PLAN_DATE) is True


def test_subject_matches_plan_with_suffix() -> None:
    title = f"张蒲龙--工作计划[{PLAN_DATE}]--[提交成功](不够300字)"
    assert _subject_matches(title, PLAN_SUBJECT, PLAN_DATE) is True


def test_subject_matches_plan_with_common_marker() -> None:
    assert _subject_matches(PLAN_TITLE, PLAN_SUBJECT, PLAN_DATE) is True


def test_subject_matches_plan_with_late_suffix() -> None:
    title = f"张蒲龙--工作计划[{PLAN_DATE}]--[提交成功]/迟发补登"
    assert _subject_matches(title, PLAN_SUBJECT, PLAN_DATE) is True


def test_subject_not_matches_wrong_date() -> None:
    title = "张蒲龙--工作计划[2026-08-24]--[提交成功]"
    assert _subject_matches(title, PLAN_SUBJECT, PLAN_DATE) is False


def test_subject_not_matches_summary_email() -> None:
    title = "张蒲龙--工作总结[2026-08-25]--[提交成功]"
    assert _subject_matches(title, PLAN_SUBJECT, PLAN_DATE) is False


def test_subject_not_matches_missing_marker() -> None:
    title = "张蒲龙--工作计划[2026-08-25]"
    assert _subject_matches(title, PLAN_SUBJECT, PLAN_DATE) is False


def test_decode_subject_plain() -> None:
    assert _decode_subject(PLAN_TITLE) == PLAN_TITLE


def test_decode_subject_encoded() -> None:
    from email.header import Header

    encoded = str(Header("工作计划", "utf-8"))
    assert _decode_subject(encoded) == "工作计划"


def test_check_today_submitted_sends_no_reminder() -> None:
    checker = _checker_with_count(2)
    with patch("app.services.work_plan_checker.WorkPlanChecker._send_reminder") as mock:
        result = checker.check_today()

    assert result["submitted"] is True
    assert result["matched"] == 2
    assert "已提交" in result["message"]
    mock.assert_not_called()


def test_check_today_not_submitted_sends_reminder() -> None:
    checker = _checker_with_count(0)
    checker.remind_enabled = True
    checker.remind_to = "me@example.com"
    with patch("app.services.work_plan_checker.WorkPlanChecker._send_reminder") as mock:
        result = checker.check_today()

    assert result["submitted"] is False
    assert result["matched"] == 0
    assert "未提交" in result["message"]
    mock.assert_called_once_with(result["date"])


def test_check_today_not_submitted_reminder_disabled() -> None:
    checker = _checker_with_count(0)
    checker.remind_enabled = False
    with patch("app.services.work_plan_checker.WorkPlanChecker._send_reminder") as mock:
        result = checker.check_today()

    assert result["submitted"] is False
    mock.assert_not_called()


def _checker_with_count(count: int):
    from app.services.work_plan_checker import WorkPlanChecker

    checker = WorkPlanChecker()
    checker._count_matching_emails = MagicMock(return_value=count)  # type: ignore[method-assign]
    checker._connect = MagicMock(return_value=True)  # type: ignore[method-assign]
    checker._disconnect = MagicMock()  # type: ignore[method-assign]
    return checker