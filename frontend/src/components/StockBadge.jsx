// Requirement 3: the number of items in stock must be shown.
export default function StockBadge({ stock }) {
  if (stock <= 0) return <span className="badge badge-out">Sold out</span>;
  if (stock <= 5) return <span className="badge badge-low">Only {stock} left</span>;
  return <span className="badge badge-in">In stock: {stock}</span>;
}
