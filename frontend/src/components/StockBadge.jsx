// Requirement 3: stock is shown only when it matters to the shopper — low stock or sold out.
export const LOW_STOCK_LIMIT = 5;

export default function StockBadge({ stock }) {
  if (stock <= 0) return <span className="badge badge-out">Sold out</span>;
  if (stock <= LOW_STOCK_LIMIT) return <span className="badge badge-low">Only {stock} left</span>;
  return null;
}
