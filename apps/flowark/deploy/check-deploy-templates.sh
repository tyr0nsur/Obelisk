#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

bash -n "$repo_root/deploy/check-dashboard-health.sh"
grep -F "health_url_from_target()" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "u.pathname = '/healthz'" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "check_frontend_assets()" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "frontend document must expose FlowARK production metadata" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "frontend document still contains scaffold metadata" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "frontend JS asset must be served as JavaScript, not HTML" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "frontend CSS asset must be served as CSS, not HTML" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "dashboard frontend assets ok" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "check_missing_frontend_asset()" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "missing frontend asset must not fall back to the SPA shell" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "X-FlowArk-Asset-Missing" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
grep -F "/assets/index-" "$repo_root/deploy/check-dashboard-health.sh" >/dev/null
bash -n "$repo_root/deploy/check-production-env.sh"
bash -n "$repo_root/deploy/check-production-ready.sh"
bash -n "$repo_root/deploy/manage-dashboard-data.sh"
bash -n "$repo_root/deploy/start-pm2.sh"
grep -F "FLOWARK_DASHBOARD_ENV" "$repo_root/deploy/check-production-env.sh" >/dev/null
grep -F "FLOWARK_DASHBOARD_ENV" "$repo_root/deploy/check-production-ready.sh" >/dev/null
node --check "$repo_root/deploy/pm2/ecosystem.config.cjs" >/dev/null
grep -F "script: 'server.js'" "$repo_root/deploy/pm2/ecosystem.config.cjs" >/dev/null
grep -F "cwd: path.join(repoRoot, 'server')" "$repo_root/deploy/pm2/ecosystem.config.cjs" >/dev/null
grep -F "pm_exec_path" "$repo_root/deploy/start-pm2.sh" >/dev/null
grep -F "pm2 delete" "$repo_root/deploy/start-pm2.sh" >/dev/null
grep -F "FLOWARK_DASHBOARD_ENV" "$repo_root/deploy/start-pm2.sh" >/dev/null
grep -F "FLOWARK_DASHBOARD_HEALTH_URL" "$repo_root/deploy/start-pm2.sh" >/dev/null
grep -F "FLOWARK_PM2_HEALTH_RETRIES" "$repo_root/deploy/start-pm2.sh" >/dev/null
grep -F "check-dashboard-health.sh" "$repo_root/deploy/start-pm2.sh" >/dev/null
grep -F 'add_header X-Robots-Tag "noindex, nofollow, noarchive" always;' \
  "$repo_root/deploy/nginx/flowark-dashboard.conf" >/dev/null
grep -F 'add_header Strict-Transport-Security "max-age=15552000" always;' \
  "$repo_root/deploy/nginx/flowark-dashboard.conf" >/dev/null
for env_example in "$repo_root/.env.example" "$repo_root/deploy/env/dashboard.env.example"; do
  for key in \
    NODE_ENV \
    PORT \
    HOST \
    JWT_SECRET_KEY \
    CORS_ORIGINS \
    TRUST_PROXY_HOPS \
    DASHBOARD_DATA_DIR \
    FLOWARK_DASHBOARD_BACKUP_DIR \
    HTTP_REQUEST_TIMEOUT_MS \
    HTTP_HEADERS_TIMEOUT_MS \
    HTTP_KEEPALIVE_TIMEOUT_MS \
    RCON_CONNECT_TIMEOUT_MS \
    RCON_COMMAND_TIMEOUT_MS \
    GAMEDIG_TIMEOUT_MS \
    DISCORD_WEBHOOK_TIMEOUT_MS
  do
    grep -E "^${key}=" "$env_example" >/dev/null
  done
done
for directive in \
  'UMask=0077' \
  'NoNewPrivileges=true' \
  'CapabilityBoundingSet=' \
  'PrivateDevices=true' \
  'PrivateMounts=true' \
  'ProtectClock=true' \
  'ProtectHostname=true' \
  'ProtectKernelTunables=true' \
  'ProtectKernelModules=true' \
  'ProtectControlGroups=true' \
  'RestrictNamespaces=true' \
  'RestrictSUIDSGID=true' \
  'RestrictRealtime=true' \
  'LockPersonality=true' \
  'RemoveIPC=true' \
  'SystemCallArchitectures=native'
do
  grep -F "$directive" "$repo_root/deploy/systemd/flowark-dashboard.service" >/dev/null
done

