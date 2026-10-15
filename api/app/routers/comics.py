import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import app.db as db
from app.config import Settings, get_settings
from app.db import get_session
from app.models import Comic, ComicStatus
from app.schemas import ComicOut
from app.services.processing import process_comic
from app.services.storage import Storage, get_storage

router = APIRouter(prefix="/comics", tags=["comics"])

ALLOWED_TYPES = {"image/png": "png", "image/jpeg": "jpg"}
MAGIC = {"image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff"}


@router.post("", status_code=202, response_model=ComicOut)
async def upload_comic(
    file: UploadFile,
    response: Response,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    storage: Storage = Depends(get_storage),
    settings: Settings = Depends(get_settings),
) -> Comic:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Only PNG and JPEG images are supported")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"Image exceeds {settings.max_upload_bytes} bytes")
    if not data.startswith(MAGIC[file.content_type]):
        raise HTTPException(415, "File content does not match its declared type")

    comic_id = uuid.uuid4()
    key = f"comics/{comic_id}.{ALLOWED_TYPES[file.content_type]}"
    await run_in_threadpool(storage.put, key, data, file.content_type)

    comic = Comic(id=comic_id, s3_key=key, status=ComicStatus.IN_PROGRESS)
    session.add(comic)
    session.commit()

    background_tasks.add_task(process_comic, comic_id, db.SessionLocal)
    response.headers["Location"] = f"/comics/{comic_id}"
    return comic


@router.get("/{comic_id}", response_model=ComicOut)
def get_comic(
    comic_id: uuid.UUID,
    response: Response,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Comic:
    comic = session.get(Comic, comic_id)
    if comic is None:
        raise HTTPException(404, "Comic not found")
    if comic.status == ComicStatus.IN_PROGRESS:
        response.headers["Retry-After"] = str(settings.poll_retry_after_seconds)
    return comic


def _load(comic_id: uuid.UUID) -> ComicOut | None:
    with db.SessionLocal() as session:
        comic = session.get(Comic, comic_id)
        return ComicOut.model_validate(comic) if comic else None


@router.get("/{comic_id}/events")
async def stream_comic(comic_id: uuid.UUID, request: Request) -> StreamingResponse:
    """Server-Sent Events alternative to polling: pushes each status change, then closes."""
    if await run_in_threadpool(_load, comic_id) is None:
        raise HTTPException(404, "Comic not found")

    async def events() -> AsyncIterator[str]:
        last = None
        while not await request.is_disconnected():
            comic = await run_in_threadpool(_load, comic_id)
            payload = comic.model_dump_json()
            if payload != last:
                last = payload
                yield f"event: status\ndata: {payload}\n\n"
            if comic.status != ComicStatus.IN_PROGRESS:
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
