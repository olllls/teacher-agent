import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.config import settings
from backend.database import init_db
from backend.router import export, system as system_router, upload, evaluate


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)
    await init_db()

    from backend.router.system import cleanup_expired_files

    # Layer 2: daily cleanup at 3:00 AM
    scheduler.add_job(
        cleanup_expired_files,
        CronTrigger(hour=3, minute=0),
        id="cleanup_uploads",
        replace_existing=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

scheduler = AsyncIOScheduler()

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.include_router(upload.router)
app.include_router(evaluate.router)
app.include_router(export.router)
app.include_router(system_router.router)

templates = Jinja2Templates(directory="frontend/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/generate/{class_id}", response_class=HTMLResponse)
async def generate_page(request: Request, class_id: int):
    return templates.TemplateResponse("generate.html", {"request": request, "class_id": class_id})


@app.get("/api/health")
async def health():
    return {"status": "ok"}
