from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.config import get_settings
from app.core.database import get_engine
from app.repositories.email_repository import EmailRepository


def get_repository() -> EmailRepository:
    settings = get_settings()
    return EmailRepository(get_engine(), settings.diligence_target_hours)


def require_session(request: Request) -> None:
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未授权，请先登录")


RepositoryDependency = Annotated[EmailRepository, Depends(get_repository)]
Authenticated = Annotated[None, Depends(require_session)]
