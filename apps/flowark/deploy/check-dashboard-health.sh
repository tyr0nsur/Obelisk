#!/usr/bin/env bash
set -euo pipefail

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
headers="$tmp_dir/headers"
body_file="$tmp_dir/body"

origin_from_url() {
  node -e "const u = new URL(process.argv[1]); console.log(u.origin)" "$1"
}

health_url_from_target() {
  node -e "
const u = new URL(process.argv[1]);
const path = u.pathname.replace(/\/+$/, '') || '/';
if (path === '/') {
  u.pathname = '/healthz';
  u.search = '';
  u.hash = '';
}
console.log(u.toString());
" "$1"
}

check_url() {
  local url="$1"

  curl --fail --silent --show-error --max-time 5 --dump-header "$headers" --output "$body_file" "$url"
  local body
  body="$(cat "$body_file")"
  case "$body" in
    *'"status":"ok"'*) ;;
    *)
      echo "unexpected healthcheck response from $url: $body" >&2
      exit 1
      ;;
  esac

  if grep -iq '^set-cookie:' "$headers"; then
    echo "healthcheck must not set cookies: $url" >&2
    exit 1
  fi

  if ! grep -iq '^cache-control:.*no-store' "$headers"; then
    echo "healthcheck must set Cache-Control: no-store: $url" >&2
    exit 1
  fi

  if ! grep -iq '^content-type: application/json' "$headers"; then
    echo "healthcheck must return application/json: $url" >&2
    exit 1
  fi

  if ! grep -iq '^x-robots-tag:.*noindex.*nofollow.*noarchive' "$headers"; then
    echo "healthcheck must set X-Robots-Tag noindex/nofollow/noarchive: $url" >&2
    exit 1
  fi

  if ! grep -Eiq '^x-request-id: [A-Za-z0-9._:-]{8,128}' "$headers"; then
    echo "healthcheck must include a sane X-Request-Id header: $url" >&2
    exit 1
  fi

  if ! grep -iq '^permissions-policy:.*camera=().*microphone=().*geolocation=().*payment=()' "$headers"; then
    echo "healthcheck must include restrictive Permissions-Policy headers: $url" >&2
    exit 1
  fi

  if ! grep -iq '^x-frame-options: DENY' "$headers"; then
    echo "healthcheck must deny legacy frame embedding: $url" >&2
    exit 1
  fi

  echo "dashboard healthcheck ok: $url"
}

check_ready_url() {
  local url="$1"

  curl --fail --silent --show-error --max-time 10 --dump-header "$headers" --output "$body_file" "$url"
  local body
  body="$(cat "$body_file")"
  case "$body" in
    *'"status":"ok"'*|*'"status":"warn"'*) ;;
    *)
      echo "unexpected readiness response from $url: $body" >&2
      exit 1
      ;;
  esac

  if [[ "$body" != *'"failed":'* ]] || [[ "$body" != *'"warnings":'* ]] || [[ "$body" != *'"checkedAt":'* ]]; then
    echo "readiness must include failed/warnings counters and checkedAt: $url" >&2
    exit 1
  fi

  if [[ "$body" != *'"failedChecks":['* ]] || [[ "$body" != *'"warningChecks":['* ]]; then
    echo "readiness must include compact failedChecks/warningChecks summaries: $url" >&2
    exit 1
  fi

  if [[ "$body" == *'"checks":['* ]] || [[ "$body" == *'"detail":'* ]]; then
    echo "readiness must not expose full check details: $url" >&2
    exit 1
  fi

  if grep -iq '^set-cookie:' "$headers"; then
    echo "readiness must not set cookies: $url" >&2
    exit 1
  fi

  if ! grep -iq '^cache-control:.*no-store' "$headers"; then
    echo "readiness must set Cache-Control: no-store: $url" >&2
    exit 1
  fi

  if ! grep -iq '^content-type: application/json' "$headers"; then
    echo "readiness must return application/json: $url" >&2
    exit 1
  fi

  if ! grep -Eiq '^x-request-id: [A-Za-z0-9._:-]{8,128}' "$headers"; then
    echo "readiness must include a sane X-Request-Id header: $url" >&2
    exit 1
  fi

  echo "dashboard readiness ok: $url"
}

