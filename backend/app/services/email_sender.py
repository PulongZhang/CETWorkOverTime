"""
邮件发送模块 - 通过 SMTP 协议发送邮件

支持 SSL/TLS 连接，发送纯文本或 HTML 邮件。
"""

import logging
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailSender:
    """邮件发送器 - 通过 SMTP 发送邮件"""

    def __init__(self) -> None:
        settings = get_settings()
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.use_ssl = settings.smtp_use_ssl
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.from_addr = settings.smtp_from or settings.smtp_username

    def is_configured(self) -> bool:
        """SMTP 配置是否完整"""
        return bool(self.host and self.username and self.password and self.from_addr)

    def send(
        self,
        to_addr: str,
        subject: str,
        content: str,
        html: Optional[str] = None,
        cc: Optional[list[str]] = None,
    ) -> str:
        """
        发送一封邮件

        Args:
            to_addr: 收件人地址
            subject: 邮件主题
            content: 邮件正文（纯文本）
            html: 可选 HTML 正文，提供时作为替代内容发送
            cc: 可选抄送地址列表

        Returns:
            SMTP 服务器返回的响应字符串
        """
        if not self.is_configured():
            raise RuntimeError(
                "SMTP 未配置，请在 .env 中设置 SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD"
            )

        recipients = [to_addr, *(cc or [])]
        message = self._build_message(to_addr, subject, content, html, cc)
        with self._connect() as server:
            response = server.sendmail(
                self.from_addr, recipients, message.as_string()
            )
        logger.info("邮件发送成功: %s -> %s", subject, recipients)
        return response

    def _connect(self) -> smtplib.SMTP:
        """建立 SMTP 连接并登录（SSL 或 STARTTLS）"""
        if self.use_ssl:
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                self.host, self.port, timeout=30
            )
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.starttls()
        server.login(self.username, self.password)
        return server

    def _build_message(
        self,
        to_addr: str,
        subject: str,
        content: str,
        html: Optional[str],
        cc: Optional[list[str]] = None,
    ) -> MIMEMultipart:
        """构造 MIME 邮件消息（中文主题使用 UTF-8 编码）"""
        message = MIMEMultipart("alternative")
        message["From"] = self.from_addr
        message["To"] = to_addr
        if cc:
            message["Cc"] = ", ".join(cc)
        message["Subject"] = Header(subject, "utf-8")

        message.attach(MIMEText(content, "plain", "utf-8"))
        if html:
            message.attach(MIMEText(html, "html", "utf-8"))
        return message


sender = EmailSender()