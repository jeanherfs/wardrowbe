import { dedupeCards } from './collect_all.mjs';

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
