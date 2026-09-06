#!/usr/bin/env bash

set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

assert_contains() {
  local expected="$1"
  local actual="$2"

  if [[ "$actual" != *"$expected"* ]]; then
    printf 'expected output to contain: %s\nactual output:\n%s\n' "$expected" "$actual" >&2
    exit 1
  fi
}

help_output="$(cd "$repo_root" && ./wardrobe)"
assert_contains 'Usage: ./wardrobe <command>' "$help_output"
assert_contains 'up' "$help_output"
assert_contains 'import' "$help_output"

mkdir -p "$test_root/bin"
cat > "$test_root/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$*" >> "${WARDROBE_TEST_DOCKER_LOG:?}"

if [[ "$1" == "info" ]]; then
  exit 0
fi

if [[ "$1" == "compose" && "$*" == *"ps"* ]]; then
  exit 0
fi
EOF
chmod +x "$test_root/bin/docker"

cat > "$test_root/bin/curl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${WARDROBE_TEST_CURL_LOG:?}"
exit 0
EOF
chmod +x "$test_root/bin/curl"

export PATH="$test_root/bin:$PATH"
export WARDROBE_TEST_DOCKER_LOG="$test_root/docker.log"
export WARDROBE_TEST_CURL_LOG="$test_root/curl.log"

cd "$repo_root"
./wardrobe up --no-build

docker_calls="$(<"$WARDROBE_TEST_DOCKER_LOG")"
assert_contains 'info' "$docker_calls"
assert_contains 'compose -f docker-compose.yml -f docker-compose.dev.yml up -d' "$docker_calls"
assert_contains 'compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend alembic upgrade head' "$docker_calls"
curl_calls="$(<"$WARDROBE_TEST_CURL_LOG")"
assert_contains 'http://localhost:8000/api/v1/health' "$curl_calls"
assert_contains 'http://localhost:3000' "$curl_calls"

mkdir -p "$test_root/images"
printf '[]\n' > "$test_root/items.json"
printf 'image' > "$test_root/images/shirt.jpg"
: > "$WARDROBE_TEST_DOCKER_LOG"

./wardrobe import \
  --user-id 00000000-0000-0000-0000-000000000001 \
  --manifest "$test_root/items.json" \
  --image-root "$test_root/images"

docker_calls="$(<"$WARDROBE_TEST_DOCKER_LOG")"
assert_contains 'run --rm --no-deps' "$docker_calls"
assert_contains '/imports/manifest/items.json' "$docker_calls"
assert_contains '--image-root /imports/images' "$docker_calls"
