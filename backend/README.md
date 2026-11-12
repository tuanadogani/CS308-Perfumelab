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

Customer cart/checkout, payments and review submission still need HTTP API
and frontend integration. Customer order history, cancellation and refund request APIs
are available along with sales-manager return review APIs (see below); their frontend
integration is pending. The frontend cart uses localStorage and checkout shows a placeholder.
Product manager backend APIs are available (see below). Payments currently use a mock bank.

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

## Customer orders and refund requests

These routes require a customer account Bearer token. Other roles receive 403;
orders and items belonging to another customer receive 404.

- `GET /api/orders/` — current customer's orders, newest first, with purchased items and their refund status.
- `GET /api/orders/<id>/` — one owned order, its delivery status and purchase-time prices.
- `POST /api/orders/<id>/cancel/` — cancel only a `processing` order and restore its stock once.
- `POST /api/orders/<id>/items/<item_id>/refund/` — request a return for one purchased order line; optional JSON `{ "reason": "Not my scent" }` (maximum 2000 characters).

Refund requests require a `delivered` order and must be made within 30 days of
`createdAt` (purchase time, not delivery time). Exactly 30 days is accepted.
Each order line can have one request; all units on that line are returned together.
The amount is calculated from the stored `unit_price × quantity`, including any
purchase-time discount. Client-supplied amounts/statuses cannot override it.
Creating a request does not refund money, restock products or cancel the order.
Invalid lifecycle actions and duplicate requests return 400.

Order responses use camelCase keys (`shippingAddress`, `createdAt`, `deliveredAt`,
`productId`, `productName`, `unitPrice`, `lineTotal`). Monetary values in these
customer routes are decimal strings. Each item has `refund: null` or a refund
object containing `id`, `orderItemId`, `reason`, `status`, `amount`, `requestedAt`,
`receivedAt`, `decidedAt` and `paymentRefund`. Internal product cost is excluded.

These APIs operate on existing orders. Customer cart/checkout HTTP integration is
still pending. Refund processing uses the mock bank described below.

Run `python manage.py test orders refunds payments --keepdb` for regression coverage.

## Sales manager return review

Apply the receipt migration with `python manage.py migrate` before using these APIs.
All routes require a `sales_manager` Bearer token (401 when unauthenticated, 403 for
other roles, 404 for an unknown refund ID).

- `GET /api/sales/refunds/` — all requests, newest first; optional `?status=requested`, `approved` or `rejected`. Invalid status filters return 400.
- `GET /api/sales/refunds/<id>/` — one request, customer/order/product details, purchased quantity and price, receipt and decision records.
- `POST /api/sales/refunds/<id>/receive/` — record that the physical return arrived at the store. No body is required. Repeating receipt while the request is pending preserves the original receiver and timestamp.
- `POST /api/sales/refunds/<id>/decision/` — JSON `{ "approve": true }` or `{ "approve": false }`. Approval requires a receipt record and a currently delivered order. Rejection does not require receipt.

Responses include the customer refund fields plus `orderId`, `customerId`,
`customerName`, `customerEmail`, `productId`, `productName`, `quantity`, `unitPrice`,
`receivedBy` and `decidedBy`. Monetary values are decimal strings. Receipt and
decision timestamps and manager IDs are assigned by the server.

Receipt does not change stock, payment or order status. Approval restores only the
selected line's quantity; the order becomes `refunded` once all its lines are
approved. Rejected requests keep stock and order status unchanged. Decided requests
cannot be received or decided again (400). The 30-day eligibility window applies
when the customer requests the return, so a timely request can be decided later.

## Refund payments (mock bank)

Apply `payments/0003_payment_refund` with `python manage.py migrate`.
Approval now requires a `Payment` for the order (created by `payments.services.checkout`).
Orders created directly with `place_order` have no payment and cannot be approved
for a refund (400); they can still be rejected. No payment records are invented
for legacy orders or earlier approvals.

The bank refund references the original payment transaction, so the saved card
may be deleted without preventing a refund. No card number is needed. The amount
comes from the request's frozen purchase-time price, and cumulative refunds cannot
exceed the original payment. A zero-price purchase produces a zero-amount confirmation.
Each request has one protected `PaymentRefund` with its original payment, amount,
unique bank reference and timestamp. Repeated decisions are rejected before a
second bank call; concurrent approvals are serialized.

The existing decision endpoint returns 502 when the mock bank raises `RefundDeclined`.
The request stays pending with no stock, order status or refund-record change, and
the manager can retry. A stable key based on the refund request ID is used on each
bank attempt. The mock deterministically returns the same confirmation on retry,
including after a local database rollback. This simulates an idempotent provider;
it does not transfer money or maintain a real banking ledger. A real provider must
implement durable idempotency and reconciliation across bank/database failures.

Customer and manager refund responses include `paymentRefund: null` before payment
or an object such as:

```json
{
  "amount": "700.00",
  "transactionId": "RFND-EXAMPLE",
  "refundedAt": "2026-11-12T22:00:00+03:00"
}
```

Existing approval email is scheduled after commit; email errors cannot undo the
refund. Application notifications and further notification handling are subsequent work.