backup_smoke_dir="$(mktemp -d)"
trap 'rm -rf "$backup_smoke_dir"' EXIT
mkdir -p "$backup_smoke_dir/data/presets/example" "$backup_smoke_dir/backups" "$backup_smoke_dir/restored"
printf '{"ok":true}\n' > "$backup_smoke_dir/data/nodes.json"
printf 'preset\n' > "$backup_smoke_dir/data/presets/example/metadata.json"
chmod 775 "$backup_smoke_dir/data" "$backup_smoke_dir/data/presets" "$backup_smoke_dir/data/presets/example"
chmod 664 "$backup_smoke_dir/data/nodes.json" "$backup_smoke_dir/data/presets/example/metadata.json"
DASHBOARD_DATA_DIR="$backup_smoke_dir/data" FLOWARK_DASHBOARD_BACKUP_DIR="$backup_smoke_dir/backups" "$repo_root/deploy/manage-dashboard-data.sh" prepare >/dev/null
test "$(stat -c '%a' "$backup_smoke_dir/data")" = "700"
test "$(stat -c '%a' "$backup_smoke_dir/data/presets/example")" = "700"
test "$(stat -c '%a' "$backup_smoke_dir/data/nodes.json")" = "600"
test "$(stat -c '%a' "$backup_smoke_dir/data/presets/example/metadata.json")" = "600"
test "$(stat -c '%a' "$backup_smoke_dir/backups")" = "700"
archive="$(DASHBOARD_DATA_DIR="$backup_smoke_dir/data" FLOWARK_DASHBOARD_BACKUP_DIR="$backup_smoke_dir/backups" "$repo_root/deploy/manage-dashboard-data.sh" backup)"
test -f "$archive"
test -f "$archive.sha256"
test "$(stat -c '%a' "$archive")" = "600"
test "$(stat -c '%a' "$archive.sha256")" = "600"
(cd "$(dirname "$archive")" && sha256sum -c "$(basename "$archive").sha256") >/dev/null
test "$(stat -c '%a' "$backup_smoke_dir/backups")" = "700"
second_archive="$(DASHBOARD_DATA_DIR="$backup_smoke_dir/data" FLOWARK_DASHBOARD_BACKUP_DIR="$backup_smoke_dir/backups" "$repo_root/deploy/manage-dashboard-data.sh" backup)"
test -f "$second_archive"
test "$archive" != "$second_archive"
"$repo_root/deploy/manage-dashboard-data.sh" list "$backup_smoke_dir/backups" | grep -F "$archive" >/dev/null
"$repo_root/deploy/manage-dashboard-data.sh" restore "$archive" "$backup_smoke_dir/restored" >/dev/null
test -f "$backup_smoke_dir/restored/nodes.json"
test "$(stat -c '%a' "$backup_smoke_dir/restored")" = "700"
test "$(stat -c '%a' "$backup_smoke_dir/restored/nodes.json")" = "600"

mkdir -p "$backup_smoke_dir/permissive-source/nested" "$backup_smoke_dir/restored-permissive"
printf 'secret\n' > "$backup_smoke_dir/permissive-source/nested/admins.json"
chmod 777 "$backup_smoke_dir/permissive-source" "$backup_smoke_dir/permissive-source/nested"
chmod 666 "$backup_smoke_dir/permissive-source/nested/admins.json"
permissive_archive="$backup_smoke_dir/backups/flowark-dashboard-data-permissive.tar.gz"
tar -C "$backup_smoke_dir/permissive-source" -czf "$permissive_archive" .
"$repo_root/deploy/manage-dashboard-data.sh" restore "$permissive_archive" "$backup_smoke_dir/restored-permissive" >/dev/null
test "$(stat -c '%a' "$backup_smoke_dir/restored-permissive")" = "700"
test "$(stat -c '%a' "$backup_smoke_dir/restored-permissive/nested")" = "700"
test "$(stat -c '%a' "$backup_smoke_dir/restored-permissive/nested/admins.json")" = "600"
for index in 1 2 3 4; do
  old_archive="$backup_smoke_dir/backups/flowark-dashboard-data-prune-$index.tar.gz"
  printf 'old-%s\n' "$index" > "$old_archive"
  touch -t "20260101010${index}.00" "$old_archive"
