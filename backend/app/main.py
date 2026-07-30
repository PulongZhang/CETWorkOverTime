import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import router as api_router
from app.core.config import PROJECT_ROOT, get_settings
from app.core.database import dispose_engine
from app.scheduler import mail_scheduler
from app.services.task_service import task_manager

settings = get_settings()
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    mail_scheduler.start()
    yield
    mail_scheduler.stop()
    task_manager.shutdown()
    dispose_engine()


app = FastAPI(
    title="CETWorkOverTime API",
    version="3.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="cetworkovertime_session",
    max_age=8 * 60 * 60,
    same_site="lax",
    https_only=settings.cookie_secure,
)
app.include_router(api_router)


@app.exception_handler(SQLAlchemyError)
def database_error_handler(_: Request, error: SQLAlchemyError) -> JSONResponse:
    logger.error(
        "数据库操作失败",
        exc_info=(type(error), error, error.__traceback__),
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "数据库暂时不可用，请稍后重试"},
    )


if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str) -> FileResponse:
    if full_path.startswith("api/"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    requested = frontend_dist / full_path
    is_frontend_file = (
        full_path
        and requested.is_file()
        and requested.resolve().is_relative_to(frontend_dist.resolve())
    )
    if is_frontend_file:
        return FileResponse(requested)

    index = frontend_dist / "index.html"
    if not index.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="前端尚未构建")
    return FileResponse(index)
