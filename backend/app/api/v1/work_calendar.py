from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import Authenticated
from app.services.work_calendar import work_calendar

router = APIRouter(prefix="/work-calendar", tags=["work-calendar"])
BEIJING_TZ = timezone(timedelta(hours=8))


class LeaveRangeRequest(BaseModel):
    start_date: date
    end_date: date


def _snapshot() -> dict:
    try:
        return work_calendar.snapshot(datetime.now(BEIJING_TZ).date())
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@router.get("")
def get_work_calendar(_: Authenticated) -> dict:
    return _snapshot()


@router.post("/leaves")
def add_leave(payload: LeaveRangeRequest, _: Authenticated) -> dict:
    try:
        work_calendar.add_leave_range(payload.start_date, payload.end_date)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    return _snapshot()


@router.delete("/leaves/{leave_date}")
def delete_leave(leave_date: date, _: Authenticated) -> dict:
    try:
        work_calendar.remove_leave(leave_date)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    return _snapshot()
