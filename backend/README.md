# PerfumeLab Backend

Django and PostgreSQL backend. Registration, email login, JWT refresh/logout, profiles, and the public product catalog are available.

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

For catalog data and one demo account per role (local development only):

```bash
python manage.py seed_products
python manage.py seed_demo_users
```

Demo emails: `customer@demo.com`, `sales@demo.com`, `product@demo.com`, `support@demo.com`; password: `Demo1234`.
New registrations always receive the `customer` role.

## Endpoints

Base URL: `http://127.0.0.1:8000`

- `GET /api/health/` — check the database connection.
- `POST /api/auth/register/` — register with `{name, email, password, taxId, homeAddress}`; returns `{user, access, refresh}`.
- `POST /api/auth/logout/` — blacklist `{refresh}`; requires an access token.
- `GET /api/products/` — public catalog; supports `q, category, brand, family, sort`.
- `GET /api/products/<id>/` — public product detail.
- `GET /api/categories/` — public categories.
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

## Frontend connection

In a second terminal, from `frontend`:

```bash
npm ci
cp .env.example .env
npm run dev
```

The default is `VITE_USE_MOCK=false`. Vite proxies `/api` to `http://localhost:8000`.
Keep the trailing slash on API routes, particularly POST requests. Login returns `{access, refresh}`;
the frontend then loads `/api/auth/me/` for `{id, name, email, role, taxId, homeAddress}`.
Tokens are stored in tab-scoped `sessionStorage`; refresh rotation updates both tokens and logout
blacklists the refresh token. An already-issued access token remains valid until its expiry.
For local integration, verify `/api/health/`, product browsing, registration, login, profile, and logout.

## Remaining integration work

Cart, orders, payments, refunds and reviews contain models/services and tests, but have
no HTTP API routes yet. The frontend cart still uses localStorage, checkout shows a placeholder,
and admin screens are skeletons. These features need authenticated API views, ownership/role
checks and frontend screens before they can be used end to end. Payments currently use a mock bank.

## Wishlist

- `GET /api/wishlist/` — current user's saved products (catalog product schema).
- `PUT /api/wishlist/<product_id>/` — save an active product, including sold-out products; repeated requests are safe.
- `DELETE /api/wishlist/<product_id>/` — remove the current user's favorite; repeated requests are safe.

All wishlist endpoints require Bearer authentication and only access the current user's entries.
The frontend shares wishlist state between product cards, product details and `/wishlist`.
Signed-in users save to PostgreSQL; guests and mock accounts save locally in separate browser storage keys.
Guest favorites remain separate from account favorites; automatic merging is not implemented.
