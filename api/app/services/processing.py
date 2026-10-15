import logging
import uuid

from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.models import Comic, ComicStatus, Segment
from app.services.narration import narrate

logger = logging.getLogger(__name__)


def process_comic(comic_id: uuid.UUID, session_factory: sessionmaker[Session]) -> None:
    """Background job: narrate the comic and record the outcome."""
    with session_factory() as session:
        comic = session.get(Comic, comic_id)
        if comic is None:
            return
        try:
            segment = Segment(text=narrate(comic.s3_key))
            session.add(segment)
            session.flush()
            comic.segment_id = segment.id
            comic.status = ComicStatus.SUCCEEDED
        except Exception as exc:  # noqa: BLE001 - any failure must end in a terminal status
            logger.exception("Processing failed for comic %s", comic_id)
            session.rollback()
            comic = session.get(Comic, comic_id)
            comic.status = ComicStatus.FAILED
            comic.error = str(exc)[:500]
        session.commit()


def fail_orphaned_comics(session_factory: sessionmaker[Session]) -> int:
    """Jobs run in-process, so any row still in progress at startup was interrupted."""
    with session_factory() as session:
        result = session.execute(
            update(Comic)
            .where(Comic.status == ComicStatus.IN_PROGRESS)
            .values(status=ComicStatus.FAILED, error="Interrupted by server restart")
        )
        session.commit()
        return result.rowcount
