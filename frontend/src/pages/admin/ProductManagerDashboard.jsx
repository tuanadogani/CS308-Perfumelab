import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  getManagedProducts, createProduct, updateProduct, deactivateProduct,
  getManagedCategories, createCategory, updateCategory, deleteCategory,
  getDeliveries, advanceOrderStatus, getComments, moderateComment,
} from '../../api/productManagerApi';

// Product manager panel (Requirement 12): products & categories, stock, deliveries, comment approval.

const TABS = [
  ['products', 'Products & Stock'],
  ['categories', 'Categories'],
  ['deliveries', 'Deliveries'],
  ['comments', 'Comments'],
];

const LOW_STOCK = 5;
const GENDERS = ['Women', 'Men', 'Unisex'];
const TIERS = [['top', 'Top notes'], ['heart', 'Heart notes'], ['base', 'Base notes']];

const STATUS_LABELS = {
  processing: 'Processing', in_transit: 'In transit', delivered: 'Delivered',
  cancelled: 'Cancelled', refunded: 'Refunded',
};
const NEXT_STATUS = { processing: 'in_transit', in_transit: 'delivered' };
const NEXT_ACTION = { processing: 'Mark in transit', in_transit: 'Mark delivered' };

const money = (n) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'TRY', currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(n ?? 0);
const fmtDateTime = (s) =>
  new Date(s).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const slugify = (s) => s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '')
  .replace(/ı/g, 'i').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
const commentState = (c) => (!c.reviewed_at ? 'pending' : c.approved ? 'approved' : 'rejected');
const stockLevel = (p) => (p.stock === 0 ? 'out' : p.stock <= LOW_STOCK ? 'low' : 'ok');

export default function ProductManagerDashboard() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = TABS.some(([k]) => k === params.get('tab')) ? params.get('tab') : 'products';
  const setTab = (key) => setParams({ tab: key }, { replace: true });

  // Everything is loaded once here so the overview numbers stay in sync with every tab.
  const [products, setProducts] = useState(null);
  const [categories, setCategories] = useState(null);
  const [deliveries, setDeliveries] = useState(null);
  const [comments, setComments] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [notice, setNotice] = useState(null);

  const load = useCallback(() => {
    setLoadError('');
    Promise.all([getManagedProducts(), getManagedCategories(), getDeliveries(), getComments()])
      .then(([p, c, d, m]) => { setProducts(p); setCategories(c); setDeliveries(d); setComments(m); })
      .catch((e) => setLoadError(e.message));
  }, []);
  useEffect(load, [load]);

  const flash = useCallback((message, type = 'success') => setNotice({ message, type, at: Date.now() }), []);
  useEffect(() => {
    if (!notice || notice.type !== 'success') return undefined;
    const t = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(t);
  }, [notice]);

  const ready = products && categories && deliveries && comments;
  const counts = useMemo(() => {
    if (!ready) return null;
    const active = products.filter((p) => p.active);
    return {
      active: active.length,
      inactive: products.length - active.length,
      out: active.filter((p) => p.stock === 0).length,
      low: active.filter((p) => stockLevel(p) === 'low').length,
      openOrders: new Set(deliveries.filter((d) => NEXT_STATUS[d.status]).map((d) => d.orderId)).size,
      processing: new Set(deliveries.filter((d) => d.status === 'processing').map((d) => d.orderId)).size,
      pendingComments: comments.filter((c) => commentState(c) === 'pending').length,
    };
  }, [ready, products, deliveries, comments]);

  return (
    <div className="container section sales pm">
      <p className="eyebrow">Admin Panel · Product Manager</p>
      <h1>Product Dashboard</h1>
      <p className="muted">Hello {user.name.split(' ')[0]}, here is what needs your attention.</p>

      {loadError && (
        <p className="form-error pm__load-error">
          {loadError} <button className="link-btn" onClick={load}>Try again</button>
        </p>
      )}

      {counts && (
        <div className="kpis pm__kpis">
          <button className="kpi kpi--link" onClick={() => setTab('products')}>
            <span className="kpi__label">Active products</span>
            <strong className="kpi__value">{counts.active}</strong>
            <span className="muted small">{counts.inactive ? `${counts.inactive} inactive` : 'All listed in the store'}</span>
          </button>
          <button className={`kpi kpi--link${counts.out ? ' is-loss' : ''}`} onClick={() => setTab('products')}>
            <span className="kpi__label">Out of stock</span>
            <strong className="kpi__value">{counts.out}</strong>
            <span className="small">{counts.low ? `${counts.low} running low (≤ ${LOW_STOCK})` : 'Stock levels look fine'}</span>
          </button>
          <button className="kpi kpi--link" onClick={() => setTab('deliveries')}>
            <span className="kpi__label">Open orders</span>
            <strong className="kpi__value">{counts.openOrders}</strong>
            <span className="muted small">{counts.processing} waiting to ship</span>
          </button>
          <button className="kpi kpi--link" onClick={() => setTab('comments')}>
            <span className="kpi__label">Comments to review</span>
            <strong className="kpi__value">{counts.pendingComments}</strong>
            <span className="muted small">{counts.pendingComments ? 'Hidden until approved' : 'All caught up'}</span>
          </button>
        </div>
      )}

      <nav className="tabs" role="tablist">
        {TABS.map(([key, label]) => {
          const badge = counts && { deliveries: counts.processing, comments: counts.pendingComments }[key];
          return (
            <button key={key} role="tab" aria-selected={tab === key}
              className={`tabs__tab${tab === key ? ' active' : ''}`} onClick={() => setTab(key)}>
              {label}
              {badge > 0 && <span className="tabs__tag">{badge}</span>}
            </button>
          );
        })}
      </nav>

      {notice && (
        <p className={notice.type === 'success' ? 'form-success' : 'form-error pm__notice'} role="status">
          {notice.message}
          <button className="pm__notice-close" aria-label="Dismiss" onClick={() => setNotice(null)}>×</button>
        </p>
      )}

      {!ready && !loadError && <p className="muted">Loading…</p>}
      {ready && tab === 'products' && (
        <ProductsTab products={products} setProducts={setProducts} categories={categories} flash={flash} />
      )}
      {ready && tab === 'categories' && (
        <CategoriesTab categories={categories} setCategories={setCategories}
          products={products} setProducts={setProducts} flash={flash} />
      )}
      {ready && tab === 'deliveries' && (
        <DeliveriesTab deliveries={deliveries} setDeliveries={setDeliveries} flash={flash} />
      )}
      {ready && tab === 'comments' && (
        <CommentsTab comments={comments} setComments={setComments} flash={flash} />
      )}
    </div>
  );
}

