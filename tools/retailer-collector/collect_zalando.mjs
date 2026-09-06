import { dedupeCards, identityKey } from './collect_all.mjs';

const EXCLUDED_ACCESSORY_WORDS = ['accessor', 'accessoire', 'belt', 'bag', 'bril', 'hoed', 'jewellery', 'jewelry', 'pet', 'portemonnee', 'riem', 'scarf', 'sjaal', 'tas', 'wallet', 'zonnebril'];
const EXCLUDED_UNDERWEAR_WORDS = ['underwear', 'boxer', 'boxershort', 'brief', 'lingerie', 'ondergoed', 'socks'];

export function classifyZalandoCategory(card) {
  const text = [card.category, card.name, card.title].filter(Boolean).join(' ').toLowerCase();
  if (EXCLUDED_UNDERWEAR_WORDS.some((word) => text.includes(word))) return 'underwear';
  if (EXCLUDED_ACCESSORY_WORDS.some((word) => text.includes(word))) return 'accessories';
  return String(card.category || 'clothing').trim().toLowerCase();
}

export function collectZalandoCards(cards) {
  return dedupeCards(cards).map((card) => ({
    retailer: 'zalando',
    retailer_product_id: String(card.productId || card.id || card.sourceUrl || card.imageUrl),
    image_path: card.imagePath || '',
    category: classifyZalandoCategory(card),
    name: card.name || card.title || '',
    brand: card.brand || '',
    source_url: card.sourceUrl,
    purchased_size: card.size || '',
    purchased_color: card.color || '',
    return_status: 'kept',
  }));
}

function productIdFromUrl(sourceUrl) {
  if (!sourceUrl) return '';
  try {
    const slug = new URL(sourceUrl).pathname.split('/').filter(Boolean).pop() || '';
    return slug.replace(/\.html?$/i, '').slice(0, 100);
  } catch {
    return String(sourceUrl).slice(0, 100);
  }
}

/** Map rows collected from Zalando's year-filtered order history. */
export function collectZalandoOrders(rows) {
  const mapped = rows.map((row) => ({
    ...row,
    productId: row.productId || productIdFromUrl(row.sourceUrl),
  }));
  const byIdentity = new Map();
  for (const row of mapped) {
    const key = identityKey(row);
    if (!key || key.startsWith('|')) continue;
    const existing = byIdentity.get(key);
    // A kept purchase wins if the same product/size also appears in a returned order.
    if (!existing || (existing.returned && !row.returned)) byIdentity.set(key, row);
  }
  return [...byIdentity.values()].map((row) => ({
    retailer: 'zalando',
    retailer_product_id: String(row.productId),
    image_path: row.imagePath || '',
    category: classifyZalandoCategory(row),
    name: row.name || row.title || '',
    brand: row.brand || '',
    source_url: row.sourceUrl,
    purchased_size: row.size || null,
    purchased_color: row.color || null,
    return_status: row.returned ? 'returned' : 'kept',
    purchase_date: row.purchaseDate || undefined,
  }));
}
