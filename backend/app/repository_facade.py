from datetime import date, datetime
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.database import get_engine
from app.repositories.email_repository import EmailRepository


@lru_cache
def _repository() -> EmailRepository:
    settings = get_settings()
    return EmailRepository(get_engine(), settings.diligence_target_hours)


def bulk_save_emails(email_data_list: list[Any]) -> dict[str, int]:
    stats = {"saved": 0, "skipped": 0, "failed": 0}
    for email_data in email_data_list:
        try:
            if not email_data.date:
                stats["skipped"] += 1
                continue
            email_date = email_data.date
            if isinstance(email_date, datetime):
                email_date = email_date.date()
            result = _repository().save_email(
                email_date=email_date,
                subject=email_data.subject or "",
                sender=email_data.sender or "",
                content=email_data.content or "",
                raw_content=email_data.raw_content or "",
                source_filename=email_data.filename or "",
            )
            stats["saved" if result is not None else "skipped"] += 1
        except Exception:
            stats["failed"] += 1
    return stats


def get_meta(key: str) -> str | None:
    return _repository().get_meta(key)


def save_meta(key: str, value: str) -> None:
    _repository().save_meta(key, value)


def get_all_years() -> list[int]:
    return _repository().get_all_years()


def get_diligence_stats(year: int) -> dict[str, Any]:
    return _repository().get_diligence_stats(year)


def get_emails_by_month(year: int, month: int) -> list[dict[str, Any]]:
    return _repository().get_emails_by_month(year, month)


def get_email_by_date(email_date: date) -> dict[str, Any] | None:
    return _repository().get_email_by_date(email_date)
