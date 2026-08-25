from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    work_summary_dir: Path = Field(default=PROJECT_ROOT / "工作总结", alias="WORK_SUMMARY_DIR")
    output_dir: Path = Field(default=PROJECT_ROOT / "output", alias="OUTPUT_DIR")

    imap_server: str = Field(default="imap.exmail.qq.com", alias="IMAP_SERVER")
    imap_port: int = Field(default=993, alias="IMAP_PORT")
    imap_use_ssl: bool = Field(default=True, alias="IMAP_USE_SSL")
    imap_username: str = Field(default="", alias="EMAIL_USERNAME")
    imap_password: str = Field(default="", alias="EMAIL_PASSWORD")
    imap_mailbox: str = Field(default="&XeVPXGXlX9c-", alias="IMAP_MAILBOX")
    work_plan_mailbox: str = Field(default="", alias="WORK_PLAN_MAILBOX")
    imap_search_subject: str = Field(default="--工作日志", alias="IMAP_SEARCH_SUBJECT")
    imap_search_days: int = Field(default=365, alias="IMAP_SEARCH_DAYS")

    smtp_host: str = Field(default="smtp.exmail.qq.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=465, alias="SMTP_PORT")
    smtp_use_ssl: bool = Field(default=True, alias="SMTP_USE_SSL")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from: str = Field(default="", alias="SMTP_FROM")

    totp_secret: str = Field(default="JBSWY3DPEHPK3PXP", alias="TOTP_SECRET")
    secret_key: str = Field(default="cetworkovertime-super-secret-key", alias="SECRET_KEY")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")

    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=3306, alias="DB_PORT")
    db_user: str = Field(default="root", alias="DB_USER")
    db_password: str = Field(default="", alias="DB_PASSWORD")
    db_name: str = Field(default="cetworkovertime", alias="DB_NAME")
    db_charset: str = Field(default="utf8mb4", alias="DB_CHARSET")

    diligence_target_hours: float = Field(default=36, alias="DILIGENCE_TARGET_HOURS")
    schedule_time: str = Field(default="21:00", alias="SCHEDULE_TIME")
    cleanup_eml_after_sync: bool = Field(default=True, alias="CLEANUP_EML_AFTER_SYNC")
    work_plan_subject: str = Field(default="工作计划", alias="WORK_PLAN_SUBJECT")
    work_plan_remind_enabled: bool = Field(default=True, alias="WORK_PLAN_REMIND_ENABLED")
    work_plan_remind_to: str = Field(default="", alias="WORK_PLAN_REMIND_TO")

    def model_post_init(self, __context: object) -> None:
        if not self.work_summary_dir.is_absolute():
            self.work_summary_dir = PROJECT_ROOT / self.work_summary_dir
        if not self.output_dir.is_absolute():
            self.output_dir = PROJECT_ROOT / self.output_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()
