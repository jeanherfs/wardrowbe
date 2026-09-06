#!/usr/bin/env bash

set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

cat > "$test_root/release.env" <<'EOF'
POSTGRES_PASSWORD=test-postgres-password
SECRET_KEY=test-secret-key-that-is-long-enough
NEXTAUTH_SECRET=test-nextauth-secret
LOCAL_AUTH_ENABLED=true
LOCAL_AUTH_BOOTSTRAP_TOKEN=test-bootstrap-token
EOF

config="$(cd "$repo_root" && docker compose --env-file "$test_root/release.env" -f docker-compose.release.yml config)"

grep -F 'published: "8080"' <<<"$config" >/dev/null
grep -F 'name: wardrobe_release_postgres' <<<"$config" >/dev/null
grep -F 'name: wardrobe_release_uploads' <<<"$config" >/dev/null
grep -F 'LOCAL_AUTH_ENABLED: "true"' <<<"$config" >/dev/null
grep -F "context: $repo_root/backend" <<<"$config" >/dev/null
grep -F "context: $repo_root/frontend" <<<"$config" >/dev/null

if grep -F 'published: "18000"' <<<"$config" >/dev/null; then
  printf 'release compose must not expose the backend directly\n' >&2
  exit 1
fi

if grep -F './backend:/app' <<<"$config" >/dev/null; then
  printf 'release compose must not include a development backend bind mount\n' >&2
  exit 1
fi
