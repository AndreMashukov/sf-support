from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import OperationalError

from app.api.routes import router as api_router
from app.db import Base, engine
from app.settings import settings

templates = Jinja2Templates(directory=str(Path(__file__).parent / "ui" / "templates"))

app = FastAPI(title="StudyForge Support", version="0.1.0")
app.include_router(api_router)


@app.on_event("startup")
def startup() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        # Health and static pages work without Postgres (unit tests, docs).
        pass


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def user_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "user_home.html",
        {"studyforge_web_url": settings.studyforge_web_url},
    )


@app.get("/staff", response_class=HTMLResponse)
def staff_home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "staff_home.html",
        {"studyforge_web_url": settings.studyforge_web_url},
    )