done
"$repo_root/deploy/manage-dashboard-data.sh" prune "$backup_smoke_dir/backups" 2 >/dev/null
test "$(find "$backup_smoke_dir/backups" -maxdepth 1 -type f -name 'flowark-dashboard-data-*.tar.gz' | wc -l)" -eq 2
if "$repo_root/deploy/manage-dashboard-data.sh" prune "$backup_smoke_dir/backups" 0 >/dev/null 2>&1; then
  echo "error: invalid prune keep count was accepted" >&2
  exit 1
fi

mkdir -p "$backup_smoke_dir/checksum-corrupt"
corrupt_archive="$backup_smoke_dir/backups/flowark-dashboard-data-corrupt.tar.gz"
checksum_source="$second_archive"
if [[ ! -f "$checksum_source" || ! -f "$checksum_source.sha256" ]]; then
  checksum_source="$(find "$backup_smoke_dir/backups" -maxdepth 1 -type f -name 'flowark-dashboard-data-*.tar.gz' -exec sh -c 'test -f "$1.sha256" && printf "%s\n" "$1"' sh {} \; | head -n1)"
fi
cp "$checksum_source" "$corrupt_archive"
read -r expected_hash _ < "$checksum_source.sha256"
printf '%s  %s\n' "$expected_hash" "$(basename "$corrupt_archive")" > "$corrupt_archive.sha256"
printf 'corruption\n' >> "$corrupt_archive"
if "$repo_root/deploy/manage-dashboard-data.sh" restore "$corrupt_archive" "$backup_smoke_dir/checksum-corrupt" >/dev/null 2>&1; then
  echo "error: corrupted archive with checksum was accepted" >&2
  exit 1
fi

mkdir -p "$backup_smoke_dir/malicious"
ln -s /etc/passwd "$backup_smoke_dir/malicious/admins.json"
malicious_archive="$backup_smoke_dir/backups/flowark-dashboard-data-malicious.tar.gz"
tar -C "$backup_smoke_dir/malicious" -czf "$malicious_archive" .
if "$repo_root/deploy/manage-dashboard-data.sh" restore "$malicious_archive" "$backup_smoke_dir/restored-symlink" >/dev/null 2>&1; then
  echo "error: symlink archive was accepted" >&2
  exit 1
fi

mkdir -p "$backup_smoke_dir/malicious-hardlink"
printf 'secret\n' > "$backup_smoke_dir/malicious-hardlink/source.json"
ln "$backup_smoke_dir/malicious-hardlink/source.json" "$backup_smoke_dir/malicious-hardlink/admins.json"
hardlink_archive="$backup_smoke_dir/backups/flowark-dashboard-data-malicious-hardlink.tar.gz"
tar -C "$backup_smoke_dir/malicious-hardlink" -czf "$hardlink_archive" .
if "$repo_root/deploy/manage-dashboard-data.sh" restore "$hardlink_archive" "$backup_smoke_dir/restored-hardlink" >/dev/null 2>&1; then
  echo "error: hardlink archive was accepted" >&2
  exit 1
fi

mkdir -p "$backup_smoke_dir/malicious-fifo"
mkfifo "$backup_smoke_dir/malicious-fifo/admins.json"
fifo_archive="$backup_smoke_dir/backups/flowark-dashboard-data-malicious-fifo.tar.gz"
tar -C "$backup_smoke_dir/malicious-fifo" -czf "$fifo_archive" .
if "$repo_root/deploy/manage-dashboard-data.sh" restore "$fifo_archive" "$backup_smoke_dir/restored-fifo" >/dev/null 2>&1; then
  echo "error: fifo archive was accepted" >&2
  exit 1
fi

mkdir -p "$backup_smoke_dir/unsafe-source-symlink"
ln -s /etc/passwd "$backup_smoke_dir/unsafe-source-symlink/admins.json"
if DASHBOARD_DATA_DIR="$backup_smoke_dir/unsafe-source-symlink" FLOWARK_DASHBOARD_BACKUP_DIR="$backup_smoke_dir/backups" "$repo_root/deploy/manage-dashboard-data.sh" prepare >/dev/null 2>&1; then
  echo "error: prepare accepted a symlinked source entry" >&2
  exit 1
fi
if DASHBOARD_DATA_DIR="$backup_smoke_dir/unsafe-source-symlink" FLOWARK_DASHBOARD_BACKUP_DIR="$backup_smoke_dir/backups" "$repo_root/deploy/manage-dashboard-data.sh" backup >/dev/null 2>&1; then
  echo "error: backup accepted a symlinked source entry" >&2
  exit 1
fi

