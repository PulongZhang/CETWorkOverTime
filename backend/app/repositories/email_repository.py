import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine, inspect, text

YEAR_TABLE_PATTERN = re.compile(r"^email_(\d{4})$")


def year_table_name(year: int) -> str:
    if year < 2000 or year > 2100:
        raise ValueError("year must be between 2000 and 2100")
    return f"email_{year}"


def parse_diligence_time(content: str) -> dict[str, Any]:
    matches = re.findall(r"\[勤奋时间\]\[(\d{1,2}:\d{2})\]\[(\d{1,2}:\d{2})\]", content or "")
    if not matches:
        return {}

    start_value, end_value = matches[-1]
    start_hour, start_minute = map(int, start_value.split(":"))
    end_hour, end_minute = map(int, end_value.split(":"))
    start_total = start_hour * 60 + start_minute
    end_total = end_hour * 60 + end_minute
    if end_total < start_total:
        end_total += 24 * 60

    return {
        "start": start_value,
        "end": end_value,
        "hours": round((end_total - start_total) / 60, 2),
    }


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
        elif isinstance(value, time):
            result[key] = value.strftime("%H:%M")
        elif isinstance(value, timedelta):
            total_seconds = int(value.total_seconds())
            result[key] = f"{total_seconds // 3600:02d}:{(total_seconds % 3600) // 60:02d}"
        elif isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    return result


