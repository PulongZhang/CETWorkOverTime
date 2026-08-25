from email.header import Header
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import get_settings
from app.services.email_sender import DeliveryUncertainError
from app.services.work_plan_checker import (
    AutoSubmitState,
    WorkPlanChecker,
    WorkPlanStatus,
    _decode_subject,
    _subject_matches,
)

PLAN_SUBJECT = "工作计划"
PLAN_DATE = "2026-08-25"
PLAN_TITLE = f"张蒲龙--{PLAN_SUBJECT}[{PLAN_DATE}]--[提交成功]"
WORK_PLAN_MAILBOX = "&work-plan-"


@pytest.fixture(autouse=True)
def isolate_auto_submit_state():
    settings = get_settings()
    original = settings.output_dir
    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        settings.output_dir = Path(directory)
        try:
            yield
        finally:
            settings.output_dir = original


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
    encoded = Header("工作计划", "utf-8").encode()
    assert _decode_subject(encoded) == "工作计划"


def test_check_today_submitted_sends_no_reminder() -> None:
    checker = _checker_with_count(2)
    with patch("app.services.work_plan_checker.WorkPlanChecker._send_reminder") as mock:
        result = checker.check_today()

    assert result["status"] == WorkPlanStatus.SUBMITTED
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

    assert result["status"] == WorkPlanStatus.MISSING
    assert result["submitted"] is False
    assert result["matched"] == 0
    assert "未提交" in result["message"]
    mock.assert_called_once_with(result["date"])


def test_check_failure_is_not_reported_as_missing_or_reminded() -> None:
    checker = WorkPlanChecker()
    checker.remind_enabled = True
    checker.remind_to = "me@example.com"
    checker._connect = MagicMock(return_value=False)  # type: ignore[method-assign]

    with patch("app.services.work_plan_checker.WorkPlanChecker._send_reminder") as mock:
        result = checker.check_for_date(PLAN_DATE)

    assert result["status"] == WorkPlanStatus.CHECK_FAILED
    assert result["submitted"] is False
    assert "检查失败" in result["message"]
    mock.assert_not_called()


def test_mailbox_command_failure_becomes_check_failure() -> None:
    checker = WorkPlanChecker()
    connection = MagicMock()
    connection.select.return_value = ("NO", [b"failed"])
    checker.connection = connection
    checker._connect = MagicMock(return_value=True)  # type: ignore[method-assign]
    checker._disconnect = MagicMock()  # type: ignore[method-assign]

    with patch(
        "app.services.work_plan_checker.config.WORK_PLAN_MAILBOX", WORK_PLAN_MAILBOX
    ):
        result = checker.check_for_date(PLAN_DATE)

    assert result["status"] == WorkPlanStatus.CHECK_FAILED
    assert result["submitted"] is False
    connection.select.assert_called_once_with(WORK_PLAN_MAILBOX, readonly=True)


def test_connect_sets_finite_timeout() -> None:
    checker = WorkPlanChecker()
    connection = MagicMock()
    with (
        patch("app.services.work_plan_checker.config.IMAP_USERNAME", "user@example.com"),
        patch("app.services.work_plan_checker.config.IMAP_PASSWORD", "secret"),
        patch("app.services.work_plan_checker.config.IMAP_USE_SSL", True),
        patch("app.services.work_plan_checker.ssl.create_default_context") as create_context,
        patch(
            "app.services.work_plan_checker.imaplib.IMAP4_SSL", return_value=connection
        ) as imap_ssl,
    ):
        assert checker._connect() is True

    imap_ssl.assert_called_once_with(
        checker.imap_server,
        checker.imap_port,
        ssl_context=create_context.return_value,
        timeout=30,
    )


def _checker_with_count(count: int) -> WorkPlanChecker:
    checker = WorkPlanChecker()
    checker._count_matching_emails = MagicMock(return_value=count)  # type: ignore[method-assign]
    checker._connect = MagicMock(return_value=True)  # type: ignore[method-assign]
    checker._disconnect = MagicMock()  # type: ignore[method-assign]
    return checker


