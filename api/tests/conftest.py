import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["FAKE_PROCESSING_SECONDS"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.db as db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.storage import get_storage  # noqa: E402


class FakeStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key, data, content_type):
        self.objects[key] = data


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def client(storage):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    db.Base.metadata.create_all(engine)
    db.SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[db.get_session] = lambda: (yield from _session())
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _session():
    with db.SessionLocal() as s:
        yield s
