"""API routes module."""

from fastapi import APIRouter

from app.api.csv import router as csv_router
from app.api.projects import router as projects_router
from app.api.prompts import router as prompts_router
from app.api.pages import router as pages_router
from app.api.opportunities import router as opportunities_router
from app.api.competitive import router as competitive_router
from app.api.jobs import router as jobs_router

router = APIRouter()

# Include all route modules
router.include_router(csv_router, prefix="/csv", tags=["CSV Import"])
router.include_router(projects_router, prefix="/projects", tags=["Projects"])
router.include_router(prompts_router, prefix="/prompts", tags=["Prompts"])
router.include_router(pages_router, prefix="/pages", tags=["Pages"])
router.include_router(opportunities_router, prefix="/opportunities", tags=["Opportunities"])
router.include_router(competitive_router, prefix="/competitive", tags=["Competitive Analysis"])
router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])

