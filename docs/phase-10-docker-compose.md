# Phase 10 — Docker Compose

Local infrastructure for PostgreSQL, Redis, and MinIO (S3-compatible storage).

## File

`docker-compose.yml`

## Services

| Service | Image | Port(s) | Purpose |
|---------|-------|---------|---------|
| **postgres** | `postgres:16-alpine` | `5432` | Production-like database |
| **redis** | `redis:7-alpine` | `6379` | Celery + ARQ broker |
| **minio** | `minio/minio` | `9000`, `9001` | S3-compatible object storage |
| **minio-init** | `minio/mc` | — | Creates `app-media` bucket on startup |

## Quick start

```bash
docker compose up -d
```

Verify:
```bash
docker compose ps
```

## Credentials (defaults)

| Service | User | Password | Database/Bucket |
|---------|------|----------|-----------------|
| Postgres | `postgres` | `postgres` | `app_db` |
| MinIO | `minioadmin` | `minioadmin` | `app-media` |
| Redis | — | — | DB `0` |

## Connect the app

Update `.env`:

```env
# PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/app_db

# S3 storage (MinIO)
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=app-media
S3_REGION=us-east-1
S3_PUBLIC_URL=http://127.0.0.1:9000/app-media

# Background tasks (Celery or ARQ)
TASK_BACKEND=celery
REDIS_URL=redis://localhost:6379/0
```

Then:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## MinIO console

Web UI: http://127.0.0.1:9001

Login: `minioadmin` / `minioadmin`

The `minio-init` service automatically:
1. Creates the `app-media` bucket
2. Sets it to public download (for dev)

## Full dev stack

Three terminals:

```bash
# Terminal 1 — infrastructure
docker compose up -d

# Terminal 2 — web app
python manage.py migrate
python manage.py runserver

# Terminal 3 — background worker (optional)
python manage.py runworker -b celery
# + another terminal for Beat:
python manage.py runworker -b celery --beat
```

## Volumes

Data persists across restarts in Docker volumes:

- `postgres_data` — database files
- `minio_data` — uploaded objects

Reset everything:
```bash
docker compose down -v
```

## Production notes

This Compose file is for **local development**. For production:

- Use managed Postgres (RDS, Cloud SQL, etc.)
- Use real AWS S3 or managed object storage
- Use managed Redis (ElastiCache, etc.)
- Change all default passwords
- Do not expose MinIO console publicly

## Status

✅ Complete — Postgres, Redis, MinIO with auto bucket init.
