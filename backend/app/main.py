from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.router import router as api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="CETWorkOverTime API",
    version="3.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
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


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
