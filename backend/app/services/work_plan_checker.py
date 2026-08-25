"""
工作计划提交检查模块 - 每天拉取邮件时检查当天是否提交了工作计划，并支持自动提交

判断依据：邮箱（IMAP）中是否存在主题为
    「{姓名}--工作计划[{日期}]--[提交成功]」的邮件
（日期为北京时间当天，格式 YYYY-MM-DD）。

若当天未提交且启用了提醒（WORK_PLAN_REMIND_ENABLED=true），
则通过 SMTP 发送提醒邮件到 WORK_PLAN_REMIND_TO。

自动提交（auto_submit_today）：若 23:55 仍未提交，则用默认模板
（工作计划[日期] + 1、2、3、）发送计划邮件给 working@cet-electric.com，
由其自动回执产生「工作计划[日期]--[提交成功]」；再发通知到 WORK_PLAN_REMIND_TO。
"""

import email
import imaplib
import logging
import re
import ssl
import time
from datetime import datetime, timedelta, timezone
from email.header import decode_header
from email.message import Message

from app import legacy_config as config
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 北京时间（UTC+8）
BEIJING_TZ = timezone(timedelta(hours=8))


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
    """
    主题是否匹配「--工作计划[YYYY-MM-DD]--[提交成功]」

    兼容可能的前缀（如姓名）与后缀（如(不够300字)），日期严格匹配传入的 date_str。
    """
    pattern = re.escape(plan_subject) + r"\[" + re.escape(date_str) + r"\]--\[提交成功\]"
    return re.search(pattern, subject, flags=re.IGNORECASE) is not None


