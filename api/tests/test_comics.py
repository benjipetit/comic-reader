import uuid

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def upload(client, data=PNG, content_type="image/png"):
    return client.post("/comics", files={"file": ("page.png", data, content_type)})


def test_upload_returns_202_and_job_completes(client, storage):
    r = upload(client)
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "in_progress"
    assert r.headers["location"] == f"/comics/{body['id']}"
    assert len(storage.objects) == 1

    # TestClient runs background tasks before returning, with a 0s fake delay.
    done = client.get(f"/comics/{body['id']}")
    assert done.status_code == 200
    assert done.json()["status"] == "succeeded"
    assert done.json()["segment"]["text"]


def test_unknown_comic_is_404(client):
    assert client.get(f"/comics/{uuid.uuid4()}").status_code == 404


def test_rejects_unsupported_type(client):
    assert upload(client, b"hello", "text/plain").status_code == 415


def test_rejects_mismatched_content(client):
    assert upload(client, b"not a png", "image/png").status_code == 415


def test_rejects_oversized(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_upload_bytes", 10)
    assert upload(client).status_code == 413


def test_events_stream_ends_with_final_status(client):
    comic_id = upload(client).json()["id"]
    with client.stream("GET", f"/comics/{comic_id}/events") as r:
        text = "".join(r.iter_text())
    assert "event: status" in text and '"succeeded"' in text
