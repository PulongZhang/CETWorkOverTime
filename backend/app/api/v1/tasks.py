from collections.abc import Callable

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import Authenticated
from app.core.config import get_settings
from app.services.email_processor import EmailProcessor
from app.services.task_service import task_actions, task_manager

router = APIRouter(prefix="/tasks", tags=["tasks"])


class FetchRequest(BaseModel):
    days: int = Field(default=365, ge=1, le=3650)


class ProcessRequest(BaseModel):
    force: bool = False


@router.get("/current")
def current_task(_: Authenticated) -> dict:
    return task_manager.status()


@router.post("/fetch")
def fetch_emails(payload: FetchRequest, _: Authenticated) -> dict:
    settings = get_settings()
    if not settings.imap_username or not settings.imap_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置邮箱账号")
    return _submit("fetch", lambda: task_actions.fetch_and_sync(payload.days))


@router.post("/process")
def process_emails(payload: ProcessRequest, _: Authenticated) -> dict:
    return _submit("process", lambda: task_actions.process(payload.force))


@router.post("/fetch-and-process")
def fetch_and_process(payload: FetchRequest, _: Authenticated) -> dict:
    settings = get_settings()
    if not settings.imap_username or not settings.imap_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未配置邮箱账号")
    return _submit("fetch-and-process", lambda: task_actions.fetch_and_sync(payload.days))


@router.post("/sync-database")
def sync_database(_: Authenticated) -> dict:
    return _submit(
        "sync-database",
        lambda: str(EmailProcessor(get_settings().work_summary_dir).sync_to_db()),
    )


def _submit(task_type: str, action: Callable[[], str]) -> dict:
    try:
        return task_manager.submit(task_type, action)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
