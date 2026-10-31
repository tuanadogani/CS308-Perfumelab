# Maison Lumière — Frontend (CS 308, Sprint 1)

React 18 + Vite + React Router. Runs on **mock data** until the backend is ready.

## Getting started
```bash
npm install
cp .env.example .env      # VITE_USE_MOCK=true   (Windows: copy .env.example .env)
npm run dev               # http://localhost:5173
npm test                  # unit tests (vitest)
```

Demo accounts (mock mode, password `Demo1234`):
`customer@demo.com`, `sales@demo.com`, `product@demo.com`, `support@demo.com`

## Folder structure
```
src/
  api/          client.js (fetch + token), productApi.js, authApi.js  ← the ONLY place that talks to the backend
  mocks/        products.js (product data model + sample data)
  context/      AuthContext, CartContext, cartReducer (pure logic, unit tested)
  routes/       ProtectedRoute (login + role checks)
  constants/    roles.js (4 roles)
  components/   Navbar, Layout, ProductCard, StockBadge, PerfumeBottle
  pages/        Home, Start, Login, Register, Shop, ProductDetail, Cart, Profile, admin/
  styles/       global.css (colors defined in :root)
  utils/        format.js, validation.js
```

## Pages / flow
| Route | Page | Access |
|---|---|---|
| `/` | Home (hero, featured products, "Get Started") | Everyone |
| `/start` | Log in / Sign up / Continue as guest | Everyone |
| `/login`, `/register` | Authentication | Everyone |
| `/shop` | Catalog: search, category, brand, scent family, sorting | Everyone |
| `/shop/:id` | Product detail, notes, stock, required fields | Everyone |
| `/cart` | Cart (guests can use it; login required to check out) | Everyone |
| `/profile` | Name, email, address | Logged in |
| `/admin` | Role-specific admin modules (skeleton) | Staff roles |

## Contract with the backend team
Set `VITE_USE_MOCK=false` in `.env` and requests go to `/api` (Vite proxy → `localhost:8000`).

| Method | Endpoint | Body / Query | Returns |
|---|---|---|---|
| GET | `/products` | `q, category, brand, family, sort=price_asc\|price_desc\|popularity` | `Product[]` |
| GET | `/products/:id` | | `Product` |
| GET | `/categories` | | `{id, name}[]` |
| POST | `/auth/register` | `{name, email, password, taxId, homeAddress}` | `{user, accessToken}` |
| POST | `/auth/login` | `{email, password}` | `{user, accessToken}` |
| POST | `/auth/logout` | | |

`Product` schema: see the comment at the top of `src/mocks/products.js`.
`user.role` values: `customer | sales_manager | product_manager | support_agent`.
On errors the backend should return `{ message: "..." }` with an appropriate HTTP status code.

## Security notes (Requirement 17)
- The role cannot be chosen on the sign-up form; new users are always `customer`.
- `ProtectedRoute` only protects the UI — **the backend must check authorization on every request**.
- Password hashing happens on the backend (bcrypt/argon2). The frontend never stores passwords.
- Recommended: issue the refresh token as an httpOnly cookie and restore the session with `GET /auth/me`.
- Login errors show a generic message (they don't reveal which field was wrong).

## Open items for upcoming sprints
- Merge the guest cart with the backend cart on login (`POST /cart/merge`)
- Checkout, invoices, order history, wish list, comments/ratings, admin modules
- Real product photos: if a product has an `imageUrl`, `PerfumeBottle` renders an `<img>` automatically
