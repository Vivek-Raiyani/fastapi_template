# Phase 8 — Google OAuth

Social login via Google — optional, enabled when credentials are set in `.env`.

## Files

| File | Purpose |
|------|---------|
| `core/oauth/google.py` | Authlib OAuth client registration |
| `modules/auth/service.py` | `google_login_or_register()` |
| `modules/auth/router.py` | `/auth/google/login` + callback routes |
| `modules/auth/template/partials/login_form.html` | "Continue with Google" button |

## Setup

### 1. Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials (Web application)
3. Add authorized redirect URI: `http://127.0.0.1:8000/auth/google/callback`
4. Copy Client ID and Client Secret

### 2. Environment

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
```

When both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set, `settings.google_oauth_enabled` is `True`.

## Routes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/auth/google/login` | Redirect to Google consent screen |
| `GET` | `/auth/google/callback` | Handle OAuth callback, set cookie, redirect to profile |

If OAuth is not configured, these routes redirect to login with an error message.

## User linking logic

`AuthService.google_login_or_register()`:

1. Look up user by `google_id` → if found, log in
2. Else look up by `email` → if found, attach `google_id` to existing account
3. Else create new user (no password, OAuth-only)
4. Issue JWT and set `access_token` cookie

## UI

When Google OAuth is enabled, the login page shows:

```
[ Login form ]

        or

[ Continue with Google ]
```

Button links to `/auth/google/login`.

## Session middleware

Google OAuth requires `SessionMiddleware` (for OAuth state/csrf). Configured in `main.py`:

```python
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
```

## Database

User model field: `google_id` (unique, nullable) — added in initial migration `001`.

OAuth-only users have `hashed_password = NULL` and `google_id` set.

## Status

✅ Complete — Google login flow, account linking, cookie auth, conditional UI.
