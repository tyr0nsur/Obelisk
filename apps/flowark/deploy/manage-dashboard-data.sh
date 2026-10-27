#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  manage-dashboard-data.sh prepare [data_dir] [backup_dir]
  manage-dashboard-data.sh backup [data_dir] [backup_dir]
  manage-dashboard-data.sh list [backup_dir]
  manage-dashboard-data.sh prune [backup_dir] [keep_count]
  manage-dashboard-data.sh restore <archive.tar.gz> [data_dir] [--force]

Environment defaults:
  DASHBOARD_DATA_DIR=/var/lib/flowark-dashboard
  FLOWARK_DASHBOARD_BACKUP_DIR=$DASHBOARD_DATA_DIR/backups
EOF
}

data_dir_default="${DASHBOARD_DATA_DIR:-/var/lib/flowark-dashboard}"
backup_dir_default="${FLOWARK_DASHBOARD_BACKUP_DIR:-$data_dir_default/backups}"
restore_tmp_dir=""

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "required command not found: $1" >&2
    exit 1
  fi
}

reject_unsafe_archive_paths() {
  local archive="$1"
  local entry
  while IFS= read -r entry; do
    case "$entry" in
      ""|/*|../*|*/../*|*"/.."|"..")
        echo "unsafe archive path: $entry" >&2
        exit 1
        ;;
	    esac
  done < <(tar -tzf "$archive")
}

reject_unsafe_archive_types() {
  local archive="$1"
  local line
  local type
  while IFS= read -r line; do
    type="${line:0:1}"
    case "$type" in
      -|d)
        ;;
      *)
        echo "unsafe archive entry type: $line" >&2
        exit 1
        ;;
    esac
  done < <(tar -tvzf "$archive")
}

reject_unsafe_source_entries() {
  local data_dir="$1"
  local unsafe_entry=""
  unsafe_entry="$(find "$data_dir" -path "$data_dir/backups" -prune -o ! -type f ! -type d -print -quit)"
  if [[ -n "$unsafe_entry" ]]; then
    echo "unsafe data entry for backup: $unsafe_entry" >&2
    exit 1
  fi

  unsafe_entry="$(find "$data_dir" -path "$data_dir/backups" -prune -o -type f -links +1 -print -quit)"
  if [[ -n "$unsafe_entry" ]]; then
    echo "hardlinked data entry for backup: $unsafe_entry" >&2
    exit 1
  fi
}

normalize_data_permissions() {
  local data_dir="$1"
  local backup_dir="${2:-}"

  if [[ -n "$backup_dir" ]]; then
    find "$data_dir" -path "$backup_dir" -prune -o -type d -exec chmod 700 {} +
    find "$data_dir" -path "$backup_dir" -prune -o -type f -exec chmod 600 {} +
  else
    find "$data_dir" -type d -exec chmod 700 {} +
    find "$data_dir" -type f -exec chmod 600 {} +
  fi
  chmod 700 "$data_dir"
}

backup_data() {
  local data_dir="${1:-$data_dir_default}"
  local backup_dir="${2:-$backup_dir_default}"
  if [[ ! -d "$data_dir" ]]; then
    echo "data directory not found: $data_dir" >&2
    exit 1
  fi
  reject_unsafe_source_entries "$data_dir"

  umask 077
  mkdir -p "$backup_dir"
  chmod 700 "$backup_dir"
  local timestamp
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  local archive
  local suffix
  while :; do
    suffix="$(printf '%04d%04d' "$RANDOM" "$RANDOM")"
    archive="$backup_dir/flowark-dashboard-data-$timestamp-$suffix.tar.gz"
    [[ ! -e "$archive" ]] && break
  done
  tar --exclude='./backups' -C "$data_dir" -czf "$archive" .
  chmod 600 "$archive"
  (cd "$backup_dir" && sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256")
  chmod 600 "$archive.sha256"
  printf '%s\n' "$archive"
}

prepare_data_dir() {
  local data_dir="${1:-$data_dir_default}"
  local backup_dir="${2:-$backup_dir_default}"

  umask 077
  mkdir -p "$data_dir" "$backup_dir"
  reject_unsafe_source_entries "$data_dir"

  normalize_data_permissions "$data_dir" "$backup_dir"
  chmod 700 "$data_dir" "$backup_dir"
  printf 'prepared %s with backups at %s\n' "$data_dir" "$backup_dir"
}

list_backups() {
  local backup_dir="${1:-$backup_dir_default}"
  if [[ ! -d "$backup_dir" ]]; then
    echo "backup directory not found: $backup_dir" >&2
    exit 1
  fi
  find "$backup_dir" -maxdepth 1 -type f -name 'flowark-dashboard-data-*.tar.gz' -printf '%T@ %p\n' \
    | sort -nr \
    | cut -d' ' -f2-
}

prune_backups() {
  local backup_dir="${1:-$backup_dir_default}"
  local keep_count="${2:-14}"
  if [[ ! -d "$backup_dir" ]]; then
    echo "backup directory not found: $backup_dir" >&2
    exit 1
  fi
  if [[ ! "$keep_count" =~ ^[0-9]+$ ]] || (( keep_count < 1 )); then
    echo "keep_count must be a positive integer" >&2
    exit 1
  fi

  local index=0
  local entry
  local archive
  while IFS= read -r -d '' entry; do
    archive="${entry#* }"
    index=$((index + 1))
    if (( index > keep_count )); then
      rm -f -- "$archive"
      rm -f -- "$archive.sha256"
      printf 'deleted %s\n' "$archive"
    fi
  done < <(find "$backup_dir" -maxdepth 1 -type f -name 'flowark-dashboard-data-*.tar.gz' -printf '%T@ %p\0' | sort -z -nr)
}

restore_data() {
  local archive="${1:-}"
  local data_dir="${2:-$data_dir_default}"
  local force="${3:-}"
  if [[ -z "$archive" ]]; then
    usage
    exit 2
  fi
  if [[ ! -f "$archive" ]]; then
    echo "archive not found: $archive" >&2
    exit 1
  fi
  if [[ -f "$archive.sha256" ]]; then
    (cd "$(dirname "$archive")" && sha256sum -c "$(basename "$archive").sha256") >/dev/null
  fi
  reject_unsafe_archive_paths "$archive"
  reject_unsafe_archive_types "$archive"

  mkdir -p "$data_dir"
  if find "$data_dir" -mindepth 1 -maxdepth 1 | read -r _ && [[ "$force" != "--force" ]]; then
    echo "data directory is not empty; pass --force to replace it: $data_dir" >&2
    exit 1
  fi

  restore_tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$restore_tmp_dir"' EXIT
  tar --no-same-owner --no-same-permissions -xzf "$archive" -C "$restore_tmp_dir"

  if [[ "$force" == "--force" ]]; then
    find "$data_dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  fi
  cp -a "$restore_tmp_dir"/. "$data_dir"/
  normalize_data_permissions "$data_dir"
  echo "restored $archive to $data_dir"
}

main() {
  require_command tar
  require_command find
  require_command sha256sum

  local command="${1:-}"
  shift || true
  case "$command" in
    prepare) prepare_data_dir "$@" ;;
    backup) backup_data "$@" ;;
    list) list_backups "$@" ;;
    prune) prune_backups "$@" ;;
    restore) restore_data "$@" ;;
    *) usage; exit 2 ;;
  esac
}

main "$@"
