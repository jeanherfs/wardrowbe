/** Return the stable identity used to deduplicate repeated lazy-loaded cards. */
export function identityKey(card) {
  const product = String(card.productId || card.retailer_product_id || card.ref || card.id || card.sourceUrl || card.href || card.imageUrl || '').trim();
  const size = String(card.size || '').trim();
  const color = String(card.color || '').trim();
  return `${product}|${size}|${color}`;
}

/** Preserve the first rendered card for each product/size/color identity. */
export function dedupeCards(cards) {
  const seen = new Set();
  return cards.filter((card) => {
    const key = identityKey(card);
    if (!key || key.startsWith('|')) return false;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/**
 * Keep reading a lazy-loaded retailer page while scrolling until it has
 * stopped yielding new identities for the configured number of passes.
 * `readCards` may return an array or `{ cards, atEnd }` when the page exposes
 * an authoritative end-of-list signal.
 */
export async function collectUntilSettled(readCards, scroll, options = {}) {
  const stablePasses = options.stablePasses ?? 2;
  const maxPasses = options.maxPasses ?? 100;
  const waitAfterScroll = options.waitAfterScroll ?? (async () => {});
  const all = [];
  const seen = new Set();
  let stable = 0;

  for (let pass = 0; pass < maxPasses; pass += 1) {
    const result = await readCards();
    const cards = Array.isArray(result) ? result : (result?.cards || []);
    const before = all.length;
    for (const card of cards) {
      const key = identityKey(card);
      if (!key || key.startsWith('|') || seen.has(key)) continue;
      seen.add(key);
      all.push(card);
    }

    if (all.length === before) stable += 1;
    else stable = 0;
    if (stable >= stablePasses || (result?.atEnd && all.length === before)) return all;
    await scroll();
    await waitAfterScroll();
  }

  return all;
}
