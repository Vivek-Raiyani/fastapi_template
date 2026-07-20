# Phase 12 — Email, Password Reset & Verification

## Features

- **Email backend:** `console` (dev) or `smtp` (production)
- **Email verification** on register (optional via `REQUIRE_EMAIL_VERIFICATION=true`)
- **Forgot / reset password** flow (API + HTML)

## Files

| File | Purpose |
|------|---------|
| `core/email.py` | `send_email()`, `send_template_email()` |
| `templates/emails/` | HTML email templates |
| `modules/auth/token_repository.py` | Secure tokens for verify/reset |
| `modules/auth/template/forgot_password.html` | Forgot password page |
| `modules/auth/template/reset_password.html` | Reset password form (CSRF protected) |

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/forgot-password` | Send reset email |
| `POST` | `/api/v1/auth/reset-password` | Reset with token |
| `POST` | `/api/v1/auth/verify-email` | Verify email with token |
| `GET` | `/auth/verify-email?token=...` | HTML verify link |

## HTML

- `/auth/forgot-password` — request reset link
- `/auth/reset-password?token=...` — set new password

## Configuration

```env
EMAIL_BACKEND=console
EMAIL_FROM=noreply@example.com
SMTP_HOST=localhost
SMTP_PORT=587
REQUIRE_EMAIL_VERIFICATION=false
```

## Status

✅ Complete
