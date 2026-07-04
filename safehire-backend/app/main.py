import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.core.config import settings
from app.api.v1.endpoints import analyze, company, scan, score, chat
from app.db.init_db import init_models

# Set HuggingFace token so sentence-transformers downloads without rate limit warnings
if settings.HF_TOKEN:
    os.environ["HF_TOKEN"] = settings.HF_TOKEN
    os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.HF_TOKEN

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables automatically on startup
    await init_models()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for the OfferShield platform",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static folder for serving CSS, JS, and image assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Expose API endpoints
app.include_router(analyze.router, prefix="/api/v1/analyze", tags=["Analysis"])
app.include_router(company.router, prefix="/api/v1/company", tags=["Company"])
app.include_router(scan.router, prefix="/api/v1/scan", tags=["Scan"])
app.include_router(score.router, prefix="/api/v1/score", tags=["Score"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])

# Root Route: Serve the gorgeous Glassmorphic SPA Dashboard
@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/health")
def health_check():
    return {"status": "ok"}
