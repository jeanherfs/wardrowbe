export function collectMangoPurchases(purchases) {
  return purchases.map((purchase) => ({
    retailer: 'mango',
    retailer_product_id: String(purchase.ref || purchase.productId),
    image_path: purchase.imagePath || '',
    category: purchase.category || 'clothing',
    name: purchase.name || purchase.title || '',
    brand: 'Mango',
    source_url: purchase.sourceUrl,
    purchased_size: purchase.size || '',
    purchased_color: purchase.color || '',
    return_status: purchase.returned === true || purchase.returnLabel === 'Teruggekeerd' ? 'returned' : 'kept',
    purchase_date: purchase.purchaseDate,
  }));
}
