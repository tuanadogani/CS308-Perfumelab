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
- `GET /api/products/` — public catalog; supports `q, category, brand, family, sort`. Repeat `family` to require several scent families (AND).
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

Customer cart/checkout, payments, refunds and review submission still need HTTP API
and frontend integration. The frontend cart uses localStorage, checkout shows a placeholder,
and admin screens are skeletons. Product manager backend APIs are available (see below).
Payments currently use a mock bank.

## Wishlist

- `GET /api/wishlist/` — current user's saved products (catalog product schema).
- `PUT /api/wishlist/<product_id>/` — save an active product, including sold-out products; repeated requests are safe.
- `DELETE /api/wishlist/<product_id>/` — remove the current user's favorite; repeated requests are safe.

All wishlist endpoints require Bearer authentication and only access the current user's entries.
The frontend shares wishlist state between product cards, product details and `/wishlist`.
Signed-in users save to PostgreSQL; guests and mock accounts save locally in separate browser storage keys.
Guest favorites remain separate from account favorites; automatic merging is not implemented.

## Product manager

The product manager implementation is backend only; frontend integration is handled separately.
All routes below require a `product_manager` account Bearer token and reject other roles.

Base path: `/api/product-manager/`

- `GET, POST products/` — list all products (including inactive) or create a product.
- `GET, PATCH, DELETE products/<id>/` — edit, update stock, or remove from the public catalog. DELETE soft deletes; PATCH `{ "active": true }` restores the product.
- `GET, POST categories/` and `GET, PATCH, DELETE categories/<id>/` — manage categories. A category referenced by any product cannot be deleted.
- `GET deliveries/` — delivery ID, order/customer/product IDs, quantity, line total, address, status and completion flag. Cancelled/refunded orders are excluded.
- `PATCH orders/<id>/status/` with `{ "status": "in_transit" }` or `{ "status": "delivered" }` — advance exactly one step. The entire order advances together; delivery completion and delivered timestamp update on delivery.
- `GET comments/` — pending and previously moderated comments.
- `PATCH comments/<id>/` with `{ "approve": true }` or `{ "approve": false }` — approve/reject and record reviewer/time. Ratings are unaffected.

Product writes use model field names: `name`, `model`, `serial_number`, `description`,
`stock`, `warranty_status`, `distributor`, `brand` (name), `category` (slug),
`gender`, `volume_ml`, optional `families` (name array), `notes`
(`{ "top": [], "heart": [], "base": [] }`), and `active`.
Responses use the public catalog's camelCase schema plus `active`.
New products start at price/base price 0; pricing and discounts belong to the sales manager.
Existing prices are preserved during product manager updates. No database migration is needed.

Run regression tests with `python manage.py test catalog orders reviews`.
