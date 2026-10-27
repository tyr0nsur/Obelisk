#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${1:-${FLOWARK_DASHBOARD_ENV:-}}"
default_env_file="/etc/flowark-dashboard/dashboard.env"

if [[ -n "$env_file" ]]; then
  echo "==> production env validation"
  "$repo_root/deploy/check-production-env.sh" "$env_file"
elif [[ -f "$default_env_file" ]]; then
  echo "==> production env validation"
  "$repo_root/deploy/check-production-env.sh" "$default_env_file"
else
  echo "==> production env validation skipped (set FLOWARK_DASHBOARD_ENV or pass an env file)"
fi

echo "==> server syntax and tests"
(
  cd "$repo_root/server"
  node --check server.js
  npm audit --omit=dev
  npm test
)

echo "==> client tests"
(
  cd "$repo_root/client"
  npm audit --omit=dev
  npm test
)

echo "==> client lint"
(
  cd "$repo_root/client"
  npm run lint
)

echo "==> client production build"
(
  cd "$repo_root/client"
  npm run build
)

echo "==> deploy template checks"
bash "$repo_root/deploy/check-deploy-templates.sh"

echo "production readiness checks passed"
