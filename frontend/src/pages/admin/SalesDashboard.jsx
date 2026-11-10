import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getRevenueReport, getInvoices, getInvoicePdf, setDiscount } from '../../api/salesApi';
import { getProducts, getCategories } from '../../api/productApi';

// Sales manager panel (Requirement 11): revenue / profit report, invoices, discounts.

const TABS = [
  ['revenue', 'Revenue Report'],
  ['invoices', 'Invoices'],
  ['discounts', 'Pricing & Discounts'],
  ['refunds', 'Refund Requests', 'Soon'],
];

const money = (n) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'TRY', currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(n ?? 0);
const moneyShort = (n) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'TRY', currencyDisplay: 'narrowSymbol',
    notation: 'compact', maximumFractionDigits: 1,
  }).format(n ?? 0);

const iso = (d) => {
  const pad = (x) => String(x).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};
const daysAgo = (n) => { const d = new Date(); d.setDate(d.getDate() - n); return iso(d); };
const parseIso = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
const fmtDay = (s, opts = { day: 'numeric', month: 'short' }) => parseIso(s).toLocaleDateString('en-GB', opts);
const fmtDateTime = (s) =>
  new Date(s).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

const PRESETS = [
  ['7 days', () => ({ startDate: daysAgo(6), endDate: iso(new Date()) })],
  ['30 days', () => ({ startDate: daysAgo(29), endDate: iso(new Date()) })],
  ['90 days', () => ({ startDate: daysAgo(89), endDate: iso(new Date()) })],
  ['This month', () => { const d = new Date(); return { startDate: iso(new Date(d.getFullYear(), d.getMonth(), 1)), endDate: iso(d) }; }],
  ['All time', () => ({ startDate: '', endDate: '' })],
];

const STATUS_LABELS = {
  processing: 'Processing', in_transit: 'In transit', delivered: 'Delivered',
  cancelled: 'Cancelled', refunded: 'Refunded',
};

export default function SalesDashboard() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = TABS.some(([k]) => k === params.get('tab')) ? params.get('tab') : 'revenue';
  // One date range shared by the report and the invoice list.
  const [range, setRange] = useState(PRESETS[1][1]);

  return (
    <div className="container section sales">
      <p className="eyebrow">Admin Panel · Sales Manager</p>
      <h1>Sales Dashboard</h1>
      <p className="muted">Hello {user.name.split(' ')[0]}, here is how the store is doing.</p>

      <nav className="tabs" role="tablist">
        {TABS.map(([key, label, tag]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            className={`tabs__tab${tab === key ? ' active' : ''}`}
            onClick={() => setParams({ tab: key }, { replace: true })}
          >
            {label}
            {tag && <span className="tabs__tag">{tag}</span>}
          </button>
        ))}
      </nav>

      {(tab === 'revenue' || tab === 'invoices') && <RangePicker range={range} onChange={setRange} />}
      {tab === 'revenue' && <RevenueTab range={range} />}
      {tab === 'invoices' && <InvoicesTab range={range} />}
      {tab === 'discounts' && <DiscountsTab />}
      {tab === 'refunds' && <RefundsTab />}
    </div>
  );
}

/* ---------- Date range ---------- */

function RangePicker({ range, onChange }) {
  const active = PRESETS.find(([, fn]) => {
    const r = fn();
    return r.startDate === range.startDate && r.endDate === range.endDate;
  })?.[0];
  return (
    <div className="range">
      <div className="chips range__chips">
        {PRESETS.map(([label, fn]) => (
          <button key={label} className={`chip${active === label ? ' active' : ''}`} onClick={() => onChange(fn())}>
            {label}
          </button>
        ))}
      </div>
      <div className="range__inputs">
        <label>
          From
          <input type="date" value={range.startDate} max={range.endDate || undefined}
            onChange={(e) => onChange({ ...range, startDate: e.target.value })} />
        </label>
        <label>
          To
          <input type="date" value={range.endDate} min={range.startDate || undefined}
            onChange={(e) => onChange({ ...range, endDate: e.target.value })} />
        </label>
      </div>
    </div>
  );
}

