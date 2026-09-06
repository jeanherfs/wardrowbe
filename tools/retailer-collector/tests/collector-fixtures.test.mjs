import test from 'node:test';
import assert from 'node:assert/strict';

import { collectZalandoCards, classifyZalandoCategory } from '../collect_zalando.mjs';
import { collectMangoPurchases } from '../collect_mango.mjs';

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
