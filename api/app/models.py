import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ComicStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    SUCCEEDED = "succeeded"


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Comic(Base):
    __tablename__ = "comics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    s3_key: Mapped[str] = mapped_column(String(512))
    status: Mapped[ComicStatus] = mapped_column(
        Enum(ComicStatus, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e]),
        default=ComicStatus.IN_PROGRESS,
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("segments.id"), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    segment: Mapped[Segment | None] = relationship(lazy="joined")
