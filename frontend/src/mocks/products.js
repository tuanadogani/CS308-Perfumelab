/**
 * Product data model (Requirement 9 — required fields + perfume-specific fields)
 *
 * Required:     id, name, model, serialNumber, description, stock, price,
 *               warrantyStatus, distributor
 * Extra fields: brand, category, gender, volumeMl, notes {top, heart, base},
 *               families, popularity, rating, color (used for the bottle illustration)
 *
 * If the backend team uses this exact schema, the frontend works without changes.
 */

export const CATEGORIES = [
  { id: 'eau-de-parfum', name: 'Eau de Parfum' },
  { id: 'eau-de-toilette', name: 'Eau de Toilette' },
  { id: 'extrait', name: 'Extrait de Parfum' },
  { id: 'cologne', name: 'Cologne' },
];

export const NOTE_FAMILIES = ['Woody', 'Floral', 'Oriental', 'Citrus', 'Spicy', 'Musky', 'Gourmand', 'Aromatic'];

export const products = [
  {
    id: 1, name: 'Nuit d’Ambre', brand: 'Maison Lumière', model: 'NA-100', serialNumber: 'ML-NA-2026-0001',
    description: 'Midnight amber, smoky incense and creamy vanilla in a warm embrace. Long-lasting and unforgettable.',
    category: 'eau-de-parfum', gender: 'Unisex', volumeMl: 100,
    notes: { top: ['Bergamot', 'Pink Pepper'], heart: ['Incense', 'Rose'], base: ['Amber', 'Vanilla', 'Labdanum'] },
    families: ['Oriental', 'Spicy'],
    stock: 12, price: 4850, warrantyStatus: 'Authenticity guaranteed — 2 years', distributor: 'Lumière Distribution Inc.',
    popularity: 98, rating: 4.8, color: '#b5651d',
  },
  {
    id: 2, name: 'Iris Poudré', brand: 'Atelier Verre', model: 'IP-75', serialNumber: 'AV-IP-2026-0102',
    description: 'Powdery orris root, suede and white musk. Quiet, elegant and close to the skin.',
    category: 'eau-de-parfum', gender: 'Women', volumeMl: 75,
    notes: { top: ['Pear', 'Aldehydes'], heart: ['Iris', 'Violet'], base: ['Suede', 'White Musk'] },
    families: ['Floral', 'Musky'],
    stock: 3, price: 3990, warrantyStatus: 'Authenticity guaranteed — 2 years', distributor: 'Verre Europe Ltd.',
    popularity: 87, rating: 4.6, color: '#b8a3c9',
  },
  {
    id: 3, name: 'Cèdre Noir', brand: 'Maison Lumière', model: 'CN-100', serialNumber: 'ML-CN-2026-0003',
    description: 'Atlas cedar, vetiver and leather. A sharp, modern and confident woody composition.',
    category: 'extrait', gender: 'Men', volumeMl: 100,
    notes: { top: ['Cardamom', 'Grapefruit'], heart: ['Cedar', 'Leather'], base: ['Vetiver', 'Patchouli'] },
    families: ['Woody', 'Spicy'],
    stock: 0, price: 6200, warrantyStatus: 'Authenticity guaranteed — 2 years', distributor: 'Lumière Distribution Inc.',
    popularity: 91, rating: 4.9, color: '#2f3a32',
  },
  {
    id: 4, name: 'Néroli Riviera', brand: 'Sol & Sel', model: 'NR-50', serialNumber: 'SS-NR-2026-0204',
    description: 'Orange blossom, sea salt and fresh lemon on the Mediterranean coast. A light, breezy summer scent.',
    category: 'eau-de-toilette', gender: 'Unisex', volumeMl: 50,
    notes: { top: ['Lemon', 'Mandarin'], heart: ['Neroli', 'Orange Blossom'], base: ['Sea Salt', 'Ambrette'] },
    families: ['Citrus', 'Floral'],
    stock: 25, price: 2450, warrantyStatus: 'Authenticity guaranteed — 1 year', distributor: 'Sol & Sel Parfums',
    popularity: 76, rating: 4.3, color: '#e8b04a',
  },
  {
    id: 5, name: 'Rose Velours', brand: 'Atelier Verre', model: 'RV-100', serialNumber: 'AV-RV-2026-0105',
    description: 'Velvety Turkish rose, raspberry and oud. A romantic yet dark interpretation.',
    category: 'extrait', gender: 'Women', volumeMl: 100,
    notes: { top: ['Raspberry', 'Saffron'], heart: ['Turkish Rose', 'Peony'], base: ['Oud', 'Patchouli'] },
    families: ['Floral', 'Oriental'],
    stock: 7, price: 5600, warrantyStatus: 'Authenticity guaranteed — 2 years', distributor: 'Verre Europe Ltd.',
    popularity: 94, rating: 4.7, color: '#8e2c3f',
  },
  {
    id: 6, name: 'Vétiver Frais', brand: 'Sol & Sel', model: 'VF-100', serialNumber: 'SS-VF-2026-0206',
    description: 'Freshly cut grass, Haitian vetiver and green pepper. A clean, energetic daytime scent.',
    category: 'cologne', gender: 'Men', volumeMl: 100,
    notes: { top: ['Green Pepper', 'Bergamot'], heart: ['Vetiver', 'Lavender'], base: ['Cedar', 'Musk'] },
    families: ['Aromatic', 'Woody'],
    stock: 18, price: 1950, warrantyStatus: 'Authenticity guaranteed — 1 year', distributor: 'Sol & Sel Parfums',
    popularity: 64, rating: 4.1, color: '#6f8b5a',
  },
  {
    id: 7, name: 'Vanille Fumée', brand: 'Maison Lumière', model: 'VF-50', serialNumber: 'ML-VF-2026-0007',
    description: 'Madagascar vanilla, tonka bean and a touch of smoke. Gourmand, but never sugary.',
    category: 'eau-de-parfum', gender: 'Unisex', volumeMl: 50,
    notes: { top: ['Rum', 'Cinnamon'], heart: ['Vanilla', 'Tonka'], base: ['Birch Tar', 'Benzoin'] },
    families: ['Gourmand', 'Oriental'],
    stock: 2, price: 3450, warrantyStatus: 'Authenticity guaranteed — 2 years', distributor: 'Lumière Distribution Inc.',
    popularity: 89, rating: 4.5, color: '#7a4a2a',
  },
  {
    id: 8, name: 'Musc Blanc', brand: 'Atelier Verre', model: 'MB-100', serialNumber: 'AV-MB-2026-0108',
    description: 'White musk, cotton flower and soft ambrette that smell like clean sheets. A true skin scent.',
    category: 'eau-de-toilette', gender: 'Unisex', volumeMl: 100,
    notes: { top: ['Aldehydes'], heart: ['Cotton Flower', 'Lily'], base: ['White Musk', 'Ambrette'] },
    families: ['Musky', 'Floral'],
    stock: 30, price: 2800, warrantyStatus: 'Authenticity guaranteed — 1 year', distributor: 'Verre Europe Ltd.',
    popularity: 71, rating: 4.4, color: '#c9c2b6',
  },
];
