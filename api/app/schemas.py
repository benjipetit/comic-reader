import uuid

from pydantic import BaseModel, ConfigDict

from app.models import ComicStatus


class SegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str


class ComicOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ComicStatus
    segment: SegmentOut | None = None
    error: str | None = None
