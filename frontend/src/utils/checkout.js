// Pure helpers for the checkout form, kept out of React so they are easy to unit test.
// The backend checks everything again; these only give the user quick feedback.

export const cardDigits = (value) => String(value ?? '').replace(/\D/g, '');

/** "4242424242424242" -> "4242 4242 4242 4242" while typing (max 19 digits). */
export const formatCardNumber = (value) => cardDigits(value).slice(0, 19).replace(/(\d{4})(?=\d)/g, '$1 ');

/** "1230" or "12/30" -> "12/30" while typing. */
export function formatExpiry(value) {
  const d = cardDigits(value).slice(0, 4);
  return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
}

/** "12/30" -> { month: 12, year: 2030 }, or null if it is not a real month. */
export function parseExpiry(value) {
  const match = /^(\d{2})\/(\d{2})$/.exec(String(value ?? '').trim());
  if (!match) return null;
  const month = Number(match[1]);
  if (month < 1 || month > 12) return null;
  return { month, year: 2000 + Number(match[2]) };
}

/** Returns { field: message } for every problem; an empty object means the form is fine. */
export function validateCheckout(form, today = new Date()) {
  const errors = {};
  if (!form.holderName?.trim()) errors.holderName = 'Enter the name on the card.';
  const digits = cardDigits(form.cardNumber);
  if (digits.length < 13 || digits.length > 19) errors.cardNumber = 'Card number must have 13–19 digits.';
  const expiry = parseExpiry(form.expiry);
  if (!expiry) {
    errors.expiry = 'Use MM/YY.';
  } else if (expiry.year * 12 + expiry.month < today.getFullYear() * 12 + today.getMonth() + 1) {
    errors.expiry = 'This card has expired.';
  }
  if (!/^\d{3,4}$/.test(form.cvv ?? '')) errors.cvv = 'CVV is 3 or 4 digits.';
  if (!form.shippingAddress?.trim()) errors.shippingAddress = 'Enter a delivery address.';
  return errors;
}

/** The body for POST /api/checkout/. */
export function toCheckoutBody(form) {
  const { month, year } = parseExpiry(form.expiry);
  return {
    cardNumber: cardDigits(form.cardNumber),
    holderName: form.holderName.trim(),
    expiryMonth: month,
    expiryYear: year,
    cvv: form.cvv,
    shippingAddress: form.shippingAddress.trim(),
  };
}

/**
 * Compare the browser cart with what the server accepted (stock may have changed since
 * the product was added). Returns the lines whose quantity differs: [{productId, name, quantity}],
 * where quantity 0 means the product is no longer available.
 */
export function cartDifferences(localItems, serverCart) {
  const server = new Map((serverCart?.items ?? []).map((i) => [i.productId, i.quantity]));
  return localItems
    .filter((i) => (server.get(i.productId) ?? 0) !== i.quantity)
    .map((i) => ({ productId: i.productId, name: i.name, quantity: server.get(i.productId) ?? 0 }));
}
