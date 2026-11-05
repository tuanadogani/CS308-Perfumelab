# Maison Lumière — Frontend (CS 308, Sprint 1)

React 18 + Vite + React Router. Uses the Django backend by default. Optional mock mode is available with `VITE_USE_MOCK=true`.

## Getting started
```bash
npm install
cp .env.example .env      # VITE_USE_MOCK=false   (Windows: copy .env.example .env)
npm run dev               # http://localhost:5173
npm test                  # unit tests (vitest)
```

Demo accounts (mock mode, or after backend `seed_demo_users`; password `Demo1234`):
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

## Backend connection

Start Django on port 8000 with migrations and seed data applied (see `../backend/README.md`).
Set `VITE_USE_MOCK=false`; `/api` goes through Vite's proxy. API routes use trailing slashes.

| Method | Endpoint | Response |
|---|---|---|
| GET | `/products/` | `Product[]`; filters: `q, category, brand, family, sort` |
| GET | `/products/:id/` | `Product` |
| GET | `/categories/` | `{id, name}[]` |
| POST | `/auth/register/` | `{user, access, refresh}` |
| POST | `/auth/login/` | `{access, refresh}` |
| GET | `/auth/me/` | `{id, name, email, role, taxId, homeAddress}` |
| POST | `/auth/refresh/` | `{access, refresh}`; body `{refresh}` |
| POST | `/auth/logout/` | 204; body `{refresh}` and Bearer access token |

The auth adapter returns `{user, accessToken, refreshToken}` to React. Tokens live in
`sessionStorage` until the tab closes. The API client rotates tokens on a 401 and retries once.
A failed refresh clears the session. Backend validation messages are displayed by the forms.
New users always receive `customer`; staff roles must be assigned by the backend.
UI route protection does not replace backend authorization checks.

For production hosting, configure `/api` routing or `VITE_API_BASE_URL`; the Vite development
proxy is not included in the static build. For cross-origin hosting configure backend CORS origins.

## Open items for upcoming sprints
- Merge the guest cart with the backend cart on login (`POST /cart/merge`)
- Checkout, invoices, order history, comments/ratings, admin modules
- Real product photos: if a product has an `imageUrl`, `PerfumeBottle` renders an `<img>` automatically

## Wishlist

The heart controls in the catalog and product details share a WishlistProvider. Saved products
appear on `/wishlist` and can be removed there. Real signed-in accounts use authenticated
`GET /wishlist/`, `PUT /wishlist/:id/` and `DELETE /wishlist/:id/` requests. Guests and mock
accounts use separate localStorage keys; guest favorites do not automatically merge on login.
Loading and request failures are shown explicitly; failed updates do not change the saved state.
