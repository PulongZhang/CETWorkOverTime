from fastapi import APIRouter

from app.api.v1 import auth, diligence, emails, reports, system

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(diligence.router)
router.include_router(emails.router)
router.include_router(reports.router)
router.include_router(system.router)
