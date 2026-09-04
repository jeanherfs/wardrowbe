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

Run the command from the backend container:

```sh
python scripts/import_retailer_manifest.py --user-id <uuid> --manifest /imports/items.json --image-root /imports/images
```