mkdir -p "$backup_smoke_dir/unsafe-source-hardlink"
printf 'secret\n' > "$backup_smoke_dir/unsafe-source-hardlink/source.json"
ln "$backup_smoke_dir/unsafe-source-hardlink/source.json" "$backup_smoke_dir/unsafe-source-hardlink/admins.json"
if DASHBOARD_DATA_DIR="$backup_smoke_dir/unsafe-source-hardlink" FLOWARK_DASHBOARD_BACKUP_DIR="$backup_smoke_dir/backups" "$repo_root/deploy/manage-dashboard-data.sh" backup >/dev/null 2>&1; then
  echo "error: backup accepted a hardlinked source entry" >&2
  exit 1
fi

mkdir -p "$backup_smoke_dir/unsafe-source-fifo"
mkfifo "$backup_smoke_dir/unsafe-source-fifo/admins.json"
if DASHBOARD_DATA_DIR="$backup_smoke_dir/unsafe-source-fifo" FLOWARK_DASHBOARD_BACKUP_DIR="$backup_smoke_dir/backups" "$repo_root/deploy/manage-dashboard-data.sh" backup >/dev/null 2>&1; then
  echo "error: backup accepted a fifo source entry" >&2
  exit 1
fi

valid_env="$backup_smoke_dir/dashboard.env"
cat > "$valid_env" <<'EOF'
NODE_ENV=production
PORT=3040
HOST=127.0.0.1
JWT_SECRET_KEY=1234567890abcdef1234567890abcdef
CORS_ORIGINS=https://ark.example.com
TRUST_PROXY_HOPS=1
DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
HTTP_REQUEST_TIMEOUT_MS=30000
HTTP_HEADERS_TIMEOUT_MS=10000
HTTP_KEEPALIVE_TIMEOUT_MS=5000
RCON_CONNECT_TIMEOUT_MS=5000
RCON_COMMAND_TIMEOUT_MS=5000
GAMEDIG_TIMEOUT_MS=5000
DISCORD_WEBHOOK_TIMEOUT_MS=3000
EOF
chmod 600 "$valid_env"
"$repo_root/deploy/check-production-env.sh" "$valid_env" "$repo_root/deploy/systemd/flowark-dashboard.service" >/dev/null
FLOWARK_DASHBOARD_ENV="$valid_env" "$repo_root/deploy/check-production-env.sh" >/dev/null

custom_env="$backup_smoke_dir/dashboard-custom-paths.env"
cat > "$custom_env" <<'EOF'
NODE_ENV=production
PORT=3040
HOST=127.0.0.1
JWT_SECRET_KEY=1234567890abcdef1234567890abcdef
CORS_ORIGINS=https://ark.example.com
DASHBOARD_DATA_DIR=/srv/flowark/state
FLOWARK_DASHBOARD_BACKUP_DIR=/srv/flowark/backups
ARK_SCRIPT_ROOTS=/srv/ark/scripts
ARK_CONFIG_ROOTS=/srv/ark/config
ARK_LOG_ROOTS=/srv/ark/logs
FILE_MANAGER_GAME_ROOT=/srv/ark/config
FILE_MANAGER_LGSM_ROOT=/srv/ark/lgsm
INGAME_ADMINS_PATH=/srv/ark/admins/AllowedCheaterSteamIDs.txt
PLUGIN_MANAGER_OBELISK_ROOT=/srv/obelisk
EOF
chmod 600 "$custom_env"
if "$repo_root/deploy/check-production-env.sh" "$custom_env" "$repo_root/deploy/systemd/flowark-dashboard.service" >/dev/null 2>&1; then
  echo "error: custom mutable paths not covered by systemd ReadWritePaths were accepted" >&2
  exit 1
fi

custom_unit="$backup_smoke_dir/flowark-dashboard-custom.service"
cp "$repo_root/deploy/systemd/flowark-dashboard.service" "$custom_unit"
cat >> "$custom_unit" <<'EOF'
ReadWritePaths=/srv/flowark/state
ReadWritePaths=/srv/flowark/backups
ReadWritePaths=/srv/ark/config
ReadWritePaths=/srv/ark/logs
ReadWritePaths=/srv/ark/lgsm
ReadWritePaths=/srv/ark/admins
ReadWritePaths=/srv/obelisk/state/instances
EOF
"$repo_root/deploy/check-production-env.sh" "$custom_env" "$custom_unit" >/dev/null

