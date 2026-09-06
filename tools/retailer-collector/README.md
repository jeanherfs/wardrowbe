# Retailer collector format

Create a JSON array matching `manifest.schema.json` and put downloaded product
images beneath one local image directory. The importer only accepts an image
path within that directory and never stores browser cookies or login data.

For Zalando, collect brand, title, size, product link, product ID from the link,
and the visible image. Classify `boxers`, `boxershorts`, `underwear`, and
`accessories` as the category so the importer skips them.

For Mango purchase details, use the visible `REF.` as `retailer_product_id`, the
displayed size and colour, purchase date and product link. Map a visible
`Teruggekeerd` label to `return_status: "returned"`; those entries are skipped.

## Lazy loading and image optimization

Retailer pages are lazy-loaded. Read the rendered cards, scroll to the bottom,
wait for new cards, and repeat until two consecutive bottom checks add no new
`retailer_product_id + purchased_size + purchased_color` identities. Do not use
the number of DOM nodes as the count: some pages render the same card twice.
`collect_all.mjs` provides the tested `collectUntilSettled` and identity helpers;
the retailer-specific mappers deduplicate with the same key.

After collection, run retained clothing images through an image-edit provider
using `optimize_images.mjs`'s `buildOptimizationPrompt`. The edit must center
one product on a square light background, remove people and props, and preserve
the product design. Keep source downloads untouched, write optimized copies
beside them, and only replace the Wardrowbe upload after reviewing the outputs.
`optimizationTargets` automatically excludes returned Mango records, Zalando
accessories, underwear, boxers and socks. The optimizer is provider-neutral and
does not store retailer credentials or API keys.

Run the command from the backend container:

```sh
python scripts/import_retailer_manifest.py --user-id <uuid> --manifest /imports/items.json --image-root /imports/images
```
