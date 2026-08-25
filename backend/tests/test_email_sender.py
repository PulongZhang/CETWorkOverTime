from unittest.mock import MagicMock, patch

from app.services.email_sender import EmailSender, sender


def test_sender_returns_configuration_state() -> None:
    configured = EmailSender()
    configured.host = "smtp.example.com"
    configured.username = "user@example.com"
    configured.password = "secret"
    configured.from_addr = "user@example.com"

    assert configured.is_configured() is True


def test_sender_reports_missing_configuration() -> None:
    configured = EmailSender()
    configured.host = ""
    configured.username = ""
    configured.password = ""
    configured.from_addr = ""

    assert configured.is_configured() is False


def test_send_uses_smtp_ssl_and_logs_in() -> None:
    configured = EmailSender()
    configured.host = "smtp.example.com"
    configured.port = 465
    configured.use_ssl = True
    configured.username = "user@example.com"
    configured.password = "secret"
    configured.from_addr = "user@example.com"

    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server
    mock_server.sendmail.return_value = {"user@example.com": "250 OK"}

    with patch("app.services.email_sender.smtplib.SMTP_SSL", return_value=mock_server) as smtp_ssl:
        result = configured.send(
            "boss@example.com", "年度报告", "正文内容", html="<p>正文内容</p>"
        )

    smtp_ssl.assert_called_once_with("smtp.example.com", 465, timeout=30)
    mock_server.login.assert_called_once_with("user@example.com", "secret")
    assert result == {"user@example.com": "250 OK"}


def test_send_uses_starttls_when_ssl_disabled() -> None:
    configured = EmailSender()
    configured.host = "smtp.example.com"
    configured.port = 587
    configured.use_ssl = False
    configured.username = "user@example.com"
    configured.password = "secret"
    configured.from_addr = "user@example.com"

    mock_server = MagicMock()

    with patch("app.services.email_sender.smtplib.SMTP", return_value=mock_server) as smtp:
        configured.send("boss@example.com", "主题", "正文")

    smtp.assert_called_once_with("smtp.example.com", 587, timeout=30)
    mock_server.starttls.assert_called_once_with()


def test_send_raises_when_not_configured() -> None:
    configured = EmailSender()
    configured.host = ""
    configured.username = ""
    configured.password = ""
    configured.from_addr = ""

    try:
        configured.send("boss@example.com", "主题", "正文")
    except RuntimeError as error:
        assert "SMTP 未配置" in str(error)
    else:
        raise AssertionError("应抛出 RuntimeError")


def test_send_message_contains_headers_and_both_parts() -> None:
    configured = EmailSender()
    configured.username = "user@example.com"
    configured.from_addr = "user@example.com"

    message = configured._build_message(
        "boss@example.com", "年度报告", "纯文本正文", html="<p>HTML 正文</p>"
    )

    assert message["To"] == "boss@example.com"
    assert message["Subject"] == "年度报告"
    decoded = b"".join(
        part.get_payload(decode=True) for part in message.get_payload()
    )
    assert "纯文本正文".encode("utf-8") in decoded
    assert "<p>HTML 正文</p>".encode("utf-8") in decoded


def test_module_singleton_is_configured_sender() -> None:
    assert isinstance(sender, EmailSender)