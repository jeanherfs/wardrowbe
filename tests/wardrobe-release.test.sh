#!/usr/bin/env bash

set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT

help_output="$(cd "$repo_root" && ./wardrobe release)"
[[ "$help_output" == *"./wardrobe release <command>"* ]]
[[ "$help_output" == *"bootstrap"* ]]
[[ "$help_output" == *"backup"* ]]

mkdir -p "$test_root/bin"
cat > "$test_root/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
printf '%s\n' "$*" >> "${WARDROBE_TEST_DOCKER_LOG:?}"
if [[ "$1" == "info" ]]; then exit 0; fi
EOF
chmod +x "$test_root/bin/docker"

export PATH="$test_root/bin:$PATH"
export WARDROBE_TEST_DOCKER_LOG="$test_root/docker.log"
export WARDROBE_RELEASE_ENV="$test_root/.env.release"

cd "$repo_root"
./wardrobe release status

test "$(stat -f '%Lp' "$WARDROBE_RELEASE_ENV" 2>/dev/null || stat -c '%a' "$WARDROBE_RELEASE_ENV")" = "600"
grep -F 'LOCAL_AUTH_ENABLED=true' "$WARDROBE_RELEASE_ENV" >/dev/null
grep -F 'compose --env-file ' "$WARDROBE_TEST_DOCKER_LOG" >/dev/null
grep -F 'docker-compose.release.yml ps' "$WARDROBE_TEST_DOCKER_LOG" >/dev/null
