import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import OperationalError

from app.api.routes import router as api_router
from app.db import ensure_schema
from app.ingest import run_seed_ingest
from app.settings import settings
from app.support_bus.cdc import router as cdc_router
from app.support_bus.consumer import router as consumer_router

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "ui" / "templates"))

app = FastAPI(title="StudyForge Support", version="0.1.0")
app.include_router(api_router)
app.include_router(cdc_router)
app.include_router(consumer_router)


def page_context(*, require_staff: bool) -> dict:
    auth_domain = settings.firebase_auth_domain
    if not auth_domain and settings.firebase_project_id:
        auth_domain = f"{settings.firebase_project_id}.firebaseapp.com"
    return {
        "studyforge_web_url": settings.studyforge_web_url,
        "require_staff": require_staff,
        "firebase_config": {
            "apiKey": settings.firebase_web_api_key,
            "authDomain": auth_domain,
            "projectId": settings.firebase_project_id,
            "emulatorAuthUrl": settings.firebase_web_auth_emulator_url or None,
        },
    }


@app.on_event("startup")
def startup() -> None:
    try:
        ensure_schema()
    except OperationalError:
        # Health and static pages work without Postgres (unit tests, docs).
        return
    if settings.local_cdc_shortcut:
        try:
            from app.support_bus.local_watch import start_local_command_watch

            start_local_command_watch()
        except Exception:
            logger.exception("Local CDC shortcut failed to start")
    if not settings.seed_on_startup:
        return
    try:
        run_seed_ingest()
    except Exception:
        logger.exception("Seed ingest failed; API will still serve")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def user_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "user_home.html",
        page_context(require_staff=False),
    )


@app.get("/staff", response_class=HTMLResponse)
def staff_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "staff_home.html",
        page_context(require_staff=True),
    )
