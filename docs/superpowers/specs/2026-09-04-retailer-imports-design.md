# Retailer Imports and NFC Entry Points

## Context

Wardrowbe already manages garment images, wear history and individual wash
history. This fork adds a reliable way to bootstrap a personal wardrobe from
the authenticated, browser-visible Zalando owned-items page and Mango purchase
history. It also records the purchased size and fit feedback needed for later
fit analysis, and supplies a stable item URL for an NFC or QR hanger tag.

Retailer sessions, passwords and cookies are never saved by Wardrowbe. An
import is explicitly initiated by the signed-in user from data they can view in
their own browser.

## Scope

The first release provides:

- a source record for Zalando and Mango items;
- a reviewed import manifest that can be safely applied more than once;
- downloads of the product image to Wardrowbe-owned storage;
- import of title, brand, product URL, retailer product reference, colour,
  purchased size, price and purchase date when supplied;
- exclusion of Mango lines whose per-item status is `returned`;
- exclusion of Zalando categories classified as underwear/boxers or
  accessories;
- fields for a user to record fit result and fit notes later;
- a stable, authenticated item route for NFC/QR tags.

The release does not automate a logged-in retailer browser from the Wardrowbe
server, add Apple Watch software, or model multi-item laundry loads. Those can
be separate follow-up features once the individual item flow is proven.

## Data model

`clothing_items` receives nullable fields so existing wardrobes remain valid:

- `retailer`: `zalando` or `mango`;
- `retailer_product_id`: Zalando product slug/ID or Mango `REF.` value;
- `source_url`: original product URL;
- `purchased_size`: the retailer-displayed purchased size;
- `purchased_color`: the retailer-displayed colour;
- `return_status`: `kept` or `returned`;
- `fit_rating`: `too_small`, `slightly_small`, `fits`, `slightly_large`, or
  `too_large`;
- `fit_notes`: optional user-entered text;
- `imported_at`: timestamp.

For items with a retailer and product ID, a per-user unique constraint on
`(user_id, retailer, retailer_product_id, purchased_size, purchased_color)`
prevents a duplicate retained item when an import is repeated. The combination
allows intentional multiple copies of the same product where a colour or size
differs.

## Import flow

An importer receives a JSON manifest and a directory of already-downloaded
images. Each manifest line has a stable `source_key`, source metadata, local
image path and a classifier result. The service validates the manifest,
rejects images outside the provided import directory, skips excluded lines,
uploads the image through the existing image service, and creates or updates an
item within one transaction per manifest line.

The command reports `created`, `updated`, `skipped_returned`,
`skipped_category`, `duplicate`, and `failed` counts with a reason per failed
line. A failed line does not block later manifest entries. Repeating a manifest
must not create extra retained items.

The browser-side collector remains a local companion script. It scrolls the
currently authenticated web page, extracts only rendered item data and downloads
product images to the local import directory. It does not write retailer data
back, retain credentials, or depend on undocumented retailer APIs.

## NFC and QR entry

The frontend adds `/dashboard/items/[id]`. It verifies the existing Wardrowbe
session, fetches only the current user's item and renders its existing item
detail experience. An NFC tag or QR code uses this route with the item's UUID.
Unauthenticated visits follow the existing login flow and return to the item
route afterwards.

## Deployment and privacy

The fork keeps upstream Docker Compose services: frontend, backend, worker,
PostgreSQL and Redis. A deployment-specific `.env` remains untracked. Default
configuration sets `AI_INTERNAL_ENABLED=false`; no AI provider or external API
key is required for importing or operating the wardrobe.

Persistent database and image storage remain Docker named volumes. Home-server
migration is supported by pinning the fork image/tag, copying `.env`, restoring
a PostgreSQL backup, and copying the image-storage volume before starting the
same Compose stack. `NEXTAUTH_URL` changes to the new host URL.

## Error handling and verification

The backend returns clear validation errors for unsupported retailers, malformed
source URLs, unknown return/fit values, unsafe image paths and missing images.
Tests cover the database migration, importer idempotency, Mango returned-item
skipping, Zalando category skipping, item metadata update, item-route
authorization and the Compose health endpoint.
