from datetime import date, time, timedelta
from decimal import Decimal

import pytest

from app.repositories.email_repository import (
    parse_diligence_time,
    serialize_row,
    year_table_name,
)


def test_year_table_name_accepts_supported_year() -> None:
    assert year_table_name(2026) == "email_2026"


@pytest.mark.parametrize("year", [1999, 2101])
def test_year_table_name_rejects_unsupported_year(year: int) -> None:
    with pytest.raises(ValueError):
        year_table_name(year)


def test_parse_diligence_time_uses_last_entry_and_supports_midnight() -> None:
    result = parse_diligence_time(
        "[勤奋时间][09:00][10:00]\n[勤奋时间][23:30][01:00]"
    )

    assert result == {"start": "23:30", "end": "01:00", "hours": 1.5}


def test_serialize_row_matches_legacy_json_shapes() -> None:
    result = serialize_row(
        {
            "email_date": date(2026, 7, 30),
            "diligence_start": time(9, 5),
            "diligence_end": timedelta(hours=18, minutes=30),
            "diligence_hours": Decimal("2.50"),
        }
    )

    assert result == {
        "email_date": "2026-07-30",
        "diligence_start": "09:05",
        "diligence_end": "18:30",
        "diligence_hours": 2.5,
    }