def test_auto_submit_when_already_submitted() -> None:
    checker = _checker_with_count(1)
    checker.remind_to = "me@example.com"
    with patch("app.services.email_sender.sender.send") as mock_send:
        result = checker.auto_submit_for(PLAN_DATE)

    assert "已提交，无需自动提交" in result
    assert mock_send.call_count == 1
    assert mock_send.call_args.kwargs["to_addr"] == "me@example.com"
    assert "自动提交确认" in mock_send.call_args.kwargs["subject"]


def test_auto_submit_not_submitted_sends_plan_and_success_notification() -> None:
    checker = WorkPlanChecker()
    checker.remind_to = "me@example.com"
    checker.check_for_date = MagicMock(  # type: ignore[method-assign]
        side_effect=[
            {
                "status": WorkPlanStatus.MISSING,
                "submitted": False,
                "date": PLAN_DATE,
                "matched": 0,
                "message": "未提交",
            },
            {
                "status": WorkPlanStatus.SUBMITTED,
                "submitted": True,
                "date": PLAN_DATE,
                "matched": 1,
                "message": "已提交",
            },
        ]
    )

    with (
        patch("app.services.email_sender.sender.send") as mock_send,
        patch("app.services.work_plan_checker.time.sleep") as mock_sleep,
    ):
        result = checker.auto_submit_for(PLAN_DATE)

    assert "自动提交成功" in result
    assert mock_send.call_count == 2
    plan_call, notification_call = mock_send.call_args_list
    assert plan_call.kwargs["to_addr"] == "working@cet-electric.com"
    assert plan_call.kwargs["subject"] == f"工作计划[{PLAN_DATE}]"
    assert "1、" in plan_call.kwargs["content"]
    assert notification_call.kwargs["to_addr"] == "me@example.com"
    assert "自动提交成功" in notification_call.kwargs["subject"]
    assert "无需自动提交" not in notification_call.kwargs["content"]
    mock_sleep.assert_called_once_with(15)
    assert checker.check_for_date.call_args_list[0].kwargs == {"send_reminder": False}
    assert checker.check_for_date.call_args_list[1].kwargs == {"send_reminder": False}


def test_auto_submit_polling_does_not_repeat_missing_reminders() -> None:
    checker = _checker_with_count(0)
    checker.remind_enabled = True
    checker.remind_to = "me@example.com"

    with (
        patch("app.services.email_sender.sender.send") as mock_send,
        patch("app.services.work_plan_checker.time.sleep") as mock_sleep,
        patch("app.services.work_plan_checker.WorkPlanChecker._send_reminder") as reminder,
    ):
        result = checker.auto_submit_for(PLAN_DATE)

    assert "已发送" in result
    assert "未在 120 秒内确认" in result
    assert mock_send.call_count == 2
    assert "待确认" in mock_send.call_args_list[1].kwargs["subject"]
    assert "请手动提交" not in mock_send.call_args_list[1].kwargs["content"]
    assert mock_sleep.call_count == 8
    reminder.assert_not_called()


def test_restart_after_send_does_not_send_plan_again() -> None:
    first = _checker_with_count(0)
    first.remind_to = ""
    with (
        patch("app.services.email_sender.sender.send") as first_send,
        patch("app.services.work_plan_checker.time.sleep"),
    ):
        first.auto_submit_for(PLAN_DATE)

    assert first_send.call_count == 1
    assert first._get_auto_submit_state(PLAN_DATE) == AutoSubmitState.SENT_UNCONFIRMED

    restarted = _checker_with_count(0)
    restarted.remind_to = ""
    with (
        patch("app.services.email_sender.sender.send") as restarted_send,
        patch("app.services.work_plan_checker.time.sleep") as sleep,
    ):
        result = restarted.auto_submit_for(PLAN_DATE)

    assert "未重复发送" in result
    assert sleep.call_count == 8
    restarted_send.assert_not_called()


def test_restart_from_uncertain_sending_state_does_not_resend() -> None:
    first = WorkPlanChecker()
    first._set_auto_submit_state(PLAN_DATE, AutoSubmitState.SENDING)

    restarted = _checker_with_count(0)
    restarted.remind_to = ""
    with (
        patch("app.services.email_sender.sender.send") as restarted_send,
        patch("app.services.work_plan_checker.time.sleep") as sleep,
    ):
        result = restarted.auto_submit_for(PLAN_DATE)

    assert "未重复发送" in result
    assert sleep.call_count == 8
    assert restarted._get_auto_submit_state(PLAN_DATE) == AutoSubmitState.DELIVERY_UNCERTAIN
    restarted_send.assert_not_called()


