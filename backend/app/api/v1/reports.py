from fastapi import APIRouter

from app.api.dependencies import Authenticated, RepositoryDependency
from app.services.report_service import build_monthly_markdown, render_markdown

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports(
    repository: RepositoryDependency,
    _: Authenticated,
) -> dict:
    reports = []
    for year in sorted(repository.get_all_years(), reverse=True):
        stats = repository.get_diligence_stats(year)
        for month in sorted(stats["months"], key=lambda item: item["month"], reverse=True):
            reports.append(
                {
                    "year": year,
                    "month": month["month"],
                    "filename": f"{year}年{month['month']:02d}月工作总结.md",
                    "entries": month["entries"],
                    "hours": month["hours"],
                }
            )
    return {"reports": reports}


@router.get("/{year}/{month}")
def report_detail(
    year: int,
    month: int,
    repository: RepositoryDependency,
    _: Authenticated,
) -> dict:
    content = build_monthly_markdown(year, month, repository.get_emails_by_month(year, month))
    return {
        "year": year,
        "month": month,
        "filename": f"{year}年{month:02d}月工作总结.md",
        "markdown": content,
        "html": render_markdown(content),
    }
