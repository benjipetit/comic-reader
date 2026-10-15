from functools import lru_cache
from typing import Protocol

import boto3
from botocore.config import Config

from app.config import get_settings


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...


def _drop_expect_header(request, **_) -> None:
    request.headers.pop("Expect", None)


class S3Storage:
    """Stores uploads in S3 (MinIO locally, AWS S3 when deployed)."""

    def __init__(self, bucket: str, endpoint_url: str | None, region: str):
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            config=Config(s3={"addressing_style": "path"}),
        )
        if endpoint_url:
            # Local S3 fakes drop the connection on "Expect: 100-continue".
            self._client.meta.events.register("before-send.s3.PutObject", _drop_expect_header)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)


@lru_cache
def get_storage() -> Storage:
    s = get_settings()
    return S3Storage(s.s3_bucket, s.s3_endpoint_url, s.s3_region)
