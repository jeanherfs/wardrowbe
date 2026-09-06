import test from 'node:test';
import assert from 'node:assert/strict';

import { collectZalandoCards, collectZalandoOrders, classifyZalandoCategory } from '../collect_zalando.mjs';
import { collectMangoPurchases } from '../collect_mango.mjs';
import { collectUntilSettled, identityKey } from '../collect_all.mjs';
import { buildOptimizationPrompt, optimizationTargets } from '../optimize_images.mjs';

test('classifies excluded Zalando categories from visible card text', () => {
  assert.equal(classifyZalandoCategory({ name: 'Logo boxer shorts', category: 'Underwear' }), 'underwear');
  assert.equal(classifyZalandoCategory({ name: 'Leather belt', category: 'Accessories' }), 'accessories');
  assert.equal(classifyZalandoCategory({ name: 'GOON UNISEX - Zonnebril - brown' }), 'accessories');
  assert.equal(classifyZalandoCategory({ name: 'Oxford shirt', category: 'Shirts' }), 'shirts');
});

test('maps Zalando cards and preserves duplicate size/color identities', () => {
  const rows = collectZalandoCards([
    {
      productId: 'shirt-1',
      name: 'Oxford shirt',
      brand: 'Example',
      size: 'M',
      color: 'Blue',
      category: 'Shirts',
      sourceUrl: 'https://www.zalando.nl/example-shirt-1.html',
      imageUrl: 'https://img.example/shirt-1.jpg',
    },
    {
      productId: 'boxer-1',
      name: 'Logo boxer shorts',
      brand: 'Example',
      size: 'M',
      category: 'Underwear',
      sourceUrl: 'https://www.zalando.nl/example-boxer-1.html',
      imageUrl: 'https://img.example/boxer-1.jpg',
    },
  ]);

  assert.equal(rows.length, 2);
  assert.equal(rows[0].retailer, 'zalando');
  assert.equal(rows[0].retailer_product_id, 'shirt-1');
  assert.equal(rows[0].purchased_size, 'M');
  assert.equal(rows[1].category, 'underwear');
});

test('maps Zalando order-history rows and preserves return status', () => {
  const rows = collectZalandoOrders([
    {
      sourceUrl: 'https://www.zalando.nl/example-shirt-1.html',
      imageUrl: 'https://img.example/shirt-1.jpg',
      brand: 'Example',
      name: 'Oxford shirt',
      size: 'M',
      returned: false,
      purchaseDate: '2026-06-11',
    },
    {
      sourceUrl: 'https://www.zalando.nl/example-shirt-1.html',
      imageUrl: 'https://img.example/shirt-1.jpg',
      brand: 'Example',
      name: 'Oxford shirt',
      size: 'M',
      returned: true,
      purchaseDate: '2026-06-11',
    },
  ]);

  assert.equal(rows.length, 1);
  assert.equal(rows[0].retailer_product_id, 'example-shirt-1');
  assert.equal(rows[0].return_status, 'kept');
  assert.equal(rows[0].purchase_date, '2026-06-11');
});

test('maps Mango returned labels and retained purchases', () => {
  const rows = collectMangoPurchases([
    {
      ref: '77040327',
      name: 'Cotton overshirt',
      size: 'L',
      color: 'Dark blue',
      sourceUrl: 'https://shop.mango.com/nl/item/77040327',
      imageUrl: 'https://img.example/mango-shirt.jpg',
      purchaseDate: '2026-08-30',
      returned: false,
    },
    {
      ref: '77040328',
      name: 'Returned trousers',
      size: 'M',
      sourceUrl: 'https://shop.mango.com/nl/item/77040328',
      imageUrl: 'https://img.example/mango-trousers.jpg',
      purchaseDate: '2026-08-30',
      returnLabel: 'Teruggekeerd',
    },
  ]);

  assert.deepEqual(rows.map((row) => row.return_status), ['kept', 'returned']);
  assert.equal(rows[0].purchased_color, 'Dark blue');
  assert.equal(rows[1].retailer_product_id, '77040328');
});

test('deduplicates repeated retailer cards by product, size, and color', () => {
  const repeated = { productId: 'shirt-1', size: 'M', color: 'Blue', sourceUrl: 'https://example/shirt-1' };
  assert.equal(identityKey(repeated), 'shirt-1|M|Blue');
  assert.deepEqual(
    collectZalandoCards([repeated, { ...repeated }, { ...repeated, color: 'Red' }]).map((row) => row.purchased_color),
    ['Blue', 'Red'],
  );
  assert.match(collectZalandoCards([{ imageUrl: 'https://img.example/unavailable.jpg', name: 'Chino' }])[0].retailer_product_id, /unavailable/);
  const mangoRows = collectMangoPurchases([
    { ref: 'mango-1', sourceUrl: 'https://example/mango-1', size: 'S', color: 'Blue' },
    { ref: 'mango-1', sourceUrl: 'https://example/mango-1', size: 'M', color: 'Blue' },
    { ref: 'mango-1', sourceUrl: 'https://example/mango-1', size: 'S', color: 'Blue' },
  ]);
  assert.deepEqual(mangoRows.map((row) => row.purchased_size), ['S', 'M']);
});

test('collects pages until two consecutive scrolls add no new identities', async () => {
  const pages = [
    [{ productId: 'a' }, { productId: 'b' }],
    [{ productId: 'a' }, { productId: 'b' }, { productId: 'c' }],
    [{ productId: 'a' }, { productId: 'b' }, { productId: 'c' }],
    [{ productId: 'a' }, { productId: 'b' }, { productId: 'c' }],
  ];
  let reads = 0;
  let scrolls = 0;
  const cards = await collectUntilSettled(
    async () => pages[Math.min(reads++, pages.length - 1)],
    async () => { scrolls += 1; },
    { stablePasses: 2, maxPasses: 10 },
  );
  assert.deepEqual(cards.map((card) => card.productId), ['a', 'b', 'c']);
  assert.equal(scrolls, 3);
});

test('waits after each scroll so delayed lazy-load requests can settle', async () => {
  let reads = 0;
  let waits = 0;
  const pages = [[{ productId: 'a' }], [{ productId: 'a' }, { productId: 'b' }], [{ productId: 'a' }, { productId: 'b' }]];
  const cards = await collectUntilSettled(
    async () => pages[Math.min(reads++, pages.length - 1)],
    async () => {},
    { stablePasses: 1, waitAfterScroll: async () => { waits += 1; } },
  );
  assert.deepEqual(cards.map((card) => card.productId), ['a', 'b']);
  assert.equal(waits, 2);
});

test('builds a conservative catalog-image optimization prompt', () => {
  const prompt = buildOptimizationPrompt({ name: 'Studio shirt', category: 'clothing' });
  assert.match(prompt, /center/i);
  assert.match(prompt, /single product/i);
  assert.match(prompt, /human|model/i);
  assert.match(prompt, /preserve|unchanged/i);
});

test('optimization targets exclude returns and skipped categories', () => {
  const targets = optimizationTargets([
    { retailer: 'mango', return_status: 'returned', category: 'clothing' },
    { retailer: 'zalando', return_status: 'kept', category: 'accessories' },
    { retailer: 'zalando', return_status: 'kept', category: 'clothing', image_path: 'shirt.jpg' },
  ]);
  assert.deepEqual(targets.map((item) => item.image_path), ['shirt.jpg']);
});
