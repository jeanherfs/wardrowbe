#!/usr/bin/env bash

set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dockerfile="$repo_root/frontend/Dockerfile.dev"

if ! rg --fixed-strings 'RUN npm ci' "$dockerfile" >/dev/null; then
  printf 'expected the development image to install dependencies with npm ci\n' >&2
  exit 1
fi

if ! rg --fixed-strings 'CMD npm ci && npm run dev' "$dockerfile" >/dev/null; then
  printf 'expected the development container to reset dependencies with npm ci\n' >&2
  exit 1
fi
