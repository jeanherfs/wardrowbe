#!/usr/bin/env bash

set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

grep -F 'pg_dump' "$repo_root/wardrobe" >/dev/null
grep -F 'pg_restore' "$repo_root/wardrobe" >/dev/null
grep -F 'uploads.tar' "$repo_root/wardrobe" >/dev/null
grep -F 'force-empty-target' "$repo_root/wardrobe" >/dev/null
