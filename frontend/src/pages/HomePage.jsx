import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PerfumeBottle from '../components/PerfumeBottle';
import ProductCard from '../components/ProductCard';
import { getProducts } from '../api/productApi';
import { useAuth } from '../context/AuthContext';

export default function HomePage() {
  const { isAuthenticated } = useAuth();
  const [featured, setFeatured] = useState([]);

  useEffect(() => {
    getProducts({ sort: 'popularity' }).then((list) => setFeatured(list.slice(0, 4)));
  }, []);

  return (
    <>
      {/* HERO: the two most popular perfumes (drawn bottles until the list has loaded) */}
      <section className="hero">
        <div className="container hero__inner">
          <div className="hero__text">
            <p className="eyebrow">Niche Fragrance House · Est. 2026</p>
            <h1>One scent,<br /><em>a thousand memories.</em></h1>
            <p className="lead">
              Niche fragrances curated from around the world. Explore by notes
              and find the signature that is truly yours.
            </p>
            <div className="hero__cta">
              <Link to="/shop" className="btn btn-gold">Explore the Collection</Link>
              {!isAuthenticated && <Link to="/start" className="btn btn-ghost">Get Started</Link>}
            </div>
          </div>
          <div className="hero__visual" aria-hidden="true">
            <div className="hero__halo" />
            <div className="hero__bottle hero__bottle--back"><PerfumeBottle color="#8b97a5" collar="#c9ced4" variant={2} size={260} imageUrl={featured[1]?.imageUrl} /></div>
            <div className="hero__bottle hero__bottle--front"><PerfumeBottle color="#2b3138" collar="#c9ced4" variant={0} size={330} imageUrl={featured[0]?.imageUrl} /></div>
          </div>
        </div>
      </section>

      {/* VALUES */}
      <section className="values container">
        {[
          ['Authenticity Guaranteed', 'Every product comes from authorized distributors with a warranty.'],
          ['Note Guide', 'Find your scent by its top, heart and base notes.'],
          ['Careful Packaging', 'Every bottle is prepared with care in its signature box.'],
        ].map(([t, d]) => (
          <div key={t} className="value">
            <h3>{t}</h3>
            <p className="muted">{d}</p>
          </div>
        ))}
      </section>

      {/* FEATURED */}
      <section className="container section">
        <div className="section__head">
          <h2>Most Loved</h2>
          <Link to="/shop" className="link-arrow">View all →</Link>
        </div>
        <div className="grid">
          {featured.map((p) => <ProductCard key={p.id} product={p} />)}
        </div>
      </section>

      {/* GET STARTED BAND */}
      {!isAuthenticated && (
        <section className="cta-band">
          <div className="container cta-band__inner">
            <h2>Ready to find your signature scent?</h2>
            <div className="hero__cta">
              <Link to="/register" className="btn btn-gold">Sign Up</Link>
              <Link to="/login" className="btn btn-ghost-light">I already have an account</Link>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