class WorkPlanChecker:
    """工作计划提交检查器 - 通过 IMAP 检查并（可选）发送提醒"""

    def __init__(self) -> None:
        settings = get_settings()
        self.plan_subject = settings.work_plan_subject or "工作计划"
        self.remind_enabled = settings.work_plan_remind_enabled
        self.remind_to = settings.work_plan_remind_to
        self.connection = None

    def check_today(self) -> dict:
        """
        检查当天（北京时间）是否已提交工作计划

        Returns:
            {
                "submitted": bool,   # 当天是否已提交
                "date": str,         # 检查的日期 YYYY-MM-DD
                "matched": int,      # 匹配到的工作计划邮件数
                "message": str,      # 人类可读摘要
            }
        """
        date_str = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        matched = 0
        try:
            if not self._connect():
                return {
                    "submitted": False,
                    "date": date_str,
                    "matched": 0,
                    "message": f"{date_str} 工作计划检查失败：无法连接邮箱",
                }
            try:
                matched = self._count_matching_emails(date_str)
            finally:
                self._disconnect()
        except Exception as error:
            logger.error("检查工作计划提交失败: %s", error)
            return {
                "submitted": False,
                "date": date_str,
                "matched": 0,
                "message": f"{date_str} 工作计划检查失败：{error}",
            }

        submitted = matched > 0
        message = (
            f"{date_str} 已提交工作计划（{matched} 封）"
            if submitted
            else f"{date_str} 未提交工作计划"
        )
        logger.info("工作计划检查: %s", message)

        if not submitted and self.remind_enabled and self.remind_to:
            self._send_reminder(date_str)

        return {
            "submitted": submitted,
            "date": date_str,
            "matched": matched,
            "message": message,
        }

    def _connect(self) -> bool:
        """建立并登录 IMAP 连接"""
        try:
            if not config.IMAP_USERNAME or not config.IMAP_PASSWORD:
                logger.error("未配置邮箱账号，无法检查工作计划")
                return False
            if config.IMAP_USE_SSL:
                context = ssl.create_default_context()
                self.connection = imaplib.IMAP4_SSL(
                    config.IMAP_SERVER, config.IMAP_PORT, ssl_context=context
                )
            else:
                self.connection = imaplib.IMAP4(config.IMAP_SERVER, config.IMAP_PORT)
            self.connection.login(config.IMAP_USERNAME, config.IMAP_PASSWORD)
            logger.debug("工作计划检查: IMAP 登录成功")
            return True
        except Exception as error:
            logger.error("工作计划检查: IMAP 登录失败: %s", error)
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
        """统计邮箱中匹配「{plan}[{date}]--[提交成功]」的邮件数"""
        mailbox = config.IMAP_MAILBOX
        status, select_data = self.connection.select(mailbox, readonly=True)
        if status != "OK":
            logger.error("工作计划检查: 无法打开邮箱文件夹 %s", mailbox)
            return 0

        status, data = self.connection.uid("search", None, "ALL")
        if status != "OK" or not data or not data[0]:
            return 0
        uids = data[0].split()
        if not uids:
            return 0

        matched = 0
        # 分批获取头部，避免一次拉取过多
        CHUNK = 200
        for i in range(0, len(uids), CHUNK):
            chunk = uids[i : i + CHUNK]
            status, batch = self.connection.uid(
                "fetch", b",".join(chunk), "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])"
            )
            if status != "OK":
                continue
            for item in batch:
                if not (isinstance(item, tuple) and len(item) == 2):
                    continue
                header_bytes = item[1]
                if isinstance(header_bytes, bytes):
                    header_bytes = header_bytes.decode("utf-8", errors="replace")
                msg: Message = email.message_from_string(header_bytes)
                subject = _decode_subject(str(msg.get("Subject", "")))
                if _subject_matches(subject, self.plan_subject, date_str):
                    matched += 1
        return matched

    def _send_reminder(self, date_str: str) -> None:
        """发送"未提交工作计划"提醒邮件"""
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
        """
        若当天（北京时间）仍未提交工作计划，则自动提交并通知。

        流程：
            1. 检查当天是否已提交（存在「工作计划[今天]--[提交成功]」回执）
            2. 未提交 → 用默认模板发送计划邮件给 working@cet-electric.com
               （主题「工作计划[今天]」，正文「工作计划[今天] + 1、2、3、」）
            3. 短暂等待后再次确认回执是否到达
            4. 发通知邮件到 WORK_PLAN_REMIND_TO

        Returns:
            人类可读结果字符串
        """
        from app.services.email_sender import sender as email_sender

        date_str = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        # 1. 先检查当天是否已提交
        check = self.check_today()
        if check["submitted"]:
            self._notify_auto_submit(date_str, already_submitted=True)
            return f"{date_str} 已提交，无需自动提交（{check['message']}）"

        # 2. 未提交 → 自动发送计划邮件给 working（默认模板）
        recipient = "working@cet-electric.com"
        subject = f"{self.plan_subject}[{date_str}]"
        content = f"{self.plan_subject}[{date_str}]\n1、\n2、\n3、"
        try:
            email_sender.send(to_addr=recipient, subject=subject, content=content)
            logger.info(
                "已自动发送计划邮件 %s -> %s（等待回执）", subject, recipient
            )
        except Exception as error:
            self._notify_auto_submit(date_str, error=str(error))
            return f"{date_str} 自动提交失败：{error}"

        # 3. 等待回执到达（最多 120 秒，每 15 秒检查一次）
        for _ in range(8):
            time.sleep(15)
            if self.check_today()["submitted"]:
                self._notify_auto_submit(date_str, already_submitted=True)
                return f"{date_str} 自动提交成功（已收到回执）"

        # 回执未在等待窗口内到达
        self._notify_auto_submit(date_str, error="回执未在 120 秒内到达")
        return f"{date_str} 自动提交已发送，但未在 120 秒内确认回执"

    def _notify_auto_submit(
        self, date_str: str, already_submitted: bool = False, error: str | None = None
    ) -> None:
        """发送自动提交结果通知到 WORK_PLAN_REMIND_TO"""
        from app.services.email_sender import sender as email_sender

        if not self.remind_to:
            return
        if error:
            subject = f"工作计划自动提交失败[{date_str}]"
            content = (
                f"您好，\n\n"
                f"今天（{date_str}）的工作计划自动提交失败：{error}\n\n"
                f"请手动提交。\n\n"
                f"本邮件由 CETWorkOverTime 自动发送。"
            )
        elif already_submitted:
            subject = f"工作计划自动提交确认[{date_str}]"
            content = (
                f"您好，\n\n"
                f"今天（{date_str}）的工作计划已提交，无需自动提交。\n\n"
                f"本邮件由 CETWorkOverTime 自动发送。"
            )
        else:
            subject = f"工作计划自动提交成功[{date_str}]"
            content = (
                f"您好，\n\n"
                f"今天（{date_str}）的工作计划已自动提交成功。\n\n"
                f"本邮件由 CETWorkOverTime 自动发送。"
            )
        try:
            email_sender.send(to_addr=self.remind_to, subject=subject, content=content)
            logger.info("已发送自动提交通知到 %s", self.remind_to)
        except Exception as error:
            logger.error("发送自动提交通知失败: %s", error)


work_plan_checker = WorkPlanChecker()