class EmailRepository:
    def __init__(self, engine: Engine, target_hours: float = 36) -> None:
        self.engine = engine
        self.target_hours = target_hours
        self._ensured_tables: set[str] = set()

    def ensure_meta_table(self) -> None:
        if "email_meta" in self._ensured_tables:
            return
        ddl = """
        CREATE TABLE IF NOT EXISTS email_meta (
            id INTEGER PRIMARY KEY AUTO_INCREMENT,
            meta_key VARCHAR(100) NOT NULL UNIQUE,
            meta_value TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with self.engine.begin() as connection:
            connection.execute(text(ddl))
        self._ensured_tables.add("email_meta")

    def ensure_year_table(self, year: int) -> None:
        table = year_table_name(year)
        if table in self._ensured_tables:
            return
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            email_date DATE NOT NULL,
            subject VARCHAR(500) NOT NULL DEFAULT '',
            sender VARCHAR(200) NOT NULL DEFAULT '',
            content TEXT NOT NULL,
            raw_content MEDIUMTEXT,
            diligence_start TIME DEFAULT NULL,
            diligence_end TIME DEFAULT NULL,
            diligence_hours DECIMAL(5,2) DEFAULT 0,
            message_id VARCHAR(500) DEFAULT '',
            source_filename VARCHAR(500) DEFAULT '',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_email_date (email_date),
            INDEX idx_message_id (message_id),
            INDEX idx_year_month (email_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with self.engine.begin() as connection:
            connection.execute(text(ddl))
        self._ensured_tables.add(table)

    def save_email(
        self,
        email_date: date,
        subject: str = "",
        sender: str = "",
        content: str = "",
        raw_content: str = "",
        message_id: str = "",
        source_filename: str = "",
    ) -> int | None:
        self.ensure_year_table(email_date.year)
        table = year_table_name(email_date.year)
        diligence = parse_diligence_time(content)
        params = {
            "email_date": email_date,
            "subject": subject,
            "sender": sender,
            "content": content,
            "raw_content": raw_content,
            "diligence_start": diligence.get("start"),
            "diligence_end": diligence.get("end"),
            "diligence_hours": diligence.get("hours", 0),
            "message_id": message_id,
            "source_filename": source_filename,
        }

        with self.engine.begin() as connection:
            existing = connection.execute(
                text(f"SELECT id, diligence_hours FROM {table} WHERE email_date = :email_date"),
                {"email_date": email_date},
            ).mappings().first()
            if existing:
                if params["diligence_hours"] <= float(existing["diligence_hours"] or 0):
                    return None
                params["id"] = existing["id"]
                connection.execute(
                    text(
                        f"""UPDATE {table}
                        SET subject = :subject, sender = :sender, content = :content,
                            raw_content = :raw_content, diligence_start = :diligence_start,
                            diligence_end = :diligence_end, diligence_hours = :diligence_hours,
                            message_id = :message_id, source_filename = :source_filename
                        WHERE id = :id"""
                    ),
                    params,
                )
                return int(existing["id"])

            result = connection.execute(
                text(
                    f"""INSERT INTO {table}
                    (email_date, subject, sender, content, raw_content,
                     diligence_start, diligence_end, diligence_hours,
                     message_id, source_filename)
                    VALUES (:email_date, :subject, :sender, :content, :raw_content,
                            :diligence_start, :diligence_end, :diligence_hours,
                            :message_id, :source_filename)"""
                ),
                params,
            )
            return int(result.lastrowid)

    def get_emails_by_month(self, year: int, month: int) -> list[dict[str, Any]]:
        if month < 1 or month > 12:
            raise ValueError("month must be between 1 and 12")
        self.ensure_year_table(year)
        table = year_table_name(year)
        start = date(year, month, 1)
        end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"SELECT * FROM {table} "
                    "WHERE email_date >= :start AND email_date < :end ORDER BY email_date"
                ),
                {"start": start, "end": end},
            ).mappings()
            return [serialize_row(dict(row)) for row in rows]

    def get_email_by_date(self, email_date: date) -> dict[str, Any] | None:
        self.ensure_year_table(email_date.year)
        table = year_table_name(email_date.year)
        with self.engine.connect() as connection:
            row = connection.execute(
                text(f"SELECT * FROM {table} WHERE email_date = :email_date"),
                {"email_date": email_date},
            ).mappings().first()
            return serialize_row(dict(row)) if row else None

    def get_all_years(self) -> list[int]:
        years: list[int] = []
        for table in inspect(self.engine).get_table_names():
            match = YEAR_TABLE_PATTERN.fullmatch(table)
            if not match:
                continue
            with self.engine.connect() as connection:
                if connection.execute(text(f"SELECT 1 FROM {table} LIMIT 1")).first():
                    years.append(int(match.group(1)))
        return sorted(years)

    def get_diligence_stats(self, year: int) -> dict[str, Any]:
        self.ensure_year_table(year)
        table = year_table_name(year)
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    f"""SELECT MONTH(email_date) AS month,
                               COALESCE(SUM(diligence_hours), 0) AS hours,
                               COUNT(*) AS entries
                        FROM {table}
                        WHERE diligence_hours > 0
                        GROUP BY MONTH(email_date)
                        ORDER BY month"""
                )
            ).mappings()
            months = [
                {
                    "month": int(row["month"]),
                    "hours": round(float(row["hours"]), 2),
                    "entries": int(row["entries"]),
                    "target": self.target_hours,
                    "delta": round(float(row["hours"]) - self.target_hours, 2),
                }
                for row in rows
            ]

        total_hours = round(sum(item["hours"] for item in months), 2)
        total_target = round(len(months) * self.target_hours, 2)
        return {
            "year": year,
            "months": months,
            "total_hours": total_hours,
            "total_target": total_target,
            "total_delta": round(total_hours - total_target, 2),
        }

    def save_meta(self, key: str, value: str) -> None:
        self.ensure_meta_table()
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """INSERT INTO email_meta (meta_key, meta_value)
                    VALUES (:key, :value)
                    ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value)"""
                ),
                {"key": key, "value": value},
            )

    def get_meta(self, key: str) -> str | None:
        self.ensure_meta_table()
        with self.engine.connect() as connection:
            row = connection.execute(
                text("SELECT meta_value FROM email_meta WHERE meta_key = :key"),
                {"key": key},
            ).mappings().first()
            return str(row["meta_value"]) if row else None