insecure_env="$backup_smoke_dir/dashboard-insecure-perms.env"
cp "$valid_env" "$insecure_env"
chmod 644 "$insecure_env"
if "$repo_root/deploy/check-production-env.sh" "$insecure_env" >/dev/null 2>&1; then
  echo "error: world-readable production env was accepted" >&2
  exit 1
fi

symlink_env="$backup_smoke_dir/dashboard-symlink.env"
ln -s "$valid_env" "$symlink_env"
if "$repo_root/deploy/check-production-env.sh" "$symlink_env" >/dev/null 2>&1; then
  echo "error: symlinked production env was accepted" >&2
  exit 1
fi

invalid_env="$backup_smoke_dir/dashboard-invalid.env"
cat > "$invalid_env" <<'EOF'
NODE_ENV=production
HOST=0.0.0.0
JWT_SECRET_KEY=replace-with-32-plus-random-characters
CORS_ORIGINS=http://localhost:3040
DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
DASHBOARD_BOOTSTRAP_USERNAME=owner
EOF
chmod 600 "$invalid_env"
if "$repo_root/deploy/check-production-env.sh" "$invalid_env" >/dev/null 2>&1; then
  echo "error: invalid production env was accepted" >&2
  exit 1
fi

invalid_cors_env="$backup_smoke_dir/dashboard-invalid-cors.env"
cat > "$invalid_cors_env" <<'EOF'
NODE_ENV=production
HOST=127.0.0.1
JWT_SECRET_KEY=1234567890abcdef1234567890abcdef
CORS_ORIGINS=https://ark.example.com/path
DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
EOF
chmod 600 "$invalid_cors_env"
if "$repo_root/deploy/check-production-env.sh" "$invalid_cors_env" >/dev/null 2>&1; then
  echo "error: malformed CORS origin was accepted" >&2
  exit 1
fi

invalid_timeout_env="$backup_smoke_dir/dashboard-invalid-timeout.env"
cat > "$invalid_timeout_env" <<'EOF'
NODE_ENV=production
HOST=127.0.0.1
JWT_SECRET_KEY=1234567890abcdef1234567890abcdef
CORS_ORIGINS=https://ark.example.com
DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
HTTP_REQUEST_TIMEOUT_MS=10000
HTTP_HEADERS_TIMEOUT_MS=20000
RCON_CONNECT_TIMEOUT_MS=999999
EOF
chmod 600 "$invalid_timeout_env"
if "$repo_root/deploy/check-production-env.sh" "$invalid_timeout_env" >/dev/null 2>&1; then
  echo "error: invalid HTTP timeout env was accepted" >&2
  exit 1
fi

invalid_discord_timeout_env="$backup_smoke_dir/dashboard-invalid-discord-timeout.env"
cat > "$invalid_discord_timeout_env" <<'EOF'
NODE_ENV=production
HOST=127.0.0.1
JWT_SECRET_KEY=1234567890abcdef1234567890abcdef
CORS_ORIGINS=https://ark.example.com
DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
DISCORD_WEBHOOK_TIMEOUT_MS=0
EOF
chmod 600 "$invalid_discord_timeout_env"
if "$repo_root/deploy/check-production-env.sh" "$invalid_discord_timeout_env" >/dev/null 2>&1; then
  echo "error: invalid Discord webhook timeout env was accepted" >&2
  exit 1
fi

invalid_proxy_env="$backup_smoke_dir/dashboard-invalid-proxy.env"
cat > "$invalid_proxy_env" <<'EOF'
NODE_ENV=production
HOST=127.0.0.1
JWT_SECRET_KEY=1234567890abcdef1234567890abcdef
CORS_ORIGINS=https://ark.example.com
DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
TRUST_PROXY_HOPS=11
EOF
chmod 600 "$invalid_proxy_env"
if "$repo_root/deploy/check-production-env.sh" "$invalid_proxy_env" >/dev/null 2>&1; then
  echo "error: invalid trust proxy hop count was accepted" >&2
  exit 1
fi

invalid_path_env="$backup_smoke_dir/dashboard-invalid-path.env"
cat > "$invalid_path_env" <<'EOF'
NODE_ENV=production
PORT=80
HOST=127.0.0.1
JWT_SECRET_KEY=1234567890abcdef1234567890abcdef
CORS_ORIGINS=https://ark.example.com
DASHBOARD_DATA_DIR=relative/data
ARK_SCRIPT_ROOTS=/servidor/ark/../escape
EOF
chmod 600 "$invalid_path_env"
if "$repo_root/deploy/check-production-env.sh" "$invalid_path_env" >/dev/null 2>&1; then
  echo "error: invalid port/path env was accepted" >&2
  exit 1
