from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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
from app import models  # noqa: F401  (register models before create_all)
from app.db.session import create_all_tables
from app.ingestion.pipeline import reconcile_index
from app.services.queue import get_task_queue, shutdown_task_queue

logger = logging.getLogger(__name__)

# Directory where the built React app is copied inside the Docker image.
# Empty when running the backend alone locally (the Vite dev server is used).
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.DEBUG)
    create_all_tables()
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
    allow_credentials=True,
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
