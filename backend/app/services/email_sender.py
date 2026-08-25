"""
邮件发送模块 - 通过 SMTP 协议发送邮件

支持 SSL/TLS 连接，发送纯文本或 HTML 邮件。
"""

import logging
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Callable, Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DeliveryFailedError(RuntimeError):
    """SMTP 在明确未接受邮件的阶段失败。"""


class DeliveryUncertainError(RuntimeError):
    """SMTP 发送已开始，但无法确认服务器最终是否接受邮件。"""


class PartialDeliveryError(RuntimeError):
    """SMTP 接受了部分收件人，但拒绝了其他收件人。"""

    def __init__(
        self,
        refused: dict[str, tuple[int, bytes]],
        recipients: list[str],
    ) -> None:
        self.refused_recipients = list(refused)
        self.accepted_recipients = [address for address in recipients if address not in refused]
        super().__init__(f"部分收件人被拒绝: {', '.join(self.refused_recipients)}")


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
        before_send: Optional[Callable[[], None]] = None,
    ) -> None:
        """发送邮件，并区分明确失败、投递结果未知和部分拒收。"""
        if not self.is_configured():
            raise RuntimeError(
                "SMTP 未配置，请在 .env 中设置 SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD"
            )

        recipients = [to_addr, *(cc or [])]
        message = self._build_message(to_addr, subject, content, html, cc)
        try:
            server = self._connect()
        except Exception as error:
            raise DeliveryFailedError(str(error)) from error

        if before_send:
            try:
                before_send()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass
                raise

        try:
            with server:
                refused = server.sendmail(self.from_addr, recipients, message.as_string())
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as error:
            raise DeliveryFailedError(str(error)) from error
        except (smtplib.SMTPHeloError, smtplib.SMTPDataError) as error:
            raise DeliveryFailedError(str(error)) from error
        except Exception as error:
            raise DeliveryUncertainError(str(error)) from error

        if refused:
            logger.warning("邮件部分发送失败: %s，拒绝地址: %s", subject, list(refused))
            raise PartialDeliveryError(refused, recipients)
        logger.info("邮件发送成功: %s -> %s", subject, recipients)

    def _connect(self) -> smtplib.SMTP:
        """建立验证服务器证书的 SMTP 连接并登录。"""
        context = ssl.create_default_context()
        if self.use_ssl:
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                self.host,
                self.port,
                timeout=30,
                context=context,
            )
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.starttls(context=context)
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
