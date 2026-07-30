from fastapi import APIRouter

from app.api.dependencies import Authenticated, RepositoryDependency

router = APIRouter(prefix="/diligence", tags=["diligence"])


@router.get("")
def diligence_summary(
    repository: RepositoryDependency,
    _: Authenticated,
) -> dict:
    years = repository.get_all_years()
    return {
        "target_hours": repository.target_hours,
        "years": {str(year): repository.get_diligence_stats(year) for year in years},
    }


@router.get("/{year}/{month}")
def diligence_month(
    year: int,
    month: int,
    repository: RepositoryDependency,
    _: Authenticated,
) -> dict:
    emails = repository.get_emails_by_month(year, month)
    return {
        "year": year,
        "month": month,
        "days": [
            {
                "date": email["email_date"],
                "subject": email.get("subject", ""),
                "hours": email.get("diligence_hours", 0),
                "start": email.get("diligence_start"),
                "end": email.get("diligence_end"),
                "content": email.get("content", ""),
            }
            for email in emails
        ],
    }
