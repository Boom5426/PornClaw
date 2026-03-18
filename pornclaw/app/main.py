from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.db import Base, engine, ensure_runtime_schema
import app.models  # noqa: F401
from app.routes import feedback, pages, profile, recommend, source


Base.metadata.create_all(bind=engine)
ensure_runtime_schema()

app = FastAPI(title="PornClaw")

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(pages.router)
app.include_router(source.router)
app.include_router(profile.router)
app.include_router(feedback.router)
app.include_router(recommend.router)


@app.get("/demo-source", response_class=HTMLResponse)
def demo_source() -> HTMLResponse:
    return HTMLResponse(
        """
        <html><body><h1>PornClaw Demo Source</h1>
        <p>Use <code>demo://seed</code> for the built-in parser path, or inspect the adapter HTML structure in code.</p>
        </body></html>
        """
    )