def test_resume_waits_for_late_receipt_without_resending_plan() -> None:
    checker = WorkPlanChecker()
    checker.remind_to = "me@example.com"
    checker._set_auto_submit_state(PLAN_DATE, AutoSubmitState.SENT_UNCONFIRMED)
    checker.check_for_date = MagicMock(  # type: ignore[method-assign]
        side_effect=[
            {"status": WorkPlanStatus.MISSING, "submitted": False},
            {"status": WorkPlanStatus.SUBMITTED, "submitted": True},
        ]
    )

    with (
        patch("app.services.email_sender.sender.send") as send,
        patch("app.services.work_plan_checker.time.sleep") as sleep,
    ):
        result = checker.auto_submit_for(PLAN_DATE)

    assert "已确认收到回执" in result
    assert checker._get_auto_submit_state(PLAN_DATE) == AutoSubmitState.CONFIRMED
    assert sleep.call_count == 1
    assert send.call_count == 1
    assert send.call_args.kwargs["to_addr"] == "me@example.com"


def test_uncertain_smtp_failure_is_not_marked_as_definite_failure() -> None:
    checker = WorkPlanChecker()
    checker.remind_to = "me@example.com"
    checker.check_for_date = MagicMock(  # type: ignore[method-assign]
        return_value={
            "status": WorkPlanStatus.MISSING,
            "submitted": False,
            "message": "未提交",
        }
    )

    def send_side_effect(**kwargs):
        if kwargs.get("before_send"):
            kwargs["before_send"]()
            raise DeliveryUncertainError("connection reset")
        return None

    with patch(
        "app.services.email_sender.sender.send",
        side_effect=send_side_effect,
    ) as send:
        result = checker.auto_submit_for(PLAN_DATE)

    assert "结果无法确认" in result
    assert checker._get_auto_submit_state(PLAN_DATE) == AutoSubmitState.DELIVERY_UNCERTAIN
    assert send.call_count == 2
    assert "结果待确认" in send.call_args_list[1].kwargs["subject"]


def test_auto_submit_does_not_start_delivery_after_safe_deadline() -> None:
    checker = WorkPlanChecker()
    checker.remind_to = "me@example.com"
    checker.check_for_date = MagicMock(  # type: ignore[method-assign]
        return_value={
            "status": WorkPlanStatus.MISSING,
            "submitted": False,
            "message": "未提交",
        }
    )

    def send_side_effect(**kwargs):
        if kwargs.get("before_send"):
            with patch.object(
                checker,
                "_auto_submit_deadline",
                return_value=datetime.now(BEIJING_TZ),
            ):
                kwargs["before_send"]()
        return None

    from datetime import datetime

    from app.services.work_plan_checker import BEIJING_TZ

    with patch(
        "app.services.email_sender.sender.send",
        side_effect=send_side_effect,
    ) as send:
        result = checker.auto_submit_for(PLAN_DATE)

    assert "未执行" in result
    assert checker._get_auto_submit_state(PLAN_DATE) == AutoSubmitState.SKIPPED
    assert send.call_count == 2
    assert "未执行" in send.call_args_list[1].kwargs["subject"]


def test_auto_submit_check_failure_never_sends_plan() -> None:
    checker = WorkPlanChecker()
    checker.remind_to = "me@example.com"
    checker.check_for_date = MagicMock(  # type: ignore[method-assign]
        return_value={
            "status": WorkPlanStatus.CHECK_FAILED,
            "submitted": False,
            "date": PLAN_DATE,
            "matched": 0,
            "message": "检查失败：连接超时",
        }
    )

    with patch("app.services.email_sender.sender.send") as mock_send:
        result = checker.auto_submit_for(PLAN_DATE)

    assert "未执行自动提交" in result
    assert mock_send.call_count == 1
    assert mock_send.call_args.kwargs["to_addr"] == "me@example.com"
    assert "状态检查失败" in mock_send.call_args.kwargs["subject"]


