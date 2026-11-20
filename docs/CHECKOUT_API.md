# Cart + Checkout API (req 4)

All endpoints need a customer JWT (`Authorization: Bearer <access>`).
Staff roles get 403, no login gets 401. Errors look like `{"message": "..."}`.

## Cart

The cart object returned by every cart endpoint:

```json
{
  "items": [
    {"productId": 7, "name": "Sauvage", "brand": "Dior", "volumeMl": 100,
     "unitPrice": "5200.00", "quantity": 2, "stock": 14, "lineTotal": "10400.00",
     "imageUrl": "http://127.0.0.1:8000/api/products/7/image/?v=..."}
  ],
  "itemCount": 2,
  "total": "10400.00"
}
```

| Method | URL | Body | Notes |
|---|---|---|---|
| GET | `/api/cart/` | - | current cart |
| POST | `/api/cart/items/` | `{"productId": 7, "quantity": 1}` | adds; capped at stock; 400 if out of stock; 201 |
| PATCH | `/api/cart/items/<productId>/` | `{"quantity": 3}` | sets exact amount, 0 removes |
| DELETE | `/api/cart/items/<productId>/` | - | removes the line |
| DELETE | `/api/cart/` | - | empties the cart |
| POST | `/api/cart/merge/` | `{"items": [{"productId": 7, "quantity": 2}]}` | call ONCE right after login with the localStorage cart, then clear localStorage. Response also has `"skipped": [ids]` (sold out / unknown) |

Guests keep using localStorage (no API) until they log in.

## Checkout

`GET /api/cards/` -> saved cards (never the number):
`[{"id": 1, "brand": "", "last4": "4242", "holderName": "Ada", "expiryMonth": 12, "expiryYear": 2030}]`

`POST /api/checkout/`

```json
{"cardNumber": "4242 4242 4242 4242", "holderName": "Ada Lovelace",
 "expiryMonth": 12, "expiryYear": 2030, "cvv": "123",
 "shippingAddress": "optional - defaults to the profile home address"}
```

| Status | Meaning | What the page should do |
|---|---|---|
| 201 | paid, order placed, invoice emailed | show the invoice screen (below), refresh cart (now empty) |
| 400 | empty cart, not enough stock, no address, bad card fields (field errors come as `{"cvv": ["..."]}`) | show the message, cart unchanged |
| 402 | bank declined the card | show "card declined", cart unchanged |

Demo: any card ending in **0002** is declined by the mock bank.

201 response:

```json
{"order": {"id": 12, "status": "processing", "total": "10400.00", "items": [...], ...},
 "invoice": {"number": "INV-0000012", "total": "10400.00", "issuedAt": "..."},
 "transactionId": "TXN-...", "cardLast4": "4242"}
```

## Invoice screen

- `GET /api/orders/<orderId>/invoice/` -> `number, issuedAt, total, orderId, customerName,
  customerEmail, shippingAddress, cardLast4, items[{name, brand, volumeMl, quantity,
  unitPrice, lineTotal}], pdfUrl`
- `GET /api/orders/<orderId>/invoice/pdf/` -> the PDF (same one that was emailed).
  Add `?download=1` to save instead of open. It needs the JWT header, so fetch it as a blob
  and open `URL.createObjectURL(blob)` rather than a plain `<a href>`.
- Another customer's order -> 404.
