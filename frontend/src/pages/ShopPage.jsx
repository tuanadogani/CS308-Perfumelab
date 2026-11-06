import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import { getProducts, getCategories, getFilters } from '../api/productApi';

// Requirements 1 & 7: categories, search (name/description), sort by price/popularity, brand & note filters
export default function ShopPage() {
  const [params, setParams] = useSearchParams(); // filters live in the URL → shareable links, back button works
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [options, setOptions] = useState({ brands: [], families: [] });
  const [brandPool, setBrandPool] = useState([]); // products matching every filter except brand
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState(params.get('q') ?? '');

  const filters = useMemo(() => ({
    q: params.get('q') ?? '',
    category: params.get('category') ?? '',
    brand: params.get('brand') ?? '',
    family: params.getAll('family'),
    sort: params.get('sort') ?? 'popularity',
  }), [params]);

  const setFilter = (key, value) => {
    const next = new URLSearchParams(params);
    value ? next.set(key, value) : next.delete(key);
    setParams(next, { replace: true });
  };

  // Toggle one scent family; products must match every selected family
  const toggleFamily = (family) => {
    const next = new URLSearchParams(params);
    const selected = filters.family.includes(family)
      ? filters.family.filter((f) => f !== family)
      : [...filters.family, family];
    next.delete('family');
    selected.forEach((f) => next.append('family', f));
    setParams(next, { replace: true });
  };

  useEffect(() => { getCategories().then(setCategories); }, []);
  useEffect(() => { getFilters().then(setOptions).catch(() => {}); }, []); // sidebar still works without them

  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError('');
    getProducts(filters)
      .then((list) => { if (!cancelled) setProducts(list); })
      .catch((e) => { if (!cancelled) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filters]);

  // While a brand is selected, the product list only holds that brand. To still offer the
  // other brands that match the remaining filters, load the list without the brand filter.
  const familyKey = filters.family.join('|');
  useEffect(() => {
    if (!filters.brand) return undefined;
    let cancelled = false;
    getProducts({ q: filters.q, category: filters.category, family: filters.family })
      .then((list) => { if (!cancelled) setBrandPool(list); })
      .catch(() => { if (!cancelled) setBrandPool([]); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.brand, filters.q, filters.category, familyKey]);

  // Search box: 300 ms debounce so we don't send a request on every keystroke
  useEffect(() => {
    const t = setTimeout(() => { if (search !== filters.q) setFilter('q', search); }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  // Only offer options that still return results. Selected options always stay visible
  // so they can be cleared.
  const brands = useMemo(() => {
    const present = new Set((filters.brand ? brandPool : products).map((p) => p.brand));
    return options.brands.map((b) => b.name).filter((b) => present.has(b) || b === filters.brand);
  }, [options.brands, products, brandPool, filters.brand]);
  // Selected families are combined with AND, so a family is available when at least
  // one listed product has it.
  const families = useMemo(() => {
    const present = new Set(products.flatMap((p) => p.families ?? []));
    return options.families.map((f) => f.name)
      .filter((f) => present.has(f) || filters.family.includes(f));
  }, [options.families, products, filters.family]);
  const hasFilters = filters.q || filters.category || filters.brand || filters.family.length > 0;

  return (
    <div className="container shop">
      <header className="shop__head">
        <div>
          <p className="eyebrow">Collection</p>
          <h1>All Fragrances</h1>
        </div>
        <input
          className="search" type="search" placeholder="Search by name, brand or description…"
          value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search products"
        />
      </header>

      <div className="shop__layout">
        <aside className="filters">
          <h4>Category</h4>
          <button className={`chip ${!filters.category ? 'active' : ''}`} onClick={() => setFilter('category', '')}>All</button>
          {categories.map((c) => (
            <button key={c.id} className={`chip ${filters.category === c.id ? 'active' : ''}`}
              onClick={() => setFilter('category', c.id)}>{c.name}</button>
          ))}

          <h4>Brand</h4>
          <select value={filters.brand} onChange={(e) => setFilter('brand', e.target.value)}>
            <option value="">All brands</option>
            {brands.map((b) => <option key={b}>{b}</option>)}
          </select>

          <h4>Scent Family</h4>
          <div className="chips">
            {families.map((f) => (
              <button key={f} className={`chip ${filters.family.includes(f) ? 'active' : ''}`}
                aria-pressed={filters.family.includes(f)} onClick={() => toggleFamily(f)}>{f}</button>
            ))}
          </div>

          {hasFilters && (
            <button className="link-btn" onClick={() => { setSearch(''); setParams({ sort: filters.sort }); }}>
              Clear filters
            </button>
          )}
        </aside>

        <section>
          <div className="shop__toolbar">
            <span className="muted">{loading ? 'Loading…' : `${products.length} products`}</span>
            <select value={filters.sort} onChange={(e) => setFilter('sort', e.target.value)} aria-label="Sort by">
              <option value="popularity">Most popular</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
          </div>

          {error && <p className="form-error">{error}</p>}
          {!loading && !error && products.length === 0 && (
            <div className="empty">No products match your search.</div>
          )}
          <div className="grid">
            {products.map((p) => <ProductCard key={p.id} product={p} />)}
          </div>
        </section>
      </div>
    </div>
  );
}
