from unittest.mock import MagicMock, patch

import pytest

from app.services.email_sender import (
    DeliveryFailedError,
    DeliveryUncertainError,
    EmailSender,
    PartialDeliveryError,
    sender,
)


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


def test_send_uses_verified_smtp_ssl_and_logs_in() -> None:
    configured = _configured_sender(use_ssl=True, port=465)
    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server
    mock_server.sendmail.return_value = {}

    with (
        patch("app.services.email_sender.ssl.create_default_context") as create_context,
        patch("app.services.email_sender.smtplib.SMTP_SSL", return_value=mock_server) as smtp_ssl,
    ):
        result = configured.send(
            "boss@example.com", "年度报告", "正文内容", html="<p>正文内容</p>"
        )

    smtp_ssl.assert_called_once_with(
        "smtp.example.com", 465, timeout=30, context=create_context.return_value
    )
    mock_server.login.assert_called_once_with("user@example.com", "secret")
    assert result is None


def test_send_uses_verified_starttls_when_ssl_disabled() -> None:
    configured = _configured_sender(use_ssl=False, port=587)
    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server
    mock_server.sendmail.return_value = {}

    with (
        patch("app.services.email_sender.ssl.create_default_context") as create_context,
        patch("app.services.email_sender.smtplib.SMTP", return_value=mock_server) as smtp,
    ):
        configured.send("boss@example.com", "主题", "正文")

    smtp.assert_called_once_with("smtp.example.com", 587, timeout=30)
    mock_server.starttls.assert_called_once_with(context=create_context.return_value)


def test_send_runs_prepare_callback_after_connect_before_delivery() -> None:
    configured = _configured_sender(use_ssl=True, port=465)
    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server
    mock_server.sendmail.return_value = {}
    configured._connect = MagicMock(return_value=mock_server)  # type: ignore[method-assign]
    prepared = MagicMock()

    configured.send("boss@example.com", "主题", "正文", before_send=prepared)

    prepared.assert_called_once_with()
    mock_server.sendmail.assert_called_once()


def test_connect_failure_is_reported_as_definite_failure() -> None:
    configured = _configured_sender(use_ssl=True, port=465)
    configured._connect = MagicMock(  # type: ignore[method-assign]
        side_effect=OSError("connection refused")
    )

    with pytest.raises(DeliveryFailedError, match="connection refused"):
        configured.send("boss@example.com", "主题", "正文")


def test_disconnect_during_send_is_reported_as_uncertain() -> None:
    configured = _configured_sender(use_ssl=True, port=465)
    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server
    mock_server.sendmail.side_effect = OSError("connection reset")
    configured._connect = MagicMock(return_value=mock_server)  # type: ignore[method-assign]

    with pytest.raises(DeliveryUncertainError, match="connection reset"):
        configured.send("boss@example.com", "主题", "正文")


def test_send_raises_partial_delivery_error_for_refused_recipient() -> None:
    configured = _configured_sender(use_ssl=True, port=465)
    mock_server = MagicMock()
    mock_server.__enter__.return_value = mock_server
    mock_server.sendmail.return_value = {"boss@example.com": (550, b"rejected")}
    configured._connect = MagicMock(return_value=mock_server)  # type: ignore[method-assign]

    with pytest.raises(PartialDeliveryError) as raised:
        configured.send(
            "boss@example.com", "主题", "正文", cc=["accepted@example.com"]
        )

    assert raised.value.refused_recipients == ["boss@example.com"]
    assert raised.value.accepted_recipients == ["accepted@example.com"]


def test_send_raises_when_not_configured() -> None:
    configured = EmailSender()
    configured.host = ""
    configured.username = ""
    configured.password = ""
    configured.from_addr = ""

    with pytest.raises(RuntimeError, match="SMTP 未配置"):
        configured.send("boss@example.com", "主题", "正文")


def test_send_message_contains_headers_and_both_parts() -> None:
    configured = EmailSender()
    configured.username = "user@example.com"
    configured.from_addr = "user@example.com"

    message = configured._build_message(
        "boss@example.com", "年度报告", "纯文本正文", html="<p>HTML 正文</p>"
    )

    assert message["To"] == "boss@example.com"
    assert message["Subject"] == "年度报告"
    decoded = b"".join(part.get_payload(decode=True) for part in message.get_payload())
    assert "纯文本正文".encode() in decoded
    assert "<p>HTML 正文</p>".encode() in decoded


def test_module_singleton_is_configured_sender() -> None:
    assert isinstance(sender, EmailSender)


def _configured_sender(*, use_ssl: bool, port: int) -> EmailSender:
    configured = EmailSender()
    configured.host = "smtp.example.com"
    configured.port = port
    configured.use_ssl = use_ssl
    configured.username = "user@example.com"
    configured.password = "secret"
    configured.from_addr = "user@example.com"
    return configured