check_frontend_assets() {
  local base_url="$1"
  local origin
  origin="$(origin_from_url "$base_url")"
  local index_url="$origin/"

  curl --fail --silent --show-error --max-time 10 --dump-header "$headers" --output "$body_file" "$index_url"

  if ! grep -iq '^content-type: text/html' "$headers"; then
    echo "frontend document must return text/html: $index_url" >&2
    exit 1
  fi

  if ! grep -q '<html lang="es">' "$body_file" ||
    ! grep -q '<title>FlowARK Panel</title>' "$body_file" ||
    ! grep -q 'name="description" content="Panel privado de operaciones para servidores ARK de FlowCommunity."' "$body_file" ||
    ! grep -q 'name="robots" content="noindex,nofollow,noarchive"' "$body_file" ||
    ! grep -q 'name="theme-color" content="#09090b"' "$body_file"; then
    echo "frontend document must expose FlowARK production metadata: $index_url" >&2
    exit 1
  fi

  if grep -Eq '<title>client</title>|<html lang="en">' "$body_file"; then
    echo "frontend document still contains scaffold metadata: $index_url" >&2
    exit 1
  fi

  local asset_list="$tmp_dir/frontend-assets"
  node - "$body_file" > "$asset_list" <<'NODE'
const fs = require('node:fs');
const html = fs.readFileSync(process.argv[2], 'utf8');
const assets = new Set();
const pattern = /\b(?:src|href)=["']([^"']+)["']/g;
let match;
while ((match = pattern.exec(html)) !== null) {
  const asset = match[1];
  if (/^\/assets\/[A-Za-z0-9._-]+\.(?:js|css)$/.test(asset)) {
    assets.add(asset);
  }
}
for (const asset of assets) {
  console.log(asset);
}
NODE

  if ! grep -Eq '^/assets/index-[A-Za-z0-9_-]+\.js$' "$asset_list"; then
    echo "frontend document did not reference a hashed index asset: $index_url" >&2
    exit 1
  fi

  if [[ ! -s "$asset_list" ]]; then
    echo "frontend document did not reference hashed JS/CSS assets: $index_url" >&2
    exit 1
  fi

  local checked_assets=0
  local asset_path
  while IFS= read -r asset_path || [[ -n "$asset_path" ]]; do
    [[ -z "$asset_path" ]] && continue
    local asset_url="$origin$asset_path"
    curl --fail --silent --show-error --max-time 10 --head --dump-header "$headers" --output /dev/null "$asset_url"

    case "$asset_path" in
      *.js)
        if ! grep -Eiq '^content-type: (text|application)/javascript' "$headers"; then
          echo "frontend JS asset must be served as JavaScript, not HTML: $asset_url" >&2
          exit 1
        fi
        ;;
      *.css)
        if ! grep -iq '^content-type: text/css' "$headers"; then
          echo "frontend CSS asset must be served as CSS, not HTML: $asset_url" >&2
          exit 1
        fi
        ;;
    esac

    if ! grep -iq '^cache-control:.*immutable' "$headers"; then
      echo "frontend hashed asset must be immutable-cacheable: $asset_url" >&2
      exit 1
    fi
    checked_assets=$((checked_assets + 1))
  done < "$asset_list"

  echo "dashboard frontend assets ok: $checked_assets checked from $index_url"
}

check_missing_frontend_asset() {
  local base_url="$1"
  local origin
  origin="$(origin_from_url "$base_url")"
  local missing_url="$origin/assets/missing-dashboard-health-probe-$(date +%s)-$RANDOM.js"
  local status_code

  status_code="$(curl --silent --show-error --max-time 10 --dump-header "$headers" --output "$body_file" --write-out '%{http_code}' "$missing_url")"
  if [[ "$status_code" != "404" ]]; then
    echo "missing frontend asset must return 404, got $status_code: $missing_url" >&2
    exit 1
  fi

  if ! grep -iq '^content-type: text/plain' "$headers"; then
    echo "missing frontend asset must return text/plain, not HTML: $missing_url" >&2
    exit 1
  fi

  if grep -iq '^content-type: text/html' "$headers" || grep -qi '<!doctype html' "$body_file"; then
    echo "missing frontend asset must not fall back to the SPA shell: $missing_url" >&2
    exit 1
  fi

  if ! grep -iq '^cache-control:.*no-store' "$headers"; then
    echo "missing frontend asset must be non-cacheable: $missing_url" >&2
    exit 1
  fi

  if ! grep -iq '^x-flowark-asset-missing: 1' "$headers"; then
    echo "missing frontend asset must include X-FlowArk-Asset-Missing: $missing_url" >&2
    exit 1
  fi

  if grep -iq '^set-cookie:' "$headers"; then
    echo "missing frontend asset must not set cookies: $missing_url" >&2
    exit 1
  fi

  echo "dashboard missing frontend asset ok: $missing_url"
}

if [ "$#" -gt 0 ] || [ -n "${FLOWARK_DASHBOARD_URL:-}" ]; then
  target_url="${1:-$FLOWARK_DASHBOARD_URL}"
  check_url "$(health_url_from_target "$target_url")"
  check_frontend_assets "$target_url"
  check_missing_frontend_asset "$target_url"
else
  check_url "http://127.0.0.1:3040/healthz"
  check_url "http://127.0.0.1:3040/api/health"
  check_ready_url "http://127.0.0.1:3040/readyz"
  check_frontend_assets "http://127.0.0.1:3040/healthz"
  check_missing_frontend_asset "http://127.0.0.1:3040/healthz"
fi
