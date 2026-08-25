"""
工作计划提交检查模块 - 每天拉取邮件时检查当天是否提交了工作计划，并支持自动提交。

检查结果区分已提交、确认未提交和检查失败；只有确认未提交时才允许自动提交。
"""

import email
import imaplib
import json
import logging
import re
import ssl
import time
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.message import Message
from enum import StrEnum

from app import legacy_config as config
from app.core.config import get_settings

logger = logging.getLogger(__name__)

BEIJING_TZ = timezone(timedelta(hours=8))
IMAP_TIMEOUT_SECONDS = 30
AUTO_SUBMIT_RECIPIENT = "working@cet-electric.com"
AUTO_SUBMIT_DEADLINE = "23:59"


class AutoSubmitDeadlineError(RuntimeError):
    """自动提交已超过指定业务日期的安全发送截止时间。"""


class WorkPlanStatus(StrEnum):
    SUBMITTED = "submitted"
    MISSING = "missing"
    CHECK_FAILED = "check_failed"


class AutoSubmitOutcome(StrEnum):
    ALREADY_SUBMITTED = "already_submitted"
    AUTO_CONFIRMED = "auto_confirmed"
    SENT_UNCONFIRMED = "sent_unconfirmed"
    DELIVERY_UNCERTAIN = "delivery_uncertain"
    SEND_FAILED = "send_failed"
    CHECK_FAILED = "check_failed"
    SKIPPED = "skipped"


class AutoSubmitState(StrEnum):
    SENDING = "sending"
    SENT_UNCONFIRMED = "sent_unconfirmed"
    DELIVERY_UNCERTAIN = "delivery_uncertain"
    CONFIRMED = "confirmed"
    SEND_FAILED = "send_failed"
    SKIPPED = "skipped"


def beijing_today() -> str:
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")


def _decode_subject(value: str) -> str:
    """解码邮件主题（RFC2047 编码）"""
    if not value:
        return ""
    parts = decode_header(value)
    return "".join(
        part.decode(charset or "utf-8", errors="replace") if isinstance(part, bytes) else part
        for part, charset in parts
    )


def _subject_matches(subject: str, plan_subject: str, date_str: str) -> bool:
    """主题是否包含指定日期的工作计划提交成功标记。"""
    pattern = re.escape(plan_subject) + r"\[" + re.escape(date_str) + r"\]--\[提交成功\]"
    return re.search(pattern, subject, flags=re.IGNORECASE) is not None


