const SKIPPED_CATEGORIES = new Set(['accessories', 'accessory', 'underwear', 'boxers', 'boxershorts']);

/**
 * Return the image-edit brief used by the Wardrowbe import workflow.
 * This is deliberately provider-neutral: an agent or an image-edit provider
 * can execute the brief without coupling the collector to credentials.
 */
export function buildOptimizationPrompt(item = {}) {
  const product = item.name || 'wardrobe item';
  return [
    'Use case: precise-object-edit.',
    `Edit this ${product} into a consistent Wardrowbe catalog image.`,
    'Keep the exact product, real color, cut, material, seams, closures, logos, and graphics unchanged.',
    'Center the single product fully in frame with even margins on a clean light gray-white studio background and soft diffuse lighting.',
    'Remove every human or model body part, face, hands, feet, hanger, props, packaging, other garments, watermark, and overlay text.',
    'Do not invent or alter the product design. Preserve a complete purchasable pair when the product itself is a pair.',
    'Output one square product image.',
  ].join(' ');
}

/** Select only retained clothing images for the optimization stage. */
export function optimizationTargets(items) {
  return items.filter((item) => {
    const category = String(item.category || 'clothing').trim().toLowerCase();
    return item.return_status !== 'returned' && !SKIPPED_CATEGORIES.has(category) && Boolean(item.image_path);
  });
}
