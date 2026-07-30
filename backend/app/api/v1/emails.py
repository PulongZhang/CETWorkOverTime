from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import Authenticated, RepositoryDependency

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("")
def list_emails(
    repository: RepositoryDependency,
    _: Authenticated,
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
) -> dict:
    emails = repository.get_emails_by_month(year, month)
    return {"count": len(emails), "emails": emails}


@router.get("/{email_date}")
def email_detail(
    email_date: date,
    repository: RepositoryDependency,
    _: Authenticated,
) -> dict:
    email = repository.get_email_by_date(email_date)
    if not email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到邮件")
    return {"email": email}
