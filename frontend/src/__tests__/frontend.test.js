import { describe, it, expect } from 'vitest';
import { cartReducer, initialCart, cartCount, cartTotal } from '../context/cartReducer';
import { filterAndSort } from '../api/productApi';
import { validateRegister } from '../utils/validation';
import { products } from '../mocks/products';

const p = (over = {}) => ({ id: 1, name: 'Test', brand: 'B', price: 100, stock: 3, volumeMl: 50, color: '#000', ...over });

describe('cartReducer', () => {
  it('adds an in-stock product to the cart', () => {
    const s = cartReducer(initialCart, { type: 'ADD', product: p() });
    expect(s.items).toHaveLength(1);
    expect(s.items[0].quantity).toBe(1);
  });
  it('does not add an out-of-stock product', () => {
    const s = cartReducer(initialCart, { type: 'ADD', product: p({ stock: 0 }) });
    expect(s.items).toHaveLength(0);
  });
  it('increases quantity when the same product is added again', () => {
    let s = cartReducer(initialCart, { type: 'ADD', product: p() });
    s = cartReducer(s, { type: 'ADD', product: p() });
    expect(s.items[0].quantity).toBe(2);
  });
  it('never exceeds available stock', () => {
    const s = cartReducer(initialCart, { type: 'ADD', product: p(), quantity: 10 });
    expect(s.items[0].quantity).toBe(3);
  });
  it('SET_QTY to 0 removes the item', () => {
    let s = cartReducer(initialCart, { type: 'ADD', product: p() });
    s = cartReducer(s, { type: 'SET_QTY', productId: 1, quantity: 0 });
    expect(s.items).toHaveLength(0);
  });
  it('SET_QTY is clamped to stock', () => {
    let s = cartReducer(initialCart, { type: 'ADD', product: p() });
    s = cartReducer(s, { type: 'SET_QTY', productId: 1, quantity: 99 });
    expect(s.items[0].quantity).toBe(3);
  });
  it('computes total count and price', () => {
    let s = cartReducer(initialCart, { type: 'ADD', product: p(), quantity: 2 });
    s = cartReducer(s, { type: 'ADD', product: p({ id: 2, price: 50 }) });
    expect(cartCount(s.items)).toBe(3);
    expect(cartTotal(s.items)).toBe(250);
  });
});

describe('filterAndSort', () => {
  it('searches by name', () => {
    expect(filterAndSort(products, { q: 'iris' }).map((x) => x.id)).toContain(2);
  });
  it('searches by description', () => {
    expect(filterAndSort(products, { q: 'sea salt' }).map((x) => x.id)).toContain(4);
  });
  it('still returns out-of-stock products in search', () => {
    expect(filterAndSort(products, { q: 'cèdre' }).some((x) => x.stock === 0)).toBe(true);
  });
  it('sorts by price ascending', () => {
    const prices = filterAndSort(products, { sort: 'price_asc' }).map((x) => x.price);
    expect(prices).toEqual([...prices].sort((a, b) => a - b));
  });
  it('filters by a single scent family', () => {
    expect(filterAndSort(products, { family: ['Woody'] }).every((x) => x.families.includes('Woody'))).toBe(true);
  });
  it('requires every selected scent family', () => {
    const ids = filterAndSort(products, { family: ['Woody', 'Spicy'] }).map((x) => x.id);
    expect(ids).toEqual(expect.arrayContaining([3]));
    expect(filterAndSort(products, { family: ['Woody', 'Spicy'] })
      .every((x) => x.families.includes('Woody') && x.families.includes('Spicy'))).toBe(true);
    expect(ids.length).toBeLessThan(filterAndSort(products, { family: ['Woody'] }).length);
  });
  it('filters by category', () => {
    expect(filterAndSort(products, { category: 'extrait' }).every((x) => x.category === 'extrait')).toBe(true);
  });
});

describe('validateRegister', () => {
  const ok = { name: 'John Doe', email: 'a@b.com', taxId: '12345678901', homeAddress: 'Tuzla, Istanbul 34956', password: 'Strong123', confirm: 'Strong123' };
  it('accepts a valid form', () => expect(validateRegister(ok)).toEqual({}));
  it('rejects a weak password', () => expect(validateRegister({ ...ok, password: 'abc', confirm: 'abc' }).password).toBeDefined());
  it('catches mismatched passwords', () => expect(validateRegister({ ...ok, confirm: 'X' }).confirm).toBeDefined());
});

describe('product model (Requirement 9)', () => {
  const required = ['id', 'name', 'model', 'serialNumber', 'description', 'stock', 'price', 'warrantyStatus', 'distributor'];
  it('every product has the required fields', () => {
    products.forEach((prod) => required.forEach((f) => expect(prod).toHaveProperty(f)));
  });
});
