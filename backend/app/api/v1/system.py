from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from app.api.dependencies import Authenticated, RepositoryDependency
from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/status")
def system_status(_: Authenticated) -> dict:
    settings = get_settings()
    return {
        "stats": {
            "email_count": _count_files(settings.work_summary_dir, "*.eml"),
            "report_count": _count_files(settings.output_dir, "*工作总结.md"),
            "imap_configured": bool(settings.imap_username and settings.imap_password),
        },
        "scheduler": {
            "enabled": True,
            "interval_hours": settings.schedule_interval_hours,
            "next_run": None,
            "last_run": None,
            "last_result": None,
        },
        "task": {"running": False, "type": None, "message": ""},
    }


@router.get("/database/status")
def database_status(
    repository: RepositoryDependency,
    _: Authenticated,
) -> dict:
    try:
        with repository.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        years = repository.get_all_years()
        return {"available": True, "years": years}
    except Exception as error:
        return {"available": False, "error": str(error)}


def _count_files(directory: Path, pattern: str) -> int:
    return len(list(directory.glob(pattern))) if directory.exists() else 0
