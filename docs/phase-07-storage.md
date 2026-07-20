# Phase 7 — Storage (Local + S3-Compatible)

Unified file storage — switch between local filesystem and S3-compatible backends via config. Equivalent to Django's storage backends.

## Files

| File | Purpose |
|------|---------|
| `storage/base.py` | `StorageBackend` protocol |
| `storage/local.py` | Filesystem storage (`media/`) |
| `storage/s3.py` | S3-compatible (AWS, MinIO, Cloudflare R2) |
| `storage/factory.py` | `get_storage()` — returns backend from settings |
| `modules/storage/router.py` | Upload API endpoint |

## Configuration

### Local (default)

```env
STORAGE_BACKEND=local
```

- Files saved to `media/`
- Served at `/media/` when `SERVE_HTML=true`
- No extra services required

### S3-compatible

```env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://127.0.0.1:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=app-media
S3_REGION=us-east-1
S3_PUBLIC_URL=http://127.0.0.1:9000/app-media
```

Works with AWS S3, MinIO, Cloudflare R2, DigitalOcean Spaces, etc.

## Usage in code

```python
from storage import get_storage

storage = get_storage()

# Save
url = await storage.save("uploads/photo.jpg", file_bytes, content_type="image/jpeg")

# Get URL (signed for private buckets)
url = await storage.url("uploads/photo.jpg", expires=3600)

# Check existence
exists = await storage.exists("uploads/photo.jpg")

# Delete
await storage.delete("uploads/photo.jpg")
```

Upload code does **not** change when switching backends — only `.env` changes.

## Upload API

```
POST /api/v1/storage/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

Form field: `file`

Response:
```json
{
  "key": "uploads/3/a1b2c3d4.jpg",
  "url": "/media/uploads/3/a1b2c3d4.jpg",
  "filename": "photo.jpg"
}
```

Files are stored under `uploads/{user_id}/{uuid}{ext}`.

## StorageBackend interface

All backends implement:

| Method | Returns | Description |
|--------|---------|-------------|
| `save(key, data, content_type)` | `str` (URL) | Store file |
| `delete(key)` | `None` | Remove file |
| `exists(key)` | `bool` | Check if file exists |
| `url(key, expires=3600)` | `str` | Access URL (presigned for private S3) |

## Static vs media

| Type | Location | Backend | Purpose |
|------|----------|---------|---------|
| **Static** | `statics/` | FastAPI `StaticFiles` | CSS, JS, images bundled with app |
| **Media** | `media/` or S3 | `storage/` abstraction | User uploads, dynamic files |

## Status

✅ Complete — local + S3 backends, factory, upload API.