def test_auto_submit_send_failure() -> None:
    checker = WorkPlanChecker()
    checker.remind_to = "me@example.com"
    checker.check_for_date = MagicMock(  # type: ignore[method-assign]
        return_value={
            "status": WorkPlanStatus.MISSING,
            "submitted": False,
            "date": PLAN_DATE,
            "matched": 0,
            "message": "未提交",
        }
    )

    with patch(
        "app.services.email_sender.sender.send",
        side_effect=[RuntimeError("SMTP 连接失败"), None],
    ) as mock_send:
        result = checker.auto_submit_for(PLAN_DATE)

    assert "自动提交失败" in result
    assert mock_send.call_count == 2
    assert "自动提交异常" in mock_send.call_args_list[1].kwargs["subject"]
    assert "先检查邮箱回执" in mock_send.call_args_list[1].kwargs["content"]


def test_notify_skipped_is_persisted_and_sent_only_once() -> None:
    checker = WorkPlanChecker()
    checker.remind_to = "me@example.com"

    with patch("app.services.email_sender.sender.send") as mock_send:
        checker.notify_auto_submit_skipped(PLAN_DATE, "已有任务在运行中")
        checker.notify_auto_submit_skipped(PLAN_DATE, "已有任务在运行中")

    assert checker._get_auto_submit_state(PLAN_DATE) == AutoSubmitState.SKIPPED
    mock_send.assert_called_once()
    assert "未执行" in mock_send.call_args.kwargs["subject"]
    assert "已有任务在运行中" in mock_send.call_args.kwargs["content"]


def test_skipped_notification_does_not_overwrite_failed_state() -> None:
    checker = WorkPlanChecker()
    checker.remind_to = "me@example.com"
    checker._set_auto_submit_state(PLAN_DATE, AutoSubmitState.SEND_FAILED)

    with patch("app.services.email_sender.sender.send") as mock_send:
        checker.notify_auto_submit_skipped(PLAN_DATE, "服务启动过晚")

    assert checker._get_auto_submit_state(PLAN_DATE) == AutoSubmitState.SEND_FAILED
    mock_send.assert_not_called()


def test_recovery_polls_pending_state_and_deduplicates_timeout_notification() -> None:
    checker = _checker_with_count(0)
    checker.remind_to = "me@example.com"
    checker._set_auto_submit_state(PLAN_DATE, AutoSubmitState.SENT_UNCONFIRMED)

    with (
        patch("app.services.work_plan_checker.beijing_today", return_value=PLAN_DATE),
        patch("app.services.work_plan_checker.time.sleep") as sleep,
        patch("app.services.email_sender.sender.send") as send,
    ):
        first = checker.resume_pending_auto_submits()
        second = checker.resume_pending_auto_submits()

    assert "未重复发送" in first
    assert "未重复发送" in second
    assert sleep.call_count == 16
    send.assert_called_once()
    assert "待确认" in send.call_args.kwargs["subject"]


def test_count_matching_emails_uses_work_plan_mailbox() -> None:
    checker = WorkPlanChecker()
    connection = MagicMock()
    connection.select.return_value = ("OK", [b"1"])
    connection.uid.return_value = ("OK", [b""])
    checker.connection = connection

    with patch(
        "app.services.work_plan_checker.config.WORK_PLAN_MAILBOX", WORK_PLAN_MAILBOX
    ):
        assert checker._count_matching_emails(PLAN_DATE) == 0

    connection.select.assert_called_once_with(WORK_PLAN_MAILBOX, readonly=True)


def test_count_matching_emails_requires_work_plan_mailbox() -> None:
    checker = WorkPlanChecker()
    checker.connection = MagicMock()

    with (
        patch("app.services.work_plan_checker.config.WORK_PLAN_MAILBOX", ""),
        patch("app.services.work_plan_checker.config.IMAP_MAILBOX", "&work-summary-"),
        pytest.raises(RuntimeError, match="WORK_PLAN_MAILBOX"),
    ):
        checker._count_matching_emails(PLAN_DATE)


def test_count_matching_emails_raises_on_fetch_failure() -> None:
    checker = WorkPlanChecker()
    connection = MagicMock()
    connection.select.return_value = ("OK", [b"1"])
    connection.uid.side_effect = [("OK", [b"1"]), ("NO", [])]
    checker.connection = connection

    with (
        patch(
            "app.services.work_plan_checker.config.WORK_PLAN_MAILBOX", WORK_PLAN_MAILBOX
        ),
        pytest.raises(RuntimeError, match="获取邮件主题失败"),
    ):
        checker._count_matching_emails(PLAN_DATE)
