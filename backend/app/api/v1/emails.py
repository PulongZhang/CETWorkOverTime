from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.api.dependencies import Authenticated, RepositoryDependency
from app.core.config import get_settings
from app.services.email_sender import PartialDeliveryError
from app.services.email_sender import sender as email_sender
from app.services.work_plan_checker import AUTO_SUBMIT_RECIPIENT

router = APIRouter(prefix="/emails", tags=["emails"])


class SendEmailRequest(BaseModel):
    to: str = Field(max_length=254)
    cc: list[str] = Field(default_factory=list, max_length=10)
    subject: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    html: str | None = None


@router.get("")
def list_emails(
    repository: RepositoryDependency,
    _: Authenticated,
    year: int = Query(ge=2000, le=2100),
    month: int = Query(ge=1, le=12),
) -> dict:
    emails = repository.get_emails_by_month(year, month)
    return {"count": len(emails), "emails": emails}


@router.get("/compose-config")
def compose_config(_: Authenticated) -> dict:
    settings = get_settings()
    return {
        "recipient": AUTO_SUBMIT_RECIPIENT,
        "plan_subject": settings.work_plan_subject or "工作计划",
    }


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


@router.post("/send", response_model=None)
def send_email(payload: SendEmailRequest, _: Authenticated) -> dict | JSONResponse:
    if not email_sender.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP 未配置，请在 .env 中设置 SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD",
        )
    try:
        email_sender.send(
            to_addr=payload.to,
            cc=payload.cc or None,
            subject=payload.subject,
            content=payload.content,
            html=payload.html,
        )
    except PartialDeliveryError as error:
        return JSONResponse(
            status_code=status.HTTP_207_MULTI_STATUS,
            content={
                "success": False,
                "partial": True,
                "to": payload.to,
                "subject": payload.subject,
                "accepted_recipients": error.accepted_recipients,
                "refused_recipients": error.refused_recipients,
                "error": "部分收件人被邮件服务器拒绝",
            },
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"邮件发送失败: {error}",
        ) from error
    return {"success": True, "to": payload.to, "subject": payload.subject}
