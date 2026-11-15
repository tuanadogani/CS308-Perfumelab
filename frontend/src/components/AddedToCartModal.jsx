import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { getProducts } from '../api/productApi';
import { recommendProducts } from '../utils/recommendations';
import PerfumeBottle from './PerfumeBottle';
import PriceTag from './PriceTag';

export default function AddedToCartModal({ product, quantity, items, onClose }) {
  const dialog = useRef(null);
  const [catalog, setCatalog] = useState(null);

  useEffect(() => {
    let active = true;
    getProducts().then((products) => { if (active) setCatalog(products); })
      .catch(() => { if (active) setCatalog([]); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const element = dialog.current;
    const previousOverflow = document.body.style.overflow;
    element.showModal();
    document.body.style.overflow = 'hidden';
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const recommendations = catalog ? recommendProducts(product, catalog, items.map((item) => item.productId)) : [];

  return (
    <dialog ref={dialog} className="added-modal" aria-labelledby="added-modal-title" onCancel={onClose}
      onClick={(event) => { if (event.target === dialog.current) onClose(); }}>
      <div className="added-modal__content">
        <header className="added-modal__header">
          <h2 id="added-modal-title"><span aria-hidden="true">✓</span> Added to your cart</h2>
          <button type="button" className="cart-notice__close" aria-label="Close" onClick={onClose} autoFocus>×</button>
        </header>
        <div className="added-modal__product">
          <PerfumeBottle color={product.color} variant={product.id} size={100} alt={product.name} imageUrl={product.imageUrl} />
          <div><p className="eyebrow">{product.brand}</p><h3>{product.name}</h3><p className="muted small">{product.volumeMl} ml · Quantity: {quantity}</p></div>
          <PriceTag product={product} />
        </div>
        <div className="added-modal__actions">
          <button type="button" className="btn btn-dark" onClick={onClose}>Continue shopping</button>
          <Link className="btn btn-outline" to="/cart" onClick={onClose}>View cart →</Link>
        </div>
        {catalog === null && <p className="muted" role="status">Finding fragrances for you…</p>}
        {recommendations.length > 0 && <section aria-labelledby="recommendations-title">
          <h2 id="recommendations-title">You may also like</h2>
          <div className="added-modal__recommendations">
            {recommendations.map((candidate) => (
              <Link key={candidate.id} className="added-modal__recommendation" to={`/shop/${candidate.id}`} onClick={onClose}>
                <div className="added-modal__media"><PerfumeBottle color={candidate.color} variant={candidate.id} size={150} alt={candidate.name} imageUrl={candidate.imageUrl} /></div>
                <p className="eyebrow">{candidate.brand}</p><h3>{candidate.name}</h3>
                <p className="muted small">{candidate.volumeMl} ml</p><PriceTag product={candidate} />
              </Link>
            ))}
          </div>
        </section>}
      </div>
    </dialog>
  );
}
