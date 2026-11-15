// Prefer shared scent families and notes, then a similar price.
export function recommendProducts(product, products, excludedIds = [], limit = 4) {
  const notes = new Set(Object.values(product.notes ?? {}).flat().map((note) => note.toLowerCase()));
  const score = (candidate) => {
    const families = (candidate.families ?? []).filter((family) => product.families?.includes(family)).length;
    const sharedNotes = Object.values(candidate.notes ?? {}).flat().filter((note) => notes.has(note.toLowerCase())).length;
    const priceDistance = Math.abs(candidate.price - product.price) / Math.max(product.price, 1);
    return families * 5 + sharedNotes * 2 + 1 / (1 + priceDistance);
  };
  return products
    .filter((candidate) => candidate.id !== product.id && candidate.stock > 0 && !excludedIds.includes(candidate.id))
    .sort((a, b) => score(b) - score(a) || (b.popularity ?? 0) - (a.popularity ?? 0))
    .slice(0, limit);
}
