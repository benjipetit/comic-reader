from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.db as db
from app.routers import comics
from app.services.processing import fail_orphaned_comics


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    fail_orphaned_comics(db.SessionLocal)
    yield


app = FastAPI(title="Comic Reader API", lifespan=lifespan)
app.include_router(comics.router)


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}
