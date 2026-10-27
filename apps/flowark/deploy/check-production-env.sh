#!/usr/bin/env bash
set -euo pipefail

env_file="${1:-${FLOWARK_DASHBOARD_ENV:-/etc/flowark-dashboard/dashboard.env}}"
systemd_unit_file="${2:-${FLOWARK_DASHBOARD_SYSTEMD_UNIT:-}}"

if [[ ! -f "$env_file" ]]; then
  echo "error: env file not found: $env_file" >&2
  exit 1
fi
if [[ -L "$env_file" || ! -f "$env_file" ]]; then
  echo "error: env file must be a regular file, not a symlink or special path: $env_file" >&2
  exit 1
fi

env_mode="$(stat -c '%a' "$env_file")"
env_perms=$((8#$env_mode))
if (( env_perms & 0077 )); then
  echo "error: env file must not be readable or writable by group/others: $env_file" >&2
  exit 1
fi

declare -A env

while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="${raw_line#"${raw_line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  [[ -z "$line" || "${line:0:1}" == "#" ]] && continue
  if [[ "$line" != *=* ]]; then
    echo "error: invalid env line: $raw_line" >&2
    exit 1
  fi
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
    echo "error: invalid env key: $key" >&2
    exit 1
  fi
  env["$key"]="$value"
done < "$env_file"

failures=0

fail() {
  echo "error: $*" >&2
  failures=$((failures + 1))
}

require() {
  local key="$1"
  if [[ -z "${env[$key]:-}" ]]; then
    fail "$key is required"
  fi
}

is_placeholder() {
  local value
  value="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    replace-with-*|change-me|changeme|password|secret)
      return 0
      ;;
  esac
  return 1
}

require NODE_ENV
require HOST
require JWT_SECRET_KEY
require CORS_ORIGINS
require DASHBOARD_DATA_DIR

[[ "${env[NODE_ENV]:-}" == "production" ]] || fail "NODE_ENV must be production"

if [[ -n "${env[PORT]:-}" ]]; then
  if [[ ! "${env[PORT]}" =~ ^[0-9]+$ ]]; then
    fail "PORT must be numeric"
  elif (( env[PORT] < 1024 || env[PORT] > 65535 )); then
    fail "PORT must be between 1024 and 65535 behind nginx"
  fi
fi

if [[ "${env[HOST]:-}" != "127.0.0.1" && "${env[HOST]:-}" != "::1" && "${env[HOST]:-}" != "localhost" ]]; then
  fail "HOST should bind to loopback behind nginx, not '${env[HOST]:-}'"
fi

validate_absolute_path() {
  local key="$1"
  local value="${env[$key]:-}"
  [[ -z "$value" ]] && return
  IFS=',' read -ra entries <<< "$value"
  local entry
  for entry in "${entries[@]}"; do
    entry="${entry#"${entry%%[![:space:]]*}"}"
    entry="${entry%"${entry##*[![:space:]]}"}"
    [[ -z "$entry" ]] && continue
    [[ "$entry" == /* ]] || fail "$key entries must be absolute paths: $entry"
    case "$entry" in
      */../*|*/..|/..)
        fail "$key entries must not contain traversal: $entry"
        ;;
    esac
  done
}

validate_absolute_path DASHBOARD_DATA_DIR
validate_absolute_path FLOWARK_DASHBOARD_BACKUP_DIR
validate_absolute_path ARK_SCRIPT_ROOTS
validate_absolute_path ARK_CONFIG_ROOTS
validate_absolute_path ARK_LOG_ROOTS
validate_absolute_path FILE_MANAGER_GAME_ROOT
validate_absolute_path FILE_MANAGER_LGSM_ROOT
validate_absolute_path INGAME_ADMINS_PATH
validate_absolute_path PLUGIN_MANAGER_OBELISK_ROOT
validate_absolute_path PLUGIN_MANAGER_ARKAPI_ROOT

jwt_secret="${env[JWT_SECRET_KEY]:-}"
if [[ ${#jwt_secret} -lt 32 ]]; then
  fail "JWT_SECRET_KEY must be at least 32 characters"
fi
if is_placeholder "$jwt_secret"; then
  fail "JWT_SECRET_KEY still uses a placeholder value"
fi

IFS=',' read -ra origins <<< "${env[CORS_ORIGINS]:-}"
valid_origin_count=0
for origin in "${origins[@]}"; do
  origin="${origin#"${origin%%[![:space:]]*}"}"
  origin="${origin%"${origin##*[![:space:]]}"}"
  [[ -z "$origin" ]] && continue
  valid_origin_count=$((valid_origin_count + 1))
  [[ "$origin" =~ ^https:// ]] || fail "CORS_ORIGINS entry must use https: $origin"
  [[ "$origin" != "*" && "${origin,,}" != "null" ]] || fail "CORS_ORIGINS must not include wildcard or null origins"
  [[ "$origin" =~ ^https://[^/?#[:space:]]+(:[0-9]+)?$ ]] || fail "CORS_ORIGINS entries must be exact origins without paths, queries, or fragments: $origin"
  [[ "$origin" =~ ^https?://(localhost|127\.0\.0\.1)(:|/|$) ]] && fail "CORS_ORIGINS must not include localhost in production: $origin"
done
[[ "$valid_origin_count" -gt 0 ]] || fail "CORS_ORIGINS must include at least one HTTPS origin"

if [[ -n "${env[TRUST_PROXY_HOPS]:-}" ]]; then
  if [[ ! "${env[TRUST_PROXY_HOPS]}" =~ ^[0-9]+$ ]]; then
    fail "TRUST_PROXY_HOPS must be numeric"
  elif (( env[TRUST_PROXY_HOPS] > 10 )); then
    fail "TRUST_PROXY_HOPS must be between 0 and 10"
  fi
fi

validate_timeout_ms() {
  local key="$1"
  local min="$2"
  local max="$3"
  local value="${env[$key]:-}"
  [[ -z "$value" ]] && return
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    fail "$key must be numeric milliseconds"
    return
  fi
  if (( value < min || value > max )); then
    fail "$key must be between ${min}ms and ${max}ms"
  fi
}

validate_timeout_ms HTTP_REQUEST_TIMEOUT_MS 5000 300000
validate_timeout_ms HTTP_HEADERS_TIMEOUT_MS 5000 60000
validate_timeout_ms HTTP_KEEPALIVE_TIMEOUT_MS 1000 60000
validate_timeout_ms RCON_CONNECT_TIMEOUT_MS 1000 60000
validate_timeout_ms RCON_COMMAND_TIMEOUT_MS 1000 60000
validate_timeout_ms GAMEDIG_TIMEOUT_MS 1000 60000
validate_timeout_ms DISCORD_WEBHOOK_TIMEOUT_MS 1000 30000

if [[ -n "${env[RCON_RESPONSE_MAX_CHARS]:-}" ]]; then
  if [[ ! "${env[RCON_RESPONSE_MAX_CHARS]}" =~ ^[0-9]+$ ]]; then
    fail "RCON_RESPONSE_MAX_CHARS must be numeric"
  elif (( env[RCON_RESPONSE_MAX_CHARS] < 1024 || env[RCON_RESPONSE_MAX_CHARS] > 1048576 )); then
    fail "RCON_RESPONSE_MAX_CHARS must be between 1024 and 1048576"
  fi
fi

normalize_path_syntax() {
  local value="$1"
  value="${value%/}"
  [[ -n "$value" ]] || value="/"
  printf '%s\n' "$value"
}

append_path_entries() {
  local key="$1"
  local fallback="${2:-}"
  local value="${env[$key]:-$fallback}"
  [[ -z "$value" ]] && return
  IFS=',' read -ra entries <<< "$value"
  local entry
  for entry in "${entries[@]}"; do
    entry="${entry#"${entry%%[![:space:]]*}"}"
    entry="${entry%"${entry##*[![:space:]]}"}"
    [[ -z "$entry" ]] && continue
    required_write_paths+=("$(normalize_path_syntax "$entry")")
  done
}

path_covered_by_systemd_write_path() {
  local target
  target="$(normalize_path_syntax "$1")"
  local writable
  for writable in "${systemd_write_paths[@]}"; do
    [[ "$target" == "$writable" || "$target" == "$writable"/* ]] && return 0
  done
  return 1
}

if [[ -n "$systemd_unit_file" ]]; then
  if [[ ! -f "$systemd_unit_file" ]]; then
    fail "systemd unit file not found: $systemd_unit_file"
  else
    declare -a systemd_write_paths=()
    while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
      line="${raw_line#"${raw_line%%[![:space:]]*}"}"
      line="${line%"${line##*[![:space:]]}"}"
      [[ "$line" == ReadWritePaths=* ]] || continue
      value="${line#ReadWritePaths=}"
      for entry in $value; do
        [[ "$entry" == /* ]] || continue
        systemd_write_paths+=("$(normalize_path_syntax "$entry")")
      done
    done < "$systemd_unit_file"

    if [[ "${#systemd_write_paths[@]}" -eq 0 ]]; then
      fail "systemd unit must define ReadWritePaths entries when ProtectSystem is used"
    fi

    declare -a required_write_paths=()
    dashboard_data_dir="${env[DASHBOARD_DATA_DIR]:-}"
    append_path_entries DASHBOARD_DATA_DIR
    append_path_entries FLOWARK_DASHBOARD_BACKUP_DIR "${dashboard_data_dir%/}/backups"
    append_path_entries ARK_CONFIG_ROOTS "${env[FILE_MANAGER_GAME_ROOT]:-/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer}"
    append_path_entries ARK_LOG_ROOTS "/servidor/ark/serverfiles/ShooterGame/Saved/Logs"
    append_path_entries FILE_MANAGER_GAME_ROOT "/servidor/ark/serverfiles/ShooterGame/Saved/Config/LinuxServer"
    append_path_entries FILE_MANAGER_LGSM_ROOT "/servidor/ark/lgsm/config-lgsm/arkserver"
    append_path_entries INGAME_ADMINS_PATH "/servidor/ark/serverfiles/ShooterGame/Saved/AllowedCheaterSteamIDs.txt"
    obelisk_root="${env[PLUGIN_MANAGER_OBELISK_ROOT]:-${env[OBELISK_ROOT]:-/servidor/ark/obelisk}}"
    required_write_paths+=("$(normalize_path_syntax "${obelisk_root%/}/state/instances")")

    declare -A seen_required_write_paths=()
    for required_path in "${required_write_paths[@]}"; do
      [[ -z "$required_path" ]] && continue
      if [[ -n "${seen_required_write_paths[$required_path]:-}" ]]; then
        continue
      fi
      seen_required_write_paths["$required_path"]=1
      if ! path_covered_by_systemd_write_path "$required_path"; then
        fail "systemd ReadWritePaths does not cover configured mutable path: $required_path"
      fi
    done
  fi
fi

if [[ -n "${env[HTTP_HEADERS_TIMEOUT_MS]:-}" && -n "${env[HTTP_REQUEST_TIMEOUT_MS]:-}" &&
      "${env[HTTP_HEADERS_TIMEOUT_MS]}" =~ ^[0-9]+$ && "${env[HTTP_REQUEST_TIMEOUT_MS]}" =~ ^[0-9]+$ &&
      "${env[HTTP_HEADERS_TIMEOUT_MS]}" -gt "${env[HTTP_REQUEST_TIMEOUT_MS]}" ]]; then
  fail "HTTP_HEADERS_TIMEOUT_MS must not exceed HTTP_REQUEST_TIMEOUT_MS"
fi

bootstrap_user_set=0
bootstrap_password_set=0
[[ -n "${env[DASHBOARD_BOOTSTRAP_USERNAME]:-}" ]] && bootstrap_user_set=1
[[ -n "${env[DASHBOARD_BOOTSTRAP_PASSWORD]:-}" ]] && bootstrap_password_set=1
if [[ "$bootstrap_user_set" -ne "$bootstrap_password_set" ]]; then
  fail "DASHBOARD_BOOTSTRAP_USERNAME and DASHBOARD_BOOTSTRAP_PASSWORD must be set together"
fi
if [[ "$bootstrap_password_set" -eq 1 ]]; then
  bootstrap_password="${env[DASHBOARD_BOOTSTRAP_PASSWORD]}"
  if [[ ${#bootstrap_password} -lt 12 ]]; then
    fail "DASHBOARD_BOOTSTRAP_PASSWORD must be at least 12 characters"
  fi
  if is_placeholder "$bootstrap_password"; then
    fail "DASHBOARD_BOOTSTRAP_PASSWORD still uses a placeholder value"
  fi
fi

if [[ "$failures" -gt 0 ]]; then
  exit 1
fi

echo "production env verified: $env_file"
