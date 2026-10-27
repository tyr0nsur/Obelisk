#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${1:-${FLOWARK_DASHBOARD_ENV:-/etc/flowark-dashboard/dashboard.env}}"
app_name="${FLOWARK_PM2_APP_NAME:-ark-dashboard}"
ecosystem_file="$repo_root/deploy/pm2/ecosystem.config.cjs"
expected_script="$repo_root/server/server.js"
dry_run="${FLOWARK_PM2_DRY_RUN:-0}"
health_url="${FLOWARK_DASHBOARD_HEALTH_URL:-}"
health_retries="${FLOWARK_PM2_HEALTH_RETRIES:-15}"
health_retry_delay="${FLOWARK_PM2_HEALTH_RETRY_DELAY:-2}"

if [[ "$dry_run" != "1" ]] && ! command -v pm2 >/dev/null 2>&1; then
  echo "pm2 is not installed or not in PATH" >&2
  exit 1
fi

"$repo_root/deploy/check-production-env.sh" "$env_file"

while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="${raw_line#"${raw_line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
  key="${line%%=*}"
  value="${line#*=}"
  key="${key%"${key##*[![:space:]]}"}"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
    echo "invalid env key after validation: $key" >&2
    exit 1
  fi
  export "$key=$value"
done < "$env_file"

if [[ "$dry_run" == "1" ]]; then
  echo "pm2 env load verified: $env_file"
  exit 0
fi

if [[ ! "$health_retries" =~ ^[0-9]+$ ]] || (( health_retries < 1 || health_retries > 120 )); then
  echo "FLOWARK_PM2_HEALTH_RETRIES must be an integer between 1 and 120" >&2
  exit 1
fi

if [[ ! "$health_retry_delay" =~ ^[0-9]+$ ]] || (( health_retry_delay < 1 || health_retry_delay > 30 )); then
  echo "FLOWARK_PM2_HEALTH_RETRY_DELAY must be an integer between 1 and 30" >&2
  exit 1
fi

if [[ ! -f "$repo_root/client/dist/index.html" ]]; then
  echo "client/dist/index.html is missing; run npm run build in client first" >&2
  exit 1
fi

if [[ "$app_name" != "ark-dashboard" ]]; then
  echo "FLOWARK_PM2_APP_NAME must remain ark-dashboard for this ecosystem file" >&2
  exit 1
fi

existing_script="$(pm2 jlist | node -e "
const fs = require('node:fs');
const apps = JSON.parse(fs.readFileSync(0, 'utf8'));
const app = apps.find(entry => entry.name === process.argv[1]);
process.stdout.write(app?.pm2_env?.pm_exec_path || '');
" "$app_name")"

if [[ -n "$existing_script" && "$(realpath -m "$existing_script")" != "$(realpath -m "$expected_script")" ]]; then
  echo "replacing existing PM2 app '$app_name' launched from $existing_script with $expected_script"
  pm2 delete "$app_name" >/dev/null
fi

pm2 startOrReload "$ecosystem_file" --only "$app_name" --update-env

if [[ -z "$health_url" ]]; then
  health_url="http://${HOST:-127.0.0.1}:${PORT:-3040}/healthz"
fi

for ((attempt = 1; attempt <= health_retries; attempt += 1)); do
  if "$repo_root/deploy/check-dashboard-health.sh" "$health_url"; then
    exit 0
  fi
  if (( attempt == health_retries )); then
    echo "PM2 app '$app_name' did not pass dashboard healthcheck after $health_retries attempts: $health_url" >&2
    pm2 status "$app_name" >&2 || true
    exit 1
  fi
  sleep "$health_retry_delay"
done
