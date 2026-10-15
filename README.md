# Comic Reader

This is a demo project of a service that reads comics for kids.

You take a picture of a comics page with the mobile app,
and after a few seconds the app narrates it.

## Repo structure

This is a monorepo, containing all the code necessary to run the service.

## Running locally

```sh
docker compose up --build
```

- API: <http://localhost:8000> (docs at `/docs`)
- Postgres: `localhost:5432` (user/password/db: `comics`)
- Fake S3 (adobe/s3mock): `localhost:9090`, bucket `comics`

```sh
# 202
curl -i \
  -F "file=@fixtures/photos/schtroumpfs-1-square-4.png;type=image/png" \
  localhost:8000/comics   # 202

# 200 / 404
curl -i localhost:8000/comics/<id>

# SSE Stream
curl -N localhost:8000/comics/<id>/events
```

Tests: `docker compose run --rm --no-deps api pytest`

The `api/Dockerfile` has a `dev` target (used by compose)
and a default `prod` target (non-root, runs migrations then uvicorn) for ECR + Fargate.