/* ---------- Products & stock ---------- */

const PRODUCT_FILTERS = [
  ['all', 'All'],
  ['active', 'Active'],
  ['low', 'Low stock'],
  ['out', 'Out of stock'],
  ['inactive', 'Inactive'],
];

function ProductsTab({ products, setProducts, categories, flash }) {
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState('all');
  const [category, setCategory] = useState('');
  const [editing, setEditing] = useState(null); // null | 'new' | product
  const [busy, setBusy] = useState(null);

  const categoryName = useMemo(() => Object.fromEntries(categories.map((c) => [c.slug, c.name])), [categories]);

  const visible = useMemo(() => {
    const term = q.trim().toLowerCase();
    return products.filter((p) => {
      const byFilter = {
        all: true,
        active: p.active,
        low: p.active && stockLevel(p) === 'low',
        out: p.active && p.stock === 0,
        inactive: !p.active,
      }[filter];
      return byFilter &&
        (!category || p.category === category) &&
        (!term || [p.name, p.brand, p.model, p.serialNumber].some((v) => v?.toLowerCase().includes(term)));
    });
  }, [products, q, filter, category]);

  const replace = (updated) => setProducts((list) => list.map((p) => (p.id === updated.id ? updated : p)));

  const saveStock = async (p, stock) => {
    setBusy(p.id);
    try {
      replace(await updateProduct(p.id, { stock }));
      flash(`Stock for ${p.name} set to ${stock}.`);
    } catch (e) {
      flash(e.message, 'error');
    } finally {
      setBusy(null);
    }
  };

  const toggleActive = async (p) => {
    if (p.active && !window.confirm(`Remove "${p.name}" from the store? Past orders keep it, and you can restore it later.`)) return;
    setBusy(p.id);
    try {
      if (p.active) {
        await deactivateProduct(p.id);
        replace({ ...p, active: false });
        flash(`${p.name} was removed from the store.`);
      } else {
        replace(await updateProduct(p.id, { active: true }));
        flash(`${p.name} is back in the store.`);
      }
    } catch (e) {
      flash(e.message, 'error');
    } finally {
      setBusy(null);
    }
  };

  const onSaved = (saved, isNew) => {
    setProducts((list) => (isNew ? [...list, saved] : list.map((p) => (p.id === saved.id ? saved : p))));
    setEditing(null);
    flash(isNew
      ? `${saved.name} was added. Its price is 0 until the sales manager sets one.`
      : `${saved.name} was updated.`);
  };

  return (
    <div>
      <div className="toolbar">
        <input className="search" type="search" placeholder="Search name, brand, model or serial no"
          value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="pm__toolbar-right">
          <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
            <option value="">All categories</option>
            {categories.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
          </select>
          <button className="btn btn-dark pm__add" onClick={() => setEditing('new')} disabled={!categories.length}
            title={categories.length ? undefined : 'Create a category first'}>
            + Add product
          </button>
        </div>
      </div>
      <div className="toolbar toolbar--sub">
        <div className="chips pm__chips">
          {PRODUCT_FILTERS.map(([key, label]) => (
            <button key={key} className={`chip${filter === key ? ' active' : ''}`} onClick={() => setFilter(key)}>{label}</button>
          ))}
        </div>
        <span className="muted small">{plural(visible.length, 'product')} shown</span>
      </div>

      {visible.length === 0 ? (
        <div className="empty">No products match.</div>
      ) : (
        <div className="table-wrap">
          <table className="data-table pm-products">
            <thead>
              <tr>
                <th>Product</th>
                <th>Category</th>
                <th>Serial no</th>
                <th className="num">Price</th>
                <th className="num">Stock</th>
                <th>Status</th>
                <th className="num">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((p) => (
                <tr key={p.id} className={p.active ? '' : 'is-inactive'}>
                  <td>
                    <strong>{p.name}</strong>
                    <div className="muted small">{p.brand} · {p.model} · {p.volumeMl} ml · {p.gender}</div>
                  </td>
                  <td>{categoryName[p.category] ?? p.category}</td>
                  <td className="muted small mono">{p.serialNumber}</td>
                  <td className="num">
                    {p.price > 0 ? money(p.price) : <span className="badge badge-low" title="Set by the sales manager">No price</span>}
                  </td>
                  <td className="num">
                    <StockInput product={p} disabled={busy === p.id} onSave={(n) => saveStock(p, n)} />
                  </td>
                  <td>
                    {!p.active ? <span className="status">Inactive</span>
                      : p.stock === 0 ? <span className="status status--cancelled">Out of stock</span>
                        : stockLevel(p) === 'low' ? <span className="status status--in_transit">Low stock</span>
                          : <span className="status status--delivered">In stock</span>}
                  </td>
                  <td className="num nowrap">
                    {p.active && <><Link to={`/shop/${p.id}`} className="link-btn">View</Link><span className="sep">·</span></>}
                    <button className="link-btn" disabled={busy === p.id} onClick={() => setEditing(p)}>Edit</button>
                    <span className="sep">·</span>
                    <button className="link-btn" disabled={busy === p.id} onClick={() => toggleActive(p)}>
                      {p.active ? 'Remove' : 'Restore'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <ProductDialog
          product={editing === 'new' ? null : editing}
          categories={categories}
          onClose={() => setEditing(null)}
          onSaved={onSaved}
        />
      )}
    </div>
  );
}

function StockInput({ product, disabled, onSave }) {
  const [value, setValue] = useState(String(product.stock));
  useEffect(() => setValue(String(product.stock)), [product.stock]);
  const n = Number(value);
  const valid = value !== '' && Number.isInteger(n) && n >= 0;
  const dirty = valid && n !== product.stock;

  const commit = () => {
    if (dirty) onSave(n);
    else setValue(String(product.stock));
  };

  return (
    <span className="stock-input">
      <button type="button" aria-label="Decrease stock" disabled={disabled || n <= 0}
        onClick={() => onSave(Math.max(0, product.stock - 1))}>−</button>
      <input
        type="number" min="0" step="1" inputMode="numeric" value={value} disabled={disabled}
        aria-label={`Stock for ${product.name}`} aria-invalid={!valid}
        onChange={(e) => setValue(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur();
          if (e.key === 'Escape') { setValue(String(product.stock)); e.currentTarget.blur(); }
        }}
      />
      <button type="button" aria-label="Increase stock" disabled={disabled}
        onClick={() => onSave(product.stock + 1)}>+</button>
    </span>
  );
}

const emptyForm = (categories, defaultCategory) => ({
  name: '', brand: '', model: '', serial_number: '', description: '',
  category: defaultCategory ?? categories[0]?.slug ?? '', gender: 'Unisex', volume_ml: '50', stock: '0',
  warranty_status: '', distributor: '', families: '', top: '', heart: '', base: '',
});

const toForm = (p) => ({
  name: p.name, brand: p.brand, model: p.model, serial_number: p.serialNumber, description: p.description,
  category: p.category, gender: p.gender, volume_ml: String(p.volumeMl), stock: String(p.stock),
  warranty_status: p.warrantyStatus, distributor: p.distributor,
  families: (p.families ?? []).join(', '),
  top: (p.notes?.top ?? []).join(', '), heart: (p.notes?.heart ?? []).join(', '), base: (p.notes?.base ?? []).join(', '),
});

const splitList = (s) => [...new Set(s.split(',').map((x) => x.trim()).filter(Boolean))];

const toPayload = (f) => ({
  name: f.name.trim(), brand: f.brand.trim(), model: f.model.trim(), serial_number: f.serial_number.trim(),
  description: f.description.trim(), category: f.category, gender: f.gender,
  volume_ml: Number(f.volume_ml), stock: Number(f.stock),
  warranty_status: f.warranty_status.trim(), distributor: f.distributor.trim(),
  families: splitList(f.families),
  notes: { top: splitList(f.top), heart: splitList(f.heart), base: splitList(f.base) },
});

function validate(f) {
  const errors = {};
  ['name', 'brand', 'model', 'serial_number', 'description', 'warranty_status', 'distributor'].forEach((k) => {
    if (!f[k].trim()) errors[k] = 'Required';
  });
  if (!f.category) errors.category = 'Required';
  const vol = Number(f.volume_ml);
  if (!Number.isInteger(vol) || vol < 1) errors.volume_ml = 'Whole number, at least 1';
  const stock = Number(f.stock);
  if (f.stock === '' || !Number.isInteger(stock) || stock < 0) errors.stock = 'Whole number, 0 or more';
  return errors;
}

// Turns DRF field errors ("serial_number: product with this ... already exists.") into per-field messages.
function fieldErrorsFrom(message) {
  const out = {};
  message.split(/\s(?=[a-z_]+: )/).forEach((part) => {
    const m = part.match(/^([a-z_]+): (.*)$/);
    if (m) out[m[1]] = m[2];
  });
  return out;
}

function ProductDialog({ product, categories, defaultCategory, onClose, onSaved }) {
  const dialog = useRef(null);
  const isNew = !product;
  const initial = useMemo(
    () => (isNew ? emptyForm(categories, defaultCategory) : toForm(product)),
    [isNew, product, categories, defaultCategory],
  );
  const [form, setForm] = useState(initial);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [serverError, setServerError] = useState('');

  useEffect(() => {
    const el = dialog.current;
    const prev = document.body.style.overflow;
    el.showModal();
    document.body.style.overflow = 'hidden';
    return () => { el.close(); document.body.style.overflow = prev; };
  }, []);

  const set = (key) => (e) => {
    const next = { ...form, [key]: e.target.value };
    setForm(next);
    if (touched) setErrors(validate(next));
  };

  const submit = async (e) => {
    e.preventDefault();
    setTouched(true);
    const errs = validate(form);
    setErrors(errs);
    if (Object.keys(errs).length) return;

    const payload = toPayload(form);
    let body = payload;
    if (!isNew) {
      // Send only what changed so concurrent stock or sales updates are not overwritten.
      const before = toPayload(initial);
      body = Object.fromEntries(Object.entries(payload).filter(([k, v]) => JSON.stringify(v) !== JSON.stringify(before[k])));
      if (!Object.keys(body).length) { onClose(); return; }
    }
    setSaving(true);
    setServerError('');
    try {
      const saved = isNew ? await createProduct(body) : await updateProduct(product.id, body);
      onSaved(saved, isNew);
    } catch (err) {
      const fieldErrs = fieldErrorsFrom(err.message);
      if (Object.keys(fieldErrs).length) setErrors(fieldErrs);
      setServerError(err.message);
      setSaving(false);
    }
  };

  const field = (key, label, props = {}) => (
    <label className="field">
      {label}
      <input value={form[key]} onChange={set(key)} aria-invalid={!!errors[key]} {...props} />
      {errors[key] && <span className="field-error">{errors[key]}</span>}
    </label>
  );

  return (
    <dialog ref={dialog} className="added-modal pm-dialog" onCancel={(e) => { e.preventDefault(); if (!saving) onClose(); }}
      aria-labelledby="pm-dialog-title">
      <form className="added-modal__content" onSubmit={submit} noValidate>
        <div className="pm-dialog__head">
          <div>
            <p className="eyebrow">{isNew ? 'New product' : `Product #${product.id}`}</p>
            <h2 id="pm-dialog-title">{isNew ? 'Add a product' : `Edit ${product.name}`}</h2>
          </div>
          <button type="button" className="pm__notice-close" aria-label="Close" onClick={onClose} disabled={saving}>×</button>
        </div>

        {serverError && <p className="form-error">{serverError}</p>}

        <fieldset className="pm-form" disabled={saving}>
          <legend>Basics</legend>
          <div className="pm-form__grid">
            {field('name', 'Name', { autoFocus: true })}
            {field('brand', 'Brand')}
            {field('model', 'Model')}
            {field('serial_number', 'Serial number')}
            <label className="field">
              Category
              <select value={form.category} onChange={set('category')} aria-invalid={!!errors.category}>
                {categories.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
              </select>
              {errors.category && <span className="field-error">{errors.category}</span>}
            </label>
            <label className="field">
              Gender
              <select value={form.gender} onChange={set('gender')}>
                {GENDERS.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </label>
            {field('volume_ml', 'Volume (ml)', { type: 'number', min: 1, step: 1 })}
            {field('stock', 'Stock', { type: 'number', min: 0, step: 1 })}
          </div>
          <label className="field">
            Description
            <textarea rows={3} value={form.description} onChange={set('description')} aria-invalid={!!errors.description} />
            {errors.description && <span className="field-error">{errors.description}</span>}
          </label>
        </fieldset>

        <fieldset className="pm-form" disabled={saving}>
          <legend>Scent</legend>
          {field('families', 'Scent families', { placeholder: 'e.g. Woody, Fresh' })}
          <div className="pm-form__grid pm-form__grid--3">
            {TIERS.map(([key, label]) => (
              <Fragment key={key}>{field(key, label, { placeholder: 'Comma separated' })}</Fragment>
            ))}
          </div>
        </fieldset>

        <fieldset className="pm-form" disabled={saving}>
          <legend>Supply</legend>
          <div className="pm-form__grid">
            {field('warranty_status', 'Warranty', { placeholder: 'e.g. 2 years' })}
            {field('distributor', 'Distributor')}
          </div>
        </fieldset>

        {isNew && (
          <p className="muted small">New products start without a price. The sales manager sets it before customers can buy.</p>
        )}

        <div className="pm-dialog__actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={saving}>Cancel</button>
          <button type="submit" className="btn btn-dark" disabled={saving}>
            {saving ? 'Saving…' : isNew ? 'Add product' : 'Save changes'}
          </button>
        </div>
      </form>
    </dialog>
  );
}

/* ---------- Categories ---------- */

function CategoriesTab({ categories, setCategories, products, setProducts, flash }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugEdited, setSlugEdited] = useState(false);
  const [adding, setAdding] = useState(false);
  const [renaming, setRenaming] = useState(null); // { id, name }
  const [busy, setBusy] = useState(null);
  const [open, setOpen] = useState(null); // expanded category id
  const [newIn, setNewIn] = useState(null); // category slug for the "new product" dialog

  const bySlug = useMemo(() => {
    const out = {};
    products.forEach((p) => { (out[p.category] ??= []).push(p); });
    Object.values(out).forEach((list) => list.sort((a, b) => b.active - a.active || a.name.localeCompare(b.name)));
    return out;
  }, [products]);

  const effectiveSlug = slugEdited ? slug : slugify(name);
  const sortByName = (list) => [...list].sort((a, b) => a.name.localeCompare(b.name));

  const add = async (e) => {
    e.preventDefault();
    if (!name.trim() || !effectiveSlug) return;
    setAdding(true);
    try {
      const created = await createCategory({ name: name.trim(), slug: effectiveSlug });
      setCategories((list) => sortByName([...list, created]));
      setName(''); setSlug(''); setSlugEdited(false);
      setOpen(created.id); // straight into filling the new category
      flash(`Category "${created.name}" was created. Add existing products or create a new one below.`);
    } catch (err) {
      flash(err.message, 'error');
    } finally {
      setAdding(false);
    }
  };

  const rename = async (c) => {
    const next = renaming.name.trim();
    if (!next || next === c.name) { setRenaming(null); return; }
    setBusy(c.id);
    try {
      const updated = await updateCategory(c.id, { name: next });
      setCategories((list) => sortByName(list.map((x) => (x.id === c.id ? updated : x))));
      setRenaming(null);
      flash(`Category renamed to "${updated.name}".`);
    } catch (err) {
      flash(err.message, 'error');
    } finally {
      setBusy(null);
    }
  };

  const remove = async (c) => {
    if (!window.confirm(`Delete the "${c.name}" category?`)) return;
    setBusy(c.id);
    try {
      await deleteCategory(c.id);
      setCategories((list) => list.filter((x) => x.id !== c.id));
      if (open === c.id) setOpen(null);
      flash(`Category "${c.name}" was deleted.`);
    } catch (err) {
      flash(err.message, 'error');
    } finally {
      setBusy(null);
    }
  };

  // A product has exactly one category, so "adding" it here moves it out of its old one.
  const moveProducts = async (ids, target) => {
    const results = await Promise.allSettled(ids.map((id) => updateProduct(id, { category: target.slug })));
    const moved = results.filter((r) => r.status === 'fulfilled').map((r) => r.value);
    const failed = results.find((r) => r.status === 'rejected');
    if (moved.length) {
      const map = new Map(moved.map((p) => [p.id, p]));
      setProducts((list) => list.map((p) => map.get(p.id) ?? p));
    }
    if (failed) flash(`${plural(moved.length, 'product')} moved. Some could not be moved: ${failed.reason.message}`, 'error');
    else flash(`${plural(moved.length, 'product')} moved to ${target.name}.`);
    return !failed;
  };

  const onSaved = (saved) => {
    setProducts((list) => [...list, saved]);
    setNewIn(null);
    flash(`${saved.name} was added. Its price is 0 until the sales manager sets one.`);
  };

  return (
    <div className="pm-categories">
      <form className="panel discount-bar" onSubmit={add}>
        <div>
          <h3>Add a category</h3>
          <p className="muted small">After creating it you can move existing perfumes into it or add new ones. A category can only be deleted once it is empty, inactive products included.</p>
        </div>
        <div className="discount-bar__form">
          <label className="field">
            Name
            <input className="pm-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Body Mist" />
          </label>
          <label className="field">
            Slug
            <input className="pm-input" value={effectiveSlug}
              onChange={(e) => { setSlugEdited(true); setSlug(slugify(e.target.value)); }} placeholder="body-mist" />
          </label>
          <button className="btn btn-dark" disabled={adding || !name.trim() || !effectiveSlug}>
            {adding ? 'Adding…' : 'Add category'}
          </button>
        </div>
      </form>

      {categories.length === 0 ? (
        <div className="empty">No categories yet.</div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Name</th><th>Slug</th><th className="num">Products</th><th className="num">Actions</th></tr>
            </thead>
            <tbody>
              {categories.map((c) => {
                const list = bySlug[c.slug] ?? [];
                const activeCount = list.filter((p) => p.active).length;
                const isRenaming = renaming?.id === c.id;
                const isOpen = open === c.id;
                const toggle = () => setOpen(isOpen ? null : c.id);
                return (
                  <Fragment key={c.id}>
                    <tr className={`invoices__row${isOpen ? ' is-open' : ''}`} onClick={isRenaming ? undefined : toggle}>
                      <td>
                        <button className="row-toggle" aria-expanded={isOpen} aria-label={`Show products in ${c.name}`}
                          onClick={(e) => { e.stopPropagation(); toggle(); }}>
                          {isOpen ? '−' : '+'}
                        </button>
                        {isRenaming ? (
                          <input className="pm-input" autoFocus value={renaming.name} disabled={busy === c.id}
                            aria-label={`New name for ${c.name}`} onClick={(e) => e.stopPropagation()}
                            onChange={(e) => setRenaming({ id: c.id, name: e.target.value })}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') rename(c);
                              if (e.key === 'Escape') setRenaming(null);
                            }} />
                        ) : <strong>{c.name}</strong>}
                      </td>
                      <td className="muted mono small">{c.slug}</td>
                      <td className="num">
                        {activeCount}
                        {list.length > activeCount && <div className="muted small">+{list.length - activeCount} inactive</div>}
                      </td>
                      <td className="num nowrap" onClick={(e) => e.stopPropagation()}>
                        {isRenaming ? (
                          <>
                            <button className="link-btn" disabled={busy === c.id} onClick={() => rename(c)}>Save</button>
                            <span className="sep">·</span>
                            <button className="link-btn" disabled={busy === c.id} onClick={() => setRenaming(null)}>Cancel</button>
                          </>
                        ) : (
                          <>
                            <button className="link-btn" disabled={busy === c.id} onClick={() => setRenaming({ id: c.id, name: c.name })}>Rename</button>
                            <span className="sep">·</span>
                            <button className="link-btn" disabled={busy === c.id || list.length > 0} onClick={() => remove(c)}
                              title={list.length ? 'Move its products to another category first' : undefined}>Delete</button>
                          </>
                        )}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="invoices__detail">
                        <td colSpan={4}>
                          <CategoryProducts
                            category={c}
                            categories={categories}
                            items={list}
                            allProducts={products}
                            onMove={moveProducts}
                            onNew={() => setNewIn(c.slug)}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {newIn && (
        <ProductDialog product={null} categories={categories} defaultCategory={newIn}
          onClose={() => setNewIn(null)} onSaved={onSaved} />
      )}
    </div>
  );
}

function CategoryProducts({ category, categories, items, allProducts, onMove, onNew }) {
  const [picking, setPicking] = useState(items.length === 0);
  const [q, setQ] = useState('');
  const [selected, setSelected] = useState(() => new Set());
  const [moving, setMoving] = useState(null); // 'in' | product id

  const categoryName = useMemo(() => Object.fromEntries(categories.map((c) => [c.slug, c.name])), [categories]);
  const others = categories.filter((c) => c.slug !== category.slug);

  const candidates = useMemo(() => {
    const term = q.trim().toLowerCase();
    return allProducts
      .filter((p) => p.category !== category.slug)
      .filter((p) => !term || [p.name, p.brand].some((v) => v.toLowerCase().includes(term)))
      .sort((a, b) => b.active - a.active || a.name.localeCompare(b.name));
  }, [allProducts, category.slug, q]);

  const toggle = (id) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const moveIn = async () => {
    setMoving('in');
    const ok = await onMove([...selected], category);
    setMoving(null);
    if (ok) { setSelected(new Set()); setPicking(false); setQ(''); }
  };

  const moveOut = async (p, slug) => {
    if (!slug) return;
    setMoving(p.id);
    await onMove([p.id], categories.find((c) => c.slug === slug));
    setMoving(null);
  };

  return (
    <div className="pm-catprod">
      <div className="pm-catprod__head">
        <h3>Perfumes in {category.name}</h3>
        <span className="pm-catprod__actions">
          <button className="btn btn-ghost" onClick={() => setPicking((v) => !v)} disabled={!!moving}>
            {picking ? 'Close picker' : '+ Add existing products'}
          </button>
          <button className="btn btn-dark" onClick={onNew} disabled={!!moving}>+ New product</button>
        </span>
      </div>

      {picking && (
        <div className="pm-picker">
          <div className="toolbar">
            <input className="search" type="search" placeholder="Search perfumes or brands" autoFocus
              value={q} onChange={(e) => setQ(e.target.value)} />
            <button className="btn btn-dark pm-picker__go" disabled={!selected.size || !!moving} onClick={moveIn}>
              {moving === 'in' ? 'Moving…' : `Move ${plural(selected.size, 'product')} here`}
            </button>
          </div>
          <p className="muted small pm-picker__hint">
            Each perfume has one category, so selected perfumes leave their current category.
          </p>
          {candidates.length === 0 ? (
            <div className="empty pm-picker__empty">No other products{q ? ' match' : ''}.</div>
          ) : (
            <ul className="pm-picker__list">
              {candidates.map((p) => (
                <li key={p.id}>
                  <label className={`check pm-picker__item${selected.has(p.id) ? ' is-selected' : ''}`}>
                    <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggle(p.id)} />
                    <span className="pm-picker__name">
                      <strong>{p.name}</strong>
                      <span className="muted small">{p.brand} · {p.volumeMl} ml{!p.active && ' · inactive'}</span>
                    </span>
                    <span className="muted small pm-picker__from">from {categoryName[p.category] ?? p.category}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {items.length === 0 ? (
        !picking && <p className="muted">No perfumes in this category yet.</p>
      ) : (
        <table className="data-table data-table--compact">
          <thead>
            <tr><th>Perfume</th><th className="num">Stock</th><th>Status</th><th className="num">Move to</th></tr>
          </thead>
          <tbody>
            {items.map((p) => (
              <tr key={p.id} className={p.active ? '' : 'is-inactive'}>
                <td>
                  {p.active
                    ? <Link to={`/shop/${p.id}`} className="underline"><strong>{p.name}</strong></Link>
                    : <strong>{p.name}</strong>}
                  <div className="muted small">{p.brand} · {p.volumeMl} ml · {p.gender}</div>
                </td>
                <td className="num">{p.stock}</td>
                <td>
                  {!p.active ? <span className="status">Inactive</span>
                    : p.stock === 0 ? <span className="status status--cancelled">Out of stock</span>
                      : <span className="status status--delivered">In stock</span>}
                </td>
                <td className="num">
                  <select value="" disabled={!!moving || !others.length} aria-label={`Move ${p.name} to another category`}
                    onChange={(e) => moveOut(p, e.target.value)}>
                    <option value="">{moving === p.id ? 'Moving…' : 'Choose…'}</option>
                    {others.map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* ---------- Deliveries ---------- */

const DELIVERY_FILTERS = [
  ['open', 'To do'],
  ['processing', 'Processing'],
  ['in_transit', 'In transit'],
  ['delivered', 'Delivered'],
  ['all', 'All'],
];

function DeliveriesTab({ deliveries, setDeliveries, flash }) {
  const [filter, setFilter] = useState('open');
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(null);

  // The backend lists one row per order line; the status moves per order, so group them.
  const orders = useMemo(() => {
    const byId = new Map();
    deliveries.forEach((d) => {
      if (!byId.has(d.orderId)) {
        byId.set(d.orderId, { id: d.orderId, customerId: d.customerId, address: d.address, status: d.status, items: [], total: 0 });
      }
      const o = byId.get(d.orderId);
      o.items.push(d);
      o.total += Number(d.totalPrice);
    });
    const rank = { processing: 0, in_transit: 1, delivered: 2 };
    return [...byId.values()].sort((a, b) => (rank[a.status] ?? 3) - (rank[b.status] ?? 3) || a.id - b.id);
  }, [deliveries]);

  const visible = useMemo(() => {
    const term = q.trim().toLowerCase();
    return orders.filter((o) =>
      (filter === 'all' || (filter === 'open' ? !!NEXT_STATUS[o.status] : o.status === filter)) &&
      (!term || String(o.id).includes(term) || o.address.toLowerCase().includes(term) ||
        o.items.some((it) => it.productName.toLowerCase().includes(term))));
  }, [orders, filter, q]);

  const advance = async (o) => {
    const next = NEXT_STATUS[o.status];
    setBusy(o.id);
    try {
      const res = await advanceOrderStatus(o.id, next);
      setDeliveries((list) => list.map((d) => (d.orderId === o.id
        ? { ...d, status: res.status, completed: res.status === 'delivered' } : d)));
      flash(`Order #${o.id} is now ${STATUS_LABELS[res.status].toLowerCase()}.`);
    } catch (e) {
      flash(e.message, 'error');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <div className="toolbar">
        <input className="search" type="search" placeholder="Search order no, product or address"
          value={q} onChange={(e) => setQ(e.target.value)} />
        <span className="muted small">{plural(visible.length, 'order')}</span>
      </div>
      <div className="chips pm__chips">
        {DELIVERY_FILTERS.map(([key, label]) => (
          <button key={key} className={`chip${filter === key ? ' active' : ''}`} onClick={() => setFilter(key)}>{label}</button>
        ))}
      </div>

      {visible.length === 0 ? (
        <div className="empty">{filter === 'open' ? 'Nothing to ship right now.' : 'No orders match.'}</div>
      ) : (
        <div className="pm-orders">
          {visible.map((o) => (
            <article key={o.id} className="pm-order">
              <header className="pm-order__head">
                <div>
                  <strong>Order #{o.id}</strong>
                  <span className={`status status--${o.status}`}>{STATUS_LABELS[o.status] ?? o.status}</span>
                </div>
                {NEXT_STATUS[o.status] && (
                  <button className="btn btn-dark pm-order__action" disabled={busy === o.id} onClick={() => advance(o)}>
                    {busy === o.id ? 'Updating…' : `${NEXT_ACTION[o.status]} →`}
                  </button>
                )}
              </header>
              <dl className="invoice-detail__meta pm-order__meta">
                <div><dt>Customer ID</dt><dd>#{o.customerId}</dd></div>
                <div><dt>Deliver to</dt><dd>{o.address || '—'}</dd></div>
                <div><dt>Order total</dt><dd>{money(o.total)}</dd></div>
              </dl>
              <table className="data-table data-table--compact">
                <thead>
                  <tr><th>Delivery</th><th>Product</th><th className="num">Qty</th><th className="num">Total</th></tr>
                </thead>
                <tbody>
                  {o.items.map((it) => (
                    <tr key={it.id}>
                      <td className="muted">#{it.id}{it.completed && <span className="badge badge-in pm-done">✓ Done</span>}</td>
                      <td><Link to={`/shop/${it.productId}`} className="underline">{it.productName}</Link></td>
                      <td className="num">{it.quantity}</td>
                      <td className="num">{money(it.totalPrice)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Comments ---------- */

const COMMENT_FILTERS = [
  ['pending', 'Pending'],
  ['approved', 'Approved'],
  ['rejected', 'Rejected'],
  ['all', 'All'],
];

function CommentsTab({ comments, setComments, flash }) {
  const [filter, setFilter] = useState('pending');
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(null);

  const counts = useMemo(() => {
    const out = { pending: 0, approved: 0, rejected: 0, all: comments.length };
    comments.forEach((c) => { out[commentState(c)] += 1; });
    return out;
  }, [comments]);

  const visible = useMemo(() => {
    const term = q.trim().toLowerCase();
    return comments.filter((c) =>
      (filter === 'all' || commentState(c) === filter) &&
      (!term || [c.text, c.productName, c.customerName].some((v) => v?.toLowerCase().includes(term))));
  }, [comments, filter, q]);

  const decide = async (c, approve) => {
    setBusy(c.id);
    try {
      const updated = await moderateComment(c.id, approve);
      setComments((list) => list.map((x) => (x.id === c.id ? updated : x)));
      flash(approve ? `Comment on ${c.productName} is now visible.` : `Comment on ${c.productName} was rejected.`);
    } catch (e) {
      flash(e.message, 'error');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <div className="toolbar">
        <input className="search" type="search" placeholder="Search comment, product or customer"
          value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="chips pm__chips">
        {COMMENT_FILTERS.map(([key, label]) => (
          <button key={key} className={`chip${filter === key ? ' active' : ''}`} onClick={() => setFilter(key)}>
            {label} ({counts[key]})
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <div className="empty">{filter === 'pending' ? 'No comments waiting for review.' : 'No comments match.'}</div>
      ) : (
        <ul className="pm-comments">
          {visible.map((c) => {
            const state = commentState(c);
            return (
              <li key={c.id} className={`pm-comment pm-comment--${state}`}>
                <div className="pm-comment__head">
                  <div>
                    <Link to={`/shop/${c.product_id}`} className="underline"><strong>{c.productName}</strong></Link>
                    <div className="muted small">{c.customerName} · {fmtDateTime(c.created_at)}</div>
                  </div>
                  <span className={`status ${state === 'approved' ? 'status--delivered' : state === 'rejected' ? 'status--cancelled' : 'status--in_transit'}`}>
                    {state}
                  </span>
                </div>
                <p className="pm-comment__text">{c.text}</p>
                <div className="pm-comment__foot">
                  <span className="muted small">{c.reviewed_at ? `Reviewed ${fmtDateTime(c.reviewed_at)}` : 'Not visible to customers yet'}</span>
                  <span className="pm-comment__actions">
                    {state !== 'rejected' && (
                      <button className="btn btn-ghost" disabled={busy === c.id} onClick={() => decide(c, false)}>Reject</button>
                    )}
                    {state !== 'approved' && (
                      <button className="btn btn-dark" disabled={busy === c.id} onClick={() => decide(c, true)}>Approve</button>
                    )}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
