# Local Release, Password Login, and Retailer Bootstrap

## Context

This fork must run as a realistic local release before it moves to a home
server. It needs one personal account, an independently persistent data store,
and a safe way to import the user's browser-visible Zalando and Mango history.
The existing stack supports OIDC and a development-only passwordless provider;
it has no credentials model suitable for a release deployment.

## Goals

- run a release stack from the fork at `http://localhost:8080` without changing
  the existing development stack at port 3000;
- create and authenticate `mail@jeanherfs.nl` using an initial temporary
  password that is stored only as a password hash;
- make the complete wardrobe transferable to a home server, including database,
  item images, configuration and migrations;
- import the user's authenticated, browser-visible Zalando owned items and
  Mango purchases into that release account;
- retain product identity, purchased size and colour, source URL, purchase date
  and Mango return state while skipping returns, underwear and accessories;
- preserve the existing OIDC integration and the development-only provider.

## Non-goals

- no retailer credentials, cookies, session storage, or hidden/private retailer
  APIs are saved or called by Wardrowbe;
- no public registration, password reset email, multi-factor authentication, or
  account administration UI in this release;
- no automatic transfer to the home server. The release provides documented
  backup and restore artifacts so that move remains explicit and reversible.

## Release topology and portability

`docker-compose.release.yml` defines a dedicated Compose project named
`wardrobe-release`. It builds the backend and production frontend from this
fork, exposes only Nginx at `127.0.0.1:8080`, and uses distinct named volumes:

- `wardrobe-release-postgres` for PostgreSQL;
- `wardrobe-release-uploads` for Wardrowbe-owned images;
- `wardrobe-release-redis` for transient queue data.

`./wardrobe release up` creates an ignored `.env.release` if absent, containing
generated database, JWT and NextAuth secrets plus `LOCAL_AUTH_ENABLED=true`.
It applies migrations and can bootstrap an explicitly supplied account. It
never writes a plaintext account password into `.env.release`, the database,
logs, docs, tests, or Git. The caller receives the generated temporary password
once on standard output and must change it after signing in.

`./wardrobe release backup <directory>` writes a PostgreSQL custom-format dump,
an archive of the uploads volume, and a copy of the non-secret deployment
template. `./wardrobe release restore <directory>` restores them into an empty
release project. The home-server move uses these same commands after updating
the host URL and, optionally, switching to OIDC.

## Local password authentication

The `users` model gains a nullable `password_hash` field. It is populated only
for local-password users and is encoded with Argon2id using the maintained
`pwdlib` password-hash API. OIDC and development users retain a null hash and
their current behavior.

The backend exposes a rate-limited local-login endpoint only when
`LOCAL_AUTH_ENABLED=true`. It verifies the submitted email/password and returns
the same stable identity payload consumed by NextAuth. It responds uniformly to
unknown emails and invalid passwords. The frontend adds a `local-credentials`
provider only when that release setting is present; the login page renders an
email and password form for it. The normal sync endpoint accepts this provider
as a trusted local identity only when local auth is enabled, and keeps the
existing OIDC token verification unchanged.

A narrow bootstrap command creates the initial user if absent or replaces its
password only when the operator explicitly requests that action. Its external
ID is a generated stable UUID, so moving later to OIDC can safely migrate the
same user by verified email.

## Retailer bootstrap flow

The existing manifest importer remains the only writer to Wardrowbe data. A
local collector runs against the user-authenticated browser tabs and collects
only rendered product data:

1. Zalando: scroll until lazy-loaded item cards are exhausted; record product
   title, brand, visible size, product URL/product ID and product image.
2. Mango: enumerate purchase detail views; record product title, `REF.`, size,
   colour, purchase date, product URL and item-specific return status. Entries
   labelled `Teruggekeerd` are emitted as `returned` and skipped by import.
3. Download product images into a local staging directory, generate one
   reviewable JSON manifest per retailer, then run `./wardrobe release import`
   against the release account.

The command mounts only that manifest and its image directory read-only into
the importer container. The importer remains idempotent on the existing
retailer identity constraint. Browser data collection never includes delivery
addresses, payment details, session tokens, or other account information not
needed to catalog a garment.

## Error handling and safety

- Release startup stops on invalid configuration, a non-ready database, failed
  migrations, or unavailable local frontend/backend health endpoints.
- Bootstrap refuses an existing user unless `--reset-password` is explicit.
- Password verification and login are rate limited; hashes are never returned
  through APIs or logs.
- Collector pages that cannot be parsed are reported by order/item reference
  without copying unrelated personal data. One failed item does not block later
  records.
- The release `import` command validates that the user exists in the release
  database before performing any image writes.

## Verification

- backend unit tests cover local credential hashing, invalid credentials,
  disabled local auth, bootstrap idempotency and password-reset refusal;
- frontend tests cover provider selection and local login form submission;
- shell tests cover release compose selection, secret-file permissions,
  backup/restore command validation, and release importer targeting;
- integration verification creates a release user, signs in at port 8080,
  imports small Zalando/Mango fixtures, repeats the import, and confirms only
  retained expected items and their size metadata exist;
- release startup verifies `GET /api/v1/health` and `GET /` before printing the
  ready URL.