function useLoader(fn, deps) {
  const [state, setState] = useState({ loading: true, error: '', data: null });
  const reload = useCallback(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: '' }));
    fn()
      .then((data) => alive && setState({ loading: false, error: '', data }))
      .catch((e) => alive && setState({ loading: false, error: e.message, data: null }));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(reload, [reload]);
  return state;
}

/* ---------- Revenue ---------- */

function RevenueTab({ range }) {
  const { loading, error, data } = useLoader(() => getRevenueReport(range), [range.startDate, range.endDate]);

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <p className="muted">Loading report…</p>;

  const profitClass = data.isProfit ? 'is-profit' : 'is-loss';
  const busiest = data.chartData.reduce((best, d) => (d.revenue > (best?.revenue ?? 0) ? d : best), null);

  return (
    <div className={loading ? 'is-loading' : ''}>
      <div className="kpis">
        <div className="kpi">
          <span className="kpi__label">Revenue</span>
          <strong className="kpi__value">{money(data.totalRevenue)}</strong>
          <span className="muted small">{data.totalOrders} order{data.totalOrders === 1 ? '' : 's'}</span>
        </div>
        <div className="kpi">
          <span className="kpi__label">Product cost</span>
          <strong className="kpi__value">{money(data.totalCost)}</strong>
          <span className="muted small">Cost of goods sold</span>
        </div>
        <div className={`kpi ${profitClass}`}>
          <span className="kpi__label">{data.isProfit ? 'Profit' : 'Loss'}</span>
          <strong className="kpi__value">{money(data.profit)}</strong>
          <span className="small">{data.profitMargin.toFixed(1)}% margin</span>
        </div>
        <div className="kpi">
          <span className="kpi__label">Avg. order value</span>
          <strong className="kpi__value">{money(data.totalOrders ? data.totalRevenue / data.totalOrders : 0)}</strong>
          <span className="muted small">
            {busiest ? `Best day: ${fmtDay(busiest.date)}` : 'No sales yet'}
          </span>
        </div>
      </div>

      <div className="panel">
        <div className="panel__head">
          <h3>Revenue, cost &amp; profit</h3>
          <div className="legend">
            <span><i className="legend__swatch legend__swatch--revenue" />Revenue</span>
            <span><i className="legend__swatch legend__swatch--cost" />Cost</span>
            <span><i className="legend__swatch legend__swatch--profit" />Profit</span>
          </div>
        </div>
        {data.chartData.length === 0
          ? <div className="empty">No sales in this period.</div>
          : <RevenueChart points={data.chartData} />}
      </div>

      {data.chartData.some((d) => d.orderCount > 0) && (
        <details className="panel daily">
          <summary>Daily breakdown</summary>
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr><th>Date</th><th className="num">Orders</th><th className="num">Revenue</th><th className="num">Cost</th><th className="num">Profit</th></tr>
              </thead>
              <tbody>
                {[...data.chartData].reverse().filter((d) => d.orderCount > 0).map((d) => (
                  <tr key={d.date}>
                    <td>{fmtDay(d.date, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}</td>
                    <td className="num">{d.orderCount}</td>
                    <td className="num">{money(d.revenue)}</td>
                    <td className="num">{money(d.cost)}</td>
                    <td className={`num ${d.profit >= 0 ? 'is-profit' : 'is-loss'}`}>{money(d.profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}

function niceMax(v) {
  if (v <= 0) return 1;
  const exp = 10 ** Math.floor(Math.log10(v));
  const f = v / exp;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * exp;
}

function RevenueChart({ points }) {
  const wrapRef = useRef(null);
  const [width, setWidth] = useState(800);
  const [hover, setHover] = useState(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return undefined;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const height = 300;
  const pad = { top: 16, right: 12, bottom: 28, left: 56 };
  const w = width - pad.left - pad.right;
  const h = height - pad.top - pad.bottom;

  const maxVal = niceMax(Math.max(...points.map((p) => Math.max(p.revenue, p.cost))));
  const minVal = Math.min(0, ...points.map((p) => p.profit));
  const yMin = minVal < 0 ? -niceMax(-minVal) : 0;
  const y = (v) => pad.top + h - ((v - yMin) / (maxVal - yMin)) * h;
  const step = w / points.length;
  const x = (i) => pad.left + step * i + step / 2;
  const barW = Math.max(2, Math.min(28, step * 0.62));

  const ticks = Array.from({ length: 5 }, (_, i) => yMin + ((maxVal - yMin) * i) / 4);
  const labelEvery = Math.ceil(points.length / Math.max(2, Math.floor(w / 70)));
  const line = (key) => points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join(' ');

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const i = Math.floor((e.clientX - rect.left - pad.left) / step);
    setHover(i >= 0 && i < points.length ? i : null);
  };
  const hp = hover != null ? points[hover] : null;

  return (
    <div className="chart" ref={wrapRef}>
      <svg width={width} height={height} onMouseMove={onMove} onMouseLeave={() => setHover(null)} role="img"
        aria-label="Daily revenue, cost and profit chart">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.left} x2={width - pad.right} y1={y(t)} y2={y(t)} className={t === 0 ? 'chart__zero' : 'chart__grid'} />
            <text x={pad.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="chart__tick">{moneyShort(t)}</text>
          </g>
        ))}
        {hover != null && <rect x={x(hover) - step / 2} y={pad.top} width={step} height={h} className="chart__hover" />}
        {points.map((p, i) => (
          <g key={p.date}>
            <rect x={x(i) - barW / 2} width={barW / 2} y={y(p.revenue)} height={Math.max(0, y(0) - y(p.revenue))} className="chart__bar--revenue" />
            <rect x={x(i)} width={barW / 2} y={y(p.cost)} height={Math.max(0, y(0) - y(p.cost))} className="chart__bar--cost" />
            {i % labelEvery === 0 && (
              <text x={x(i)} y={height - 8} textAnchor="middle" className="chart__tick">{fmtDay(p.date)}</text>
            )}
          </g>
        ))}
        <path d={line('profit')} className="chart__line" />
        {points.length <= 45 && points.map((p, i) => (
          <circle key={p.date} cx={x(i)} cy={y(p.profit)} r={hover === i ? 4.5 : 2.5}
            className={p.profit >= 0 ? 'chart__dot' : 'chart__dot chart__dot--loss'} />
        ))}
      </svg>
      {hp && (
        <div className="chart__tooltip" style={{ left: Math.min(x(hover) + 12, width - 190) }}>
          <strong>{fmtDay(hp.date, { weekday: 'short', day: 'numeric', month: 'short' })}</strong>
          <span>Revenue <b>{money(hp.revenue)}</b></span>
          <span>Cost <b>{money(hp.cost)}</b></span>
          <span>Profit <b className={hp.profit >= 0 ? 'is-profit' : 'is-loss'}>{money(hp.profit)}</b></span>
          <span className="muted">{hp.orderCount} order{hp.orderCount === 1 ? '' : 's'}</span>
        </div>
      )}
    </div>
  );
}

/* ---------- Invoices ---------- */

async function openPdf(id, download) {
  // Open the tab synchronously so popup blockers allow it, then point it at the PDF.
  const win = download ? null : window.open('', '_blank');
  try {
    const blob = await getInvoicePdf(id, download);
    const url = URL.createObjectURL(blob);
    if (download) {
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice-${id}.pdf`;
      a.click();
    } else if (win) {
      win.location.href = url;
    } else {
      window.location.href = url;
    }
    setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (e) {
    win?.close();
    throw e;
  }
}

function InvoicesTab({ range }) {
  const { loading, error, data } = useLoader(() => getInvoices(range), [range.startDate, range.endDate]);
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(null);
  const [pdfError, setPdfError] = useState('');
  const [busy, setBusy] = useState(null);

  const invoices = useMemo(() => {
    const term = q.trim().toLowerCase();
    if (!data || !term) return data ?? [];
    return data.filter((inv) =>
      inv.number.toLowerCase().includes(term) ||
      inv.customer?.name?.toLowerCase().includes(term) ||
      inv.customer?.email?.toLowerCase().includes(term));
  }, [data, q]);

  const handlePdf = async (id, download) => {
    setPdfError('');
    setBusy(`${id}-${download}`);
    try { await openPdf(id, download); } catch (e) { setPdfError(e.message); } finally { setBusy(null); }
  };

  if (error) return <p className="form-error">{error}</p>;
  if (!data) return <p className="muted">Loading invoices…</p>;

  const total = invoices.reduce((s, inv) => s + inv.total, 0);

  return (
    <div className={loading ? 'is-loading' : ''}>
      <div className="toolbar">
        <input className="search" placeholder="Search invoice no, customer or email" value={q} onChange={(e) => setQ(e.target.value)} />
        <span className="muted small">{invoices.length} invoice{invoices.length === 1 ? '' : 's'} · <strong className="text-ink">{money(total)}</strong></span>
      </div>
      {pdfError && <p className="form-error">{pdfError}</p>}

      {invoices.length === 0 ? (
        <div className="empty">No invoices in this period.</div>
      ) : (
        <div className="table-wrap">
          <table className="data-table invoices">
            <thead>
              <tr>
                <th>Invoice</th><th>Date</th><th>Customer</th><th>Status</th>
                <th className="num">Total</th><th className="num">PDF</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <Fragment key={inv.id}>
                  <tr className={`invoices__row${open === inv.id ? ' is-open' : ''}`} onClick={() => setOpen(open === inv.id ? null : inv.id)}>
                    <td>
                      <button className="row-toggle" aria-expanded={open === inv.id} onClick={(e) => { e.stopPropagation(); setOpen(open === inv.id ? null : inv.id); }}>
                        {open === inv.id ? '−' : '+'}
                      </button>
                      <strong>{inv.number}</strong>
                      <div className="muted small">Order #{inv.orderId}</div>
                    </td>
                    <td>{fmtDateTime(inv.issuedAt)}</td>
                    <td>{inv.customer?.name}<div className="muted small">{inv.customer?.email}</div></td>
                    <td><span className={`status status--${inv.status}`}>{STATUS_LABELS[inv.status] ?? inv.status}</span></td>
                    <td className="num"><strong>{money(inv.total)}</strong></td>
                    <td className="num nowrap" onClick={(e) => e.stopPropagation()}>
                      <button className="link-btn" disabled={!!busy} onClick={() => handlePdf(inv.id, false)}>
                        {busy === `${inv.id}-false` ? 'Opening…' : 'View'}
                      </button>
                      <span className="sep">·</span>
                      <button className="link-btn" disabled={!!busy} onClick={() => handlePdf(inv.id, true)}>
                        {busy === `${inv.id}-true` ? 'Saving…' : 'Download'}
                      </button>
                    </td>
                  </tr>
                  {open === inv.id && (
                    <tr className="invoices__detail">
                      <td colSpan={6}><InvoiceDetail inv={inv} /></td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function InvoiceDetail({ inv }) {
  const cost = inv.items.reduce((s, it) => s + it.unitCost * it.quantity, 0);
  return (
    <div className="invoice-detail">
      <dl className="invoice-detail__meta">
        <div><dt>Ship to</dt><dd>{inv.shippingAddress || '—'}</dd></div>
        <div><dt>Tax ID</dt><dd>{inv.customer?.taxId || '—'}</dd></div>
        <div><dt>Card</dt><dd>{inv.cardLast4 ? `•••• ${inv.cardLast4}` : '—'}</dd></div>
      </dl>
      <table className="data-table data-table--compact">
        <thead>
          <tr><th>Product</th><th className="num">Qty</th><th className="num">Unit price</th><th className="num">Unit cost</th><th className="num">Line total</th></tr>
        </thead>
        <tbody>
          {inv.items.map((it) => (
            <tr key={it.id}>
              <td><Link to={`/shop/${it.productId}`} className="underline">{it.productName}</Link><div className="muted small">{it.brand}</div></td>
              <td className="num">{it.quantity}</td>
              <td className="num">{money(it.unitPrice)}</td>
              <td className="num muted">{money(it.unitCost)}</td>
              <td className="num">{money(it.lineTotal)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr><td colSpan={4}>Total</td><td className="num"><strong>{money(inv.total)}</strong></td></tr>
          <tr className="muted"><td colSpan={4}>Gross profit</td><td className="num">{money(inv.total - cost)}</td></tr>
        </tfoot>
      </table>
    </div>
  );
}

/* ---------- Discounts ---------- */

function DiscountsTab() {
  const [products, setProducts] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [q, setQ] = useState('');
  const [onlyDiscounted, setOnlyDiscounted] = useState(false);
  const [category, setCategory] = useState('');
  const [brand, setBrand] = useState('');
  const [families, setFamilies] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selected, setSelected] = useState(() => new Set());
  const [rate, setRate] = useState('10');
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getProducts().then(setProducts).catch((e) => setLoadError(e.message));
    getCategories().then(setCategories).catch(() => {});
  }, []);

  // Same filters as the collection page, applied locally on the full product list.
  const matches = useCallback((p, skip) => {
    const term = q.trim().toLowerCase();
    return (!onlyDiscounted || p.discountRate > 0) &&
      (!term || p.name.toLowerCase().includes(term) || p.brand.toLowerCase().includes(term)) &&
      (!category || p.category === category) &&
      (skip === 'brand' || !brand || p.brand === brand) &&
      families.every((f) => p.families?.includes(f));
  }, [q, onlyDiscounted, category, brand, families]);

  const visible = useMemo(() => (products ?? []).filter((p) => matches(p)), [products, matches]);
  // Only offer brands / families that still have results; keep selected ones so they can be cleared.
  const brandOptions = useMemo(() => {
    const counts = {};
    (products ?? []).filter((p) => matches(p, 'brand')).forEach((p) => { counts[p.brand] = (counts[p.brand] ?? 0) + 1; });
    if (brand && !counts[brand]) counts[brand] = 0;
    return Object.entries(counts).sort(([a], [b]) => a.localeCompare(b));
  }, [products, matches, brand]);
  const familyOptions = useMemo(() => {
    const present = new Set(visible.flatMap((p) => p.families ?? []));
    families.forEach((f) => present.add(f));
    return [...present].sort();
  }, [visible, families]);
  const toggleFamily = (f) => setFamilies((list) => (list.includes(f) ? list.filter((x) => x !== f) : [...list, f]));
  const hasFilters = q || onlyDiscounted || category || brand || families.length > 0;
  const clearFilters = () => { setQ(''); setOnlyDiscounted(false); setCategory(''); setBrand(''); setFamilies([]); };

  const rateNum = Number(rate);
  const rateValid = rate !== '' && rateNum >= 0 && rateNum <= 100;
  const allVisibleSelected = visible.length > 0 && visible.every((p) => selected.has(p.id));

  const toggle = (id) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const toggleAll = () => setSelected((s) => {
    const n = new Set(s);
    visible.forEach((p) => (allVisibleSelected ? n.delete(p.id) : n.add(p.id)));
    return n;
  });

  const apply = async (discountRate) => {
    setSaving(true); setError(''); setResult(null);
    try {
      const res = await setDiscount({ productIds: [...selected], discountRate });
      const updated = new Map(res.products.map((p) => [p.id, p]));
      setProducts((list) => list.map((p) => (updated.has(p.id) ? { ...p, ...updated.get(p.id) } : p)));
      setResult(res);
      setSelected(new Set());
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  if (loadError) return <p className="form-error">{loadError}</p>;
  if (!products) return <p className="muted">Loading products…</p>;

  return (
    <div className="discounts">
      <div className="panel discount-bar">
        <div>
          <h3>Apply a discount</h3>
          <p className="muted small">
            Select products below, set a rate and apply. Customers who have the product in their wishlist are notified automatically.
            Use 0% to remove a discount.
          </p>
        </div>
        <div className="discount-bar__form">
          <label className="field">
            Discount rate
            <span className="input-suffix">
              <input type="number" min="0" max="100" step="1" value={rate} onChange={(e) => setRate(e.target.value)} aria-invalid={!rateValid} />
              <span>%</span>
            </span>
          </label>
          <button className="btn btn-dark" disabled={!selected.size || !rateValid || saving} onClick={() => apply(rateNum)}>
            {saving ? 'Applying…' : `Apply to ${selected.size || 0} product${selected.size === 1 ? '' : 's'}`}
          </button>
          <button className="btn btn-ghost" disabled={!selected.size || saving} onClick={() => apply(0)}>Remove discount</button>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}
      {result && (
        <p className="form-success">
          {result.discountRate > 0
            ? `${result.discountRate}% discount applied to ${result.products.length} product${result.products.length === 1 ? '' : 's'}.`
            : `Discount removed from ${result.products.length} product${result.products.length === 1 ? '' : 's'}.`}
          {' '}{result.notificationsSent} wishlist notification{result.notificationsSent === 1 ? '' : 's'} sent.
        </p>
      )}

      <div className="shop__layout discounts__layout">
      <aside className="filters">
        <h4>Category</h4>
        <button className={`chip ${!category ? 'active' : ''}`} onClick={() => setCategory('')}>All</button>
        {categories.map((c) => (
          <button key={c.id} className={`chip ${category === c.id ? 'active' : ''}`} onClick={() => setCategory(c.id)}>{c.name}</button>
        ))}

        <h4>Brand</h4>
        <select value={brand} onChange={(e) => setBrand(e.target.value)} aria-label="Brand">
          <option value="">All brands</option>
          {brandOptions.map(([b, n]) => <option key={b} value={b}>{b} ({n})</option>)}
        </select>

        <h4>Scent Family</h4>
        <div className="chips">
          {familyOptions.map((f) => (
            <button key={f} className={`chip ${families.includes(f) ? 'active' : ''}`} aria-pressed={families.includes(f)} onClick={() => toggleFamily(f)}>{f}</button>
          ))}
        </div>

        {hasFilters && <button className="link-btn" onClick={clearFilters}>Clear filters</button>}
      </aside>

      <section>
      <div className="toolbar">
        <input className="search" type="search" placeholder="Search products or brands" value={q} onChange={(e) => setQ(e.target.value)} />
        <label className="check">
          <input type="checkbox" checked={onlyDiscounted} onChange={(e) => setOnlyDiscounted(e.target.checked)} />
          Only discounted
        </label>
      </div>
      <div className="toolbar toolbar--sub">
        <span className="muted small">
          {visible.length} product{visible.length === 1 ? '' : 's'} shown · {selected.size} selected
        </span>
        <span className="small">
          <button className="link-btn" disabled={!visible.length} onClick={toggleAll}>
            {allVisibleSelected ? 'Deselect all shown' : `Select all ${visible.length} shown`}
          </button>
          {selected.size > 0 && <><span className="sep">·</span><button className="link-btn" onClick={() => setSelected(new Set())}>Clear selection</button></>}
        </span>
      </div>

      {visible.length === 0 ? (
        <div className="empty">No products match.</div>
      ) : (
        <div className="table-wrap">
          <table className="data-table products-table">
            <thead>
              <tr>
                <th className="check-col"><input type="checkbox" checked={allVisibleSelected} onChange={toggleAll} aria-label="Select all" /></th>
                <th>Product</th>
                <th className="num">Stock</th>
                <th className="num">List price</th>
                <th className="num">Discount</th>
                <th className="num">Current price</th>
                <th className="num">{rateValid && selected.size ? `New at ${rateNum}%` : 'Preview'}</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((p) => {
                const isSel = selected.has(p.id);
                const preview = p.originalPrice * (1 - rateNum / 100);
                return (
                  <tr key={p.id} className={isSel ? 'is-selected' : ''} onClick={() => toggle(p.id)}>
                    <td className="check-col"><input type="checkbox" checked={isSel} onChange={() => toggle(p.id)} onClick={(e) => e.stopPropagation()} aria-label={`Select ${p.name}`} /></td>
                    <td><strong>{p.name}</strong><div className="muted small">{p.brand} · {p.volumeMl} ml</div></td>
                    <td className="num">{p.stock}</td>
                    <td className="num muted">{money(p.originalPrice)}</td>
                    <td className="num">{p.discountRate > 0 ? <span className="badge badge-out">−{p.discountRate}%</span> : <span className="muted">—</span>}</td>
                    <td className="num"><strong>{money(p.price)}</strong></td>
                    <td className="num">{isSel && rateValid ? money(preview) : <span className="muted">—</span>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      </section>
      </div>
    </div>
  );
}

/* ---------- Refunds (placeholder until the backend endpoints exist) ---------- */

function RefundsTab() {
  return (
    <div className="coming-soon">
      <span className="badge badge-low">Coming soon</span>
      <h2>Refund Requests</h2>
      <p className="muted">
        Review refund requests from customers, approve or reject them, and see the refunded amount
        at the original purchase price. This section will be available in an upcoming release.
      </p>
      <ul className="coming-soon__list">
        <li>Pending requests with order and product details</li>
        <li>Approve or reject with one click</li>
        <li>Refunded amount based on the price paid at purchase</li>
      </ul>
    </div>
  );
}
