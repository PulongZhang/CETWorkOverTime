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


def test_auto_submit_when_already_submitted() -> None:
    checker = _checker_with_count(1)
    checker.remind_to = "me@example.com"
    with (
        patch(
            "app.services.work_plan_checker.WorkPlanChecker._send_reminder"
        ) as mock_remind,
        patch(
            "app.services.email_sender.sender.send"
        ) as mock_send,
    ):
        result = checker.auto_submit_today()

    assert "已提交，无需自动提交" in result
    # 已提交 → 不发计划邮件给 working，只发确认通知
    assert mock_send.call_count == 1
    assert mock_send.call_args.kwargs["to_addr"] == "me@example.com"
    assert "自动提交确认" in mock_send.call_args.kwargs["subject"]
    mock_remind.assert_not_called()  # 已提交则不发未提交提醒


def test_auto_submit_not_submitted_sends_plan_and_confirms() -> None:
    checker = _checker_with_count(0)
    checker.remind_to = "me@example.com"
    from datetime import datetime

    from app.services.work_plan_checker import BEIJING_TZ

    date_str = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

    with (
        patch(
            "app.services.email_sender.sender.send"
        ) as mock_send,
        patch("app.services.work_plan_checker.time.sleep") as mock_sleep,
    ):
        # 第一次 check_today（未提交）→ 发送计划邮件；等待后第二次检查变为已提交
        mock_send.side_effect = ["250 OK", "250 OK"]
        checker.check_today = MagicMock(  # type: ignore[method-assign]
            side_effect=[
                {"submitted": False, "date": date_str, "matched": 0, "message": "未提交"},
                {"submitted": True, "date": date_str, "matched": 1, "message": "已提交"},
            ]
        )
        result = checker.auto_submit_today()

    assert "自动提交成功" in result
    # 发送计划邮件给 working
    plan_call = mock_send.call_args_list[0]
    assert plan_call.kwargs["to_addr"] == "working@cet-electric.com"
    assert f"工作计划[{date_str}]" in plan_call.kwargs["subject"]
    assert f"工作计划[{date_str}]" in plan_call.kwargs["content"]
    assert "1、" in plan_call.kwargs["content"]
    # 通知
    mock_send.assert_called()
    mock_sleep.assert_called()


def test_auto_submit_send_failure() -> None:
    checker = _checker_with_count(0)
    checker.remind_to = "me@example.com"
    with (
        patch(
            "app.services.work_plan_checker.WorkPlanChecker._send_reminder"
        ) as mock_remind,
        patch(
            "app.services.email_sender.sender.send",
            side_effect=RuntimeError("SMTP 连接失败"),
        ) as mock_send,
    ):
        result = checker.auto_submit_today()

    assert "自动提交失败" in result
    mock_send.assert_called()
    mock_remind.assert_called()  # 发送失败也发提醒/通知