fi

pm2_safe_env="$backup_smoke_dir/dashboard-pm2-safe.env"
pm2_marker="$backup_smoke_dir/pm2-env-executed"
cat > "$pm2_safe_env" <<EOF
NODE_ENV=production
PORT=3040
HOST=127.0.0.1
JWT_SECRET_KEY=1234567890abcdef1234567890abcdef
CORS_ORIGINS=https://ark.example.com
TRUST_PROXY_HOPS=1
DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
HTTP_REQUEST_TIMEOUT_MS=30000
HTTP_HEADERS_TIMEOUT_MS=10000
HTTP_KEEPALIVE_TIMEOUT_MS=5000
RCON_CONNECT_TIMEOUT_MS=5000
RCON_COMMAND_TIMEOUT_MS=5000
GAMEDIG_TIMEOUT_MS=5000
DISCORD_WEBHOOK_TIMEOUT_MS=3000
FLOWARK_UNUSED_PROBE=\$(touch "$pm2_marker")
EOF
chmod 600 "$pm2_safe_env"
FLOWARK_PM2_DRY_RUN=1 "$repo_root/deploy/start-pm2.sh" "$pm2_safe_env" >/dev/null
if [[ -e "$pm2_marker" ]]; then
  echo "error: PM2 env loader executed shell content from env file" >&2
  exit 1
fi
FLOWARK_DASHBOARD_ENV="$pm2_safe_env" FLOWARK_PM2_DRY_RUN=1 "$repo_root/deploy/start-pm2.sh" >/dev/null

if command -v systemd-analyze >/dev/null 2>&1; then
  systemd-analyze verify "$repo_root/deploy/systemd/flowark-dashboard.service"
else
  echo "skip: systemd-analyze not installed"
fi

if command -v logrotate >/dev/null 2>&1; then
  state_file="$(mktemp)"
  logrotate -d -s "$state_file" "$repo_root/deploy/logrotate/flowark-dashboard" >/dev/null 2>&1
  rm -f "$state_file"
else
  echo "skip: logrotate not installed"
fi

if command -v nginx >/dev/null 2>&1 && command -v openssl >/dev/null 2>&1; then
  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$backup_smoke_dir" "$tmp_dir"' EXIT
  mkdir -p "$tmp_dir/conf.d" "$tmp_dir/logs" "$tmp_dir/client_body_temp" "$tmp_dir/proxy_temp"
  grep -F 'proxy_set_header X-Request-Id $request_id;' "$repo_root/deploy/nginx/flowark-dashboard.conf" >/dev/null
  grep -F 'proxy_set_header X-Forwarded-Host $host;' "$repo_root/deploy/nginx/flowark-dashboard.conf" >/dev/null
  grep -F 'proxy_set_header X-Forwarded-Port $server_port;' "$repo_root/deploy/nginx/flowark-dashboard.conf" >/dev/null
  cp "$repo_root/deploy/nginx/flowark-dashboard.conf" "$tmp_dir/conf.d/site.conf"
  cp "$repo_root/deploy/nginx/flowark-dashboard-map.conf" "$tmp_dir/conf.d/map.conf"
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$tmp_dir/key.pem" \
    -out "$tmp_dir/cert.pem" \
    -subj '/CN=ark.example.com' \
    -days 1 >/dev/null 2>&1
  sed -i \
    -e 's#listen 80;#listen 18080;#' \
    -e 's#listen 443 ssl;#listen 18443 ssl;#' \
    -e "s#/etc/letsencrypt/live/ark.example.com/fullchain.pem#$tmp_dir/cert.pem#" \
    -e "s#/etc/letsencrypt/live/ark.example.com/privkey.pem#$tmp_dir/key.pem#" \
    "$tmp_dir/conf.d/site.conf"
  cat > "$tmp_dir/nginx.conf" <<EOF
error_log $tmp_dir/logs/error.log;
pid $tmp_dir/nginx.pid;
events {}
http {
  access_log $tmp_dir/logs/access.log;
  include $tmp_dir/conf.d/map.conf;
  include $tmp_dir/conf.d/site.conf;
}
EOF
  nginx -t -c "$tmp_dir/nginx.conf" -p "$tmp_dir" -e "$tmp_dir/logs/error.log" >/dev/null
else
  echo "skip: nginx or openssl not installed"
fi

echo "deploy templates verified"
