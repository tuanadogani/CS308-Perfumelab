export const formatPrice = (n) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'TRY', currencyDisplay: 'narrowSymbol', maximumFractionDigits: 0,
  }).format(n);