class WorkPlanChecker:
    """通过 IMAP 检查工作计划，并按配置发送提醒或自动提交。"""

    def __init__(self) -> None:
        settings = get_settings()
        self.plan_subject = settings.work_plan_subject or "工作计划"
        self.remind_enabled = settings.work_plan_remind_enabled
        self.remind_to = settings.work_plan_remind_to
        self.imap_server = settings.imap_server
        self.imap_port = settings.imap_port
        self.state_path = settings.output_dir / ".work_plan_auto_submit.json"
        self.connection = None

    def check_today(self, *, send_reminder: bool = True) -> dict:
        """检查北京时间当天的工作计划。"""
        return self.check_for_date(beijing_today(), send_reminder=send_reminder)

    def check_for_date(self, date_str: str, *, send_reminder: bool = True) -> dict:
        """检查指定业务日期，并返回明确的三态结果。"""
        try:
            if not self._connect():
                return self._check_failed(date_str, "无法连接邮箱")
            try:
                matched = self._count_matching_emails(date_str)
            finally:
                self._disconnect()
        except Exception as error:
            logger.error("检查工作计划提交失败: %s", error)
            return self._check_failed(date_str, str(error))

        status = WorkPlanStatus.SUBMITTED if matched > 0 else WorkPlanStatus.MISSING
        message = (
            f"{date_str} 已提交工作计划（{matched} 封）"
            if status == WorkPlanStatus.SUBMITTED
            else f"{date_str} 未提交工作计划"
        )
        logger.info("工作计划检查: %s", message)

        if (
            status == WorkPlanStatus.MISSING
            and send_reminder
            and self.remind_enabled
            and self.remind_to
        ):
            self._send_reminder(date_str)

        return {
            "status": status,
            "submitted": status == WorkPlanStatus.SUBMITTED,
            "date": date_str,
            "matched": matched,
            "message": message,
        }

    @staticmethod
    def _check_failed(date_str: str, reason: str) -> dict:
        return {
            "status": WorkPlanStatus.CHECK_FAILED,
            "submitted": False,
            "date": date_str,
            "matched": 0,
            "message": f"{date_str} 工作计划检查失败：{reason}",
        }

    def _connect(self) -> bool:
        """建立带证书校验和有限超时的 IMAP 连接。"""
        try:
            if not config.IMAP_USERNAME or not config.IMAP_PASSWORD:
                logger.error("未配置邮箱账号，无法检查工作计划")
                return False
            if config.IMAP_USE_SSL:
                context = ssl.create_default_context()
                self.connection = imaplib.IMAP4_SSL(
                    self.imap_server,
                    self.imap_port,
                    ssl_context=context,
                    timeout=IMAP_TIMEOUT_SECONDS,
                )
            else:
                self.connection = imaplib.IMAP4(
                    self.imap_server,
                    self.imap_port,
                    timeout=IMAP_TIMEOUT_SECONDS,
                )
            self.connection.login(config.IMAP_USERNAME, config.IMAP_PASSWORD)
            logger.debug("工作计划检查: IMAP 登录成功")
            return True
        except Exception as error:
            logger.error("工作计划检查: IMAP 登录失败: %s", error)
            self._disconnect()
            return False

    def _disconnect(self) -> None:
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            try:
                self.connection.logout()
            except Exception:
                pass
            self.connection = None

    def _count_matching_emails(self, date_str: str) -> int:
        """统计邮箱中匹配指定日期提交成功主题的邮件数。"""
        if self.connection is None:
            raise RuntimeError("IMAP 尚未连接")

        mailbox = config.IMAP_MAILBOX
        status, _ = self.connection.select(mailbox, readonly=True)
        if status != "OK":
            raise RuntimeError(f"无法打开邮箱文件夹 {mailbox}")

        status, data = self.connection.uid("search", None, "ALL")
        if status != "OK":
            raise RuntimeError("搜索工作计划邮件失败")
        if not data or not data[0]:
            return 0

        uids = data[0].split()
        matched = 0
        chunk_size = 200
        for index in range(0, len(uids), chunk_size):
            chunk = uids[index : index + chunk_size]
            status, batch = self.connection.uid(
                "fetch", b",".join(chunk), "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])"
            )
            if status != "OK":
                raise RuntimeError("获取邮件主题失败")
            for item in batch or []:
                if not (isinstance(item, tuple) and len(item) == 2):
                    continue
                header_bytes = item[1]
                if isinstance(header_bytes, bytes):
                    header_bytes = header_bytes.decode("utf-8", errors="replace")
                message: Message = email.message_from_string(header_bytes)
                subject = _decode_subject(str(message.get("Subject", "")))
                if _subject_matches(subject, self.plan_subject, date_str):
                    matched += 1
        return matched

    def _send_reminder(self, date_str: str) -> None:
        """发送未提交工作计划提醒。"""
        from app.services.email_sender import sender as email_sender

        subject = f"工作计划未提交提醒[{date_str}]"
        content = (
            f"您好，\n\n"
            f"今天（{date_str}）的工作计划尚未提交。\n\n"
            f"本邮件由 CETWorkOverTime 自动发送。"
        )
        try:
            email_sender.send(to_addr=self.remind_to, subject=subject, content=content)
            logger.info("已发送工作计划未提交提醒到 %s", self.remind_to)
        except Exception as error:
            logger.error("发送工作计划提醒失败: %s", error)

    def auto_submit_today(self) -> str:
        """自动处理北京时间当天的工作计划。"""
        return self.auto_submit_for(beijing_today())

    def pending_auto_submit_dates(self) -> list[str]:
        """返回启动时需要只读恢复确认的业务日期。"""
        pending_states = {
            AutoSubmitState.SENDING,
            AutoSubmitState.SENT_UNCONFIRMED,
            AutoSubmitState.DELIVERY_UNCERTAIN,
            AutoSubmitState.SEND_FAILED,
        }
        states = self._load_auto_submit_states()
        dates = []
        for date_str, entry in states.items():
            if not isinstance(entry, dict):
                continue
            try:
                state = AutoSubmitState(entry.get("state"))
            except (TypeError, ValueError):
                continue
            if state in pending_states:
                dates.append(date_str)
        return sorted(dates)

    def resume_pending_auto_submits(self) -> str:
        """启动时恢复待确认状态，只检查回执，不重新发送计划。"""
        dates = self.pending_auto_submit_dates()
        if not dates:
            return "没有待恢复的工作计划自动提交状态"

        today = beijing_today()
        results = []
        for date_str in dates:
            state = self._get_auto_submit_state(date_str)
            if state:
                results.append(
                    self._resume_auto_submit(
                        date_str,
                        state,
                        wait_for_receipt=date_str == today,
                    )
                )
        return "；".join(results)

    def auto_submit_for(self, date_str: str) -> str:
        """只在完整检查确认缺失时，自动提交指定业务日期的计划。"""
        from app.services.email_sender import DeliveryUncertainError
        from app.services.email_sender import sender as email_sender

        try:
            state = self._get_auto_submit_state(date_str)
        except RuntimeError as error:
            self._notify_auto_submit(
                date_str,
                AutoSubmitOutcome.CHECK_FAILED,
                detail=str(error),
            )
            return f"{date_str} 自动提交状态无法读取，未执行：{error}"

        if state:
            return self._resume_auto_submit(date_str, state)

        check = self.check_for_date(date_str, send_reminder=False)
        if check["status"] == WorkPlanStatus.CHECK_FAILED:
            self._notify_auto_submit(
                date_str,
                AutoSubmitOutcome.CHECK_FAILED,
                detail=check["message"],
            )
            return f"{date_str} 状态无法确认，未执行自动提交（{check['message']}）"
        if check["status"] == WorkPlanStatus.SUBMITTED:
            self._set_auto_submit_state(date_str, AutoSubmitState.CONFIRMED)
            self._notify_auto_submit(date_str, AutoSubmitOutcome.ALREADY_SUBMITTED)
            return f"{date_str} 已提交，无需自动提交（{check['message']}）"

        subject = f"{self.plan_subject}[{date_str}]"
        content = f"{self.plan_subject}[{date_str}]\n1、\n2、\n3、"

        def prepare_send() -> None:
            if datetime.now(BEIJING_TZ) >= self._auto_submit_deadline(date_str):
                self._set_auto_submit_state(date_str, AutoSubmitState.SKIPPED)
                raise AutoSubmitDeadlineError("已超过自动提交安全截止时间")
            self._set_auto_submit_state(date_str, AutoSubmitState.SENDING)

        try:
            email_sender.send(
                to_addr=AUTO_SUBMIT_RECIPIENT,
                subject=subject,
                content=content,
                before_send=prepare_send,
            )
        except AutoSubmitDeadlineError as error:
            self._notify_auto_submit(
                date_str,
                AutoSubmitOutcome.SKIPPED,
                detail=str(error),
            )
            return f"{date_str} 自动提交未执行：{error}"
        except DeliveryUncertainError as error:
            try:
                self._set_auto_submit_state(date_str, AutoSubmitState.DELIVERY_UNCERTAIN)
            except RuntimeError as state_error:
                logger.error("记录发送结果未知状态失败: %s", state_error)
            self._notify_auto_submit(
                date_str,
                AutoSubmitOutcome.DELIVERY_UNCERTAIN,
                detail=str(error),
            )
            return f"{date_str} 自动发送结果无法确认，未重复发送：{error}"
        except Exception as error:
            try:
                self._set_auto_submit_state(date_str, AutoSubmitState.SEND_FAILED)
            except RuntimeError as state_error:
                logger.error("记录自动提交失败状态失败: %s", state_error)
            self._notify_auto_submit(
                date_str,
                AutoSubmitOutcome.SEND_FAILED,
                detail=str(error),
            )
            return f"{date_str} 自动提交失败：{error}"

        try:
            self._set_auto_submit_state(date_str, AutoSubmitState.SENT_UNCONFIRMED)
        except RuntimeError as error:
            logger.error("计划已发送，但记录待确认状态失败: %s", error)
            self._notify_auto_submit(
                date_str,
                AutoSubmitOutcome.SENT_UNCONFIRMED,
                detail=str(error),
            )
            return f"{date_str} 自动提交已发送，但状态记录失败，未重复发送"
        logger.info(
            "已自动发送计划邮件 %s -> %s（等待回执）",
            subject,
            AUTO_SUBMIT_RECIPIENT,
        )

        if self._wait_for_receipt(date_str, check_immediately=False):
            self._confirm_auto_submit(date_str)
            return f"{date_str} 自动提交成功（已收到回执）"

        self._notify_auto_submit(date_str, AutoSubmitOutcome.SENT_UNCONFIRMED)
        return f"{date_str} 自动提交已发送，但未在 120 秒内确认回执"

    def _resume_auto_submit(
        self,
        date_str: str,
        state: AutoSubmitState,
        *,
        wait_for_receipt: bool = True,
    ) -> str:
        """恢复已持久化的自动提交状态，绝不重复发送计划邮件。"""
        if state == AutoSubmitState.CONFIRMED:
            return f"{date_str} 自动提交已处理，无需重复执行"
        if state == AutoSubmitState.SKIPPED:
            return f"{date_str} 自动提交此前已标记为未执行"

        if state == AutoSubmitState.SEND_FAILED:
            if self.check_for_date(date_str, send_reminder=False)["submitted"]:
                self._confirm_auto_submit(date_str)
                return f"{date_str} 自动提交已确认收到回执"
            self._notify_auto_submit(date_str, AutoSubmitOutcome.SEND_FAILED)
            return f"{date_str} 自动提交此前失败，未重复发送"

        confirmed = (
            self._wait_for_receipt(date_str, check_immediately=True)
            if wait_for_receipt
            else self.check_for_date(date_str, send_reminder=False)["submitted"]
        )
        if confirmed:
            self._confirm_auto_submit(date_str)
            return f"{date_str} 自动提交已确认收到回执"

        if state == AutoSubmitState.SENDING:
            try:
                self._set_auto_submit_state(date_str, AutoSubmitState.DELIVERY_UNCERTAIN)
            except RuntimeError as error:
                logger.error("恢复发送结果未知状态失败: %s", error)
            state = AutoSubmitState.DELIVERY_UNCERTAIN

        outcome = (
            AutoSubmitOutcome.SENT_UNCONFIRMED
            if state == AutoSubmitState.SENT_UNCONFIRMED
            else AutoSubmitOutcome.DELIVERY_UNCERTAIN
        )
        self._notify_auto_submit(date_str, outcome)
        return f"{date_str} 自动提交此前已开始发送，当前结果待确认，未重复发送"

    def _wait_for_receipt(self, date_str: str, *, check_immediately: bool) -> bool:
        checks = 9 if check_immediately else 8
        for index in range(checks):
            if not check_immediately or index > 0:
                time.sleep(15)
            check = self.check_for_date(date_str, send_reminder=False)
            if check["status"] == WorkPlanStatus.SUBMITTED:
                return True
        return False

    def _confirm_auto_submit(self, date_str: str) -> None:
        try:
            self._set_auto_submit_state(date_str, AutoSubmitState.CONFIRMED)
        except RuntimeError as error:
            logger.error("记录自动提交确认状态失败: %s", error)
        self._notify_auto_submit(date_str, AutoSubmitOutcome.AUTO_CONFIRMED)

    def notify_auto_submit_skipped(self, date_str: str, reason: str) -> None:
        """记录并通知指定日期的自动提交任务未执行。"""
        try:
            existing = self._get_auto_submit_state(date_str)
            if existing is not None:
                return
            self._set_auto_submit_state(date_str, AutoSubmitState.SKIPPED)
        except RuntimeError as error:
            reason = f"{reason}；状态记录失败：{error}"
        self._notify_auto_submit(date_str, AutoSubmitOutcome.SKIPPED, detail=reason)

    @staticmethod
    def _auto_submit_deadline(date_str: str) -> datetime:
        return datetime.strptime(
            f"{date_str} {AUTO_SUBMIT_DEADLINE}",
            "%Y-%m-%d %H:%M",
        ).replace(tzinfo=BEIJING_TZ)

    def _get_auto_submit_state(self, date_str: str) -> AutoSubmitState | None:
        states = self._load_auto_submit_states()
        entry = states.get(date_str)
        if not isinstance(entry, dict) or not entry.get("state"):
            return None
        try:
            return AutoSubmitState(entry["state"])
        except ValueError as error:
            raise RuntimeError(f"自动提交状态非法: {entry['state']}") from error

    def _set_auto_submit_state(self, date_str: str, state: AutoSubmitState) -> None:
        states = self._load_auto_submit_states()
        existing = states.get(date_str) if isinstance(states.get(date_str), dict) else {}
        states[date_str] = {
            "state": state,
            "updated_at": datetime.now(BEIJING_TZ).isoformat(timespec="seconds"),
            "notified_outcomes": existing.get("notified_outcomes", []),
        }
        self._write_auto_submit_states(dict(sorted(states.items())[-30:]))

    def _notification_was_sent(
        self,
        date_str: str,
        outcome: AutoSubmitOutcome,
    ) -> bool:
        states = self._load_auto_submit_states()
        entry = states.get(date_str)
        if not isinstance(entry, dict):
            return False
        return outcome in entry.get("notified_outcomes", [])

    def _mark_notification_sent(
        self,
        date_str: str,
        outcome: AutoSubmitOutcome,
    ) -> None:
        states = self._load_auto_submit_states()
        entry = states.get(date_str)
        if not isinstance(entry, dict) or not entry.get("state"):
            return
        notified = list(entry.get("notified_outcomes", []))
        if outcome not in notified:
            notified.append(outcome)
            entry["notified_outcomes"] = notified
            self._write_auto_submit_states(states)

    def _write_auto_submit_states(self, states: dict) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.state_path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(states, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.state_path)
        except OSError as error:
            raise RuntimeError(f"无法保存自动提交状态: {error}") from error

    def _load_auto_submit_states(self) -> dict:
        if not self.state_path.exists():
            return {}
        try:
            states = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(f"无法读取自动提交状态: {error}") from error
        if not isinstance(states, dict):
            raise RuntimeError("自动提交状态文件格式非法")
        return states

    def _notify_auto_submit(
        self,
        date_str: str,
        outcome: AutoSubmitOutcome,
        *,
        detail: str = "",
    ) -> None:
        """发送自动提交结果通知到 WORK_PLAN_REMIND_TO。"""
        from app.services.email_sender import sender as email_sender

        if not self.remind_to:
            return
        try:
            if self._notification_was_sent(date_str, outcome):
                return
        except RuntimeError as error:
            logger.error("读取自动提交通知状态失败: %s", error)

        if outcome == AutoSubmitOutcome.ALREADY_SUBMITTED:
            subject = f"工作计划自动提交确认[{date_str}]"
            message = f"今天（{date_str}）的工作计划已提交，无需自动提交。"
        elif outcome == AutoSubmitOutcome.AUTO_CONFIRMED:
            subject = f"工作计划自动提交成功[{date_str}]"
            message = f"今天（{date_str}）的工作计划已自动提交成功，并已收到回执。"
        elif outcome == AutoSubmitOutcome.SENT_UNCONFIRMED:
            subject = f"工作计划已自动发送待确认[{date_str}]"
            message = (
                f"今天（{date_str}）的工作计划已自动发送，但尚未收到回执。"
                "请先检查邮箱回执，避免重复提交。"
            )
        elif outcome == AutoSubmitOutcome.DELIVERY_UNCERTAIN:
            subject = f"工作计划自动发送结果待确认[{date_str}]"
            message = (
                f"今天（{date_str}）的工作计划发送过程曾被中断，无法确认是否已投递。"
                "系统不会重复发送，请检查邮箱回执后再决定是否手动提交。"
            )
        elif outcome == AutoSubmitOutcome.CHECK_FAILED:
            subject = f"工作计划状态检查失败[{date_str}]"
            message = f"无法确认今天（{date_str}）的工作计划状态，未执行自动提交：{detail}"
        elif outcome == AutoSubmitOutcome.SKIPPED:
            subject = f"工作计划自动提交未执行[{date_str}]"
            message = f"今天（{date_str}）的工作计划自动提交未执行：{detail}。请人工核查。"
        else:
            subject = f"工作计划自动提交异常[{date_str}]"
            reason = detail or "此前发送过程已明确失败"
            message = (
                f"今天（{date_str}）的工作计划发送过程报错：{reason}。"
                "请先检查邮箱回执，确认未投递后再手动提交。"
            )

        content = f"您好，\n\n{message}\n\n本邮件由 CETWorkOverTime 自动发送。"
        try:
            email_sender.send(to_addr=self.remind_to, subject=subject, content=content)
            try:
                self._mark_notification_sent(date_str, outcome)
            except RuntimeError as state_error:
                logger.error("记录自动提交通知状态失败: %s", state_error)
            logger.info("已发送自动提交通知到 %s", self.remind_to)
        except Exception as error:
            logger.error("发送自动提交通知失败: %s", error)


work_plan_checker = WorkPlanChecker()
