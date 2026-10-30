# PerfumeLab Backend

Django and PostgreSQL backend. Email login, token refresh, and user profile endpoints are available.

## Setup

Requires Python 3.13 and PostgreSQL 17. Run these commands from the `backend` folder.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
```

For a new local database on macOS with Homebrew:

```bash
brew services start postgresql@17
python scripts/setup_local_db.py
```

The script creates the database, application user, and `.env` file. To use an existing database, copy `.env.example` to `.env` and fill in the database credentials and `DJANGO_SECRET_KEY`. Keep `.env` out of Git.

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Use `createsuperuser` to create an admin account for testing. Registration is not available yet.

## Endpoints

Base URL: `http://127.0.0.1:8000`

- `GET /api/health/` — check the database connection.
- `POST /api/auth/login/` — log in and get access and refresh tokens.
- `POST /api/auth/refresh/` — get new tokens using a refresh token.
- `GET /api/auth/me/` — get the current user's profile.

Login request (JSON):

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

Send `Authorization: Bearer ACCESS_TOKEN` with requests to `me`. To refresh tokens, send `{"refresh": "REFRESH_TOKEN"}` and save the new refresh token from the response. Access tokens last 15 minutes; refresh tokens last one day.

Set frontend origins through `CORS_ALLOWED_ORIGINS` in `.env`. Defaults are `http://localhost:3000` and `http://localhost:5173`.

## Tests

Tests use a separate `test_perfume` database. Create it with a PostgreSQL admin account and set the application user as its owner, then run:

```bash
python manage.py test accounts --keepdb
```
