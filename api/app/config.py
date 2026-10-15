from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://comics:comics@localhost:5432/comics"

    # S3 (MinIO locally). Leave endpoint unset on AWS; credentials come from the
    # standard AWS_* environment variables / task role.
    s3_bucket: str = "comics"
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"

    max_upload_bytes: int = 10 * 1024 * 1024
    fake_processing_seconds: float = 5.0
    poll_retry_after_seconds: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
