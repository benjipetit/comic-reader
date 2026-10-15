import time

from app.config import get_settings

STATIC_NARRATION = (
    "Once upon a time, in a big old hotel at the edge of the forest, "
    "a little ghost woke up and decided to say hello to the new guests."
)


def narrate(s3_key: str) -> str:
    """Fake narration: pretends to compute, then returns a static script.

    The real implementation will fetch the image from S3 and call a vision model.
    """
    time.sleep(get_settings().fake_processing_seconds)
    return STATIC_NARRATION
