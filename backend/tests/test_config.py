from app.core.config import PROJECT_ROOT, Settings


def test_settings_accept_legacy_environment_names() -> None:
    settings = Settings(
        _env_file=None,
        WORK_SUMMARY_DIR="mail-cache",
        OUTPUT_DIR="reports",
        EMAIL_USERNAME="user@example.com",
        DB_HOST="database.internal",
        DILIGENCE_TARGET_HOURS="40",
    )

    assert settings.work_summary_dir == PROJECT_ROOT / "mail-cache"
    assert settings.output_dir == PROJECT_ROOT / "reports"
    assert settings.imap_username == "user@example.com"
    assert settings.db_host == "database.internal"
    assert settings.diligence_target_hours == 40
