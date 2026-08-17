from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select

from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.qa import router as qa_router
from app.api.routes.reports import router as reports_router
from app.api.routes.search import router as search_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app import models  # noqa: F401  (register models before create_all)
from app.db.session import create_all_tables, SessionLocal
from app.ingestion.pipeline import reconcile_index
from app.models import User
from app.services.queue import get_task_queue, shutdown_task_queue

logger = logging.getLogger(__name__)

# Directory where the built React app is copied inside the Docker image.
# Empty when running the backend alone locally (the Vite dev server is used).
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _bootstrap_admin():
    """Create admin user at startup if ADMIN_BOOTSTRAP is enabled."""
    with SessionLocal() as session:
        existing = session.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        ).scalar_one_or_none()
        if existing:
            logger.info("admin user '%s' already exists, skipping bootstrap", settings.ADMIN_USERNAME)
            return
        user = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            role=settings.ADMIN_ROLE,
        )
        session.add(user)
        session.commit()
        logger.info("bootstrapped admin user '%s'", settings.ADMIN_USERNAME)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.DEBUG)
    create_all_tables()
    if settings.ADMIN_BOOTSTRAP:
        _bootstrap_admin()
    get_task_queue()
    repaired = reconcile_index()
    if any(repaired.values()):
        logger.info("startup index reconciliation: %s", repaired)
    yield
    shutdown_task_queue()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered financial due diligence copilot with grounded, "
        "evidence-cited answers."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True if settings.CORS_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(search_router, prefix=settings.API_V1_PREFIX)
app.include_router(qa_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)


# ---- Static SPA serving (production, single-port deployment) ----
# The built frontend is served by FastAPI so the app is reachable on one port.
# Only active when the static directory exists (i.e. inside the Docker image).
if (STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def serve_spa(full_path: str) -> FileResponse | JSONResponse:
    if not STATIC_DIR.is_dir():
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    if full_path.startswith(settings.API_V1_PREFIX.lstrip("/")):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    candidate = (STATIC_DIR / full_path).resolve()
    if full_path and candidate.is_file() and str(candidate).startswith(str(STATIC_DIR.resolve())):
        return FileResponse(candidate)
    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"detail": "Not Found"}, status_code=404)
