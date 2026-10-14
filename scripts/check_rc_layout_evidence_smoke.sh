#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

SERVER_ROOT="/servidor/ark"

usage() {
  cat >&2 <<'EOF'
Usage: scripts/check_rc_layout_evidence_smoke.sh --candidate-root PATH

Validates the fixed RC layout-only target sets against a copied second-source
candidate root. This is not a base-fixture smoke; it must compare a distinct
candidate root and fail on readiness gaps. Final RC/stable gates need a
second-source root freshly assembled for the intended HEAD, including current
bool-tail metadata; do not reuse a historical published-RC root such as
v0.1.0-rc.1 or v0.1.0-rc.2.
EOF
}

is_under_path() {
  local path="$1"
  local parent="$2"

  [[ "${path}" == "${parent}" || "${path}" == "${parent}/"* ]]
}

reject_protected_path() {
  local label="$1"
  local action="$2"
  local path="$3"
  local absolute_path
  local resolved_path

  absolute_path="$(realpath -s -m "${path}")"
  if is_under_path "${absolute_path}" "${SERVER_ROOT}"; then
    printf '%s must not %s protected server root %s: %s\n' \
      "${label}" "${action}" "${SERVER_ROOT}" "${absolute_path}" >&2
    exit 2
  fi

  resolved_path="$(realpath -m "${path}")"
  if is_under_path "${resolved_path}" "${SERVER_ROOT}"; then
    printf '%s must not %s protected server root %s: %s\n' \
      "${label}" "${action}" "${SERVER_ROOT}" "${resolved_path}" >&2
    exit 2
  fi
}

candidate_root=""
while (($# > 0)); do
  case "$1" in
    --candidate-root)
      if (($# < 2)); then
        printf '--candidate-root requires a path\n' >&2
        usage
        exit 2
      fi
      candidate_root="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${candidate_root}" ]]; then
  printf 'Missing required --candidate-root\n' >&2
  usage
  exit 2
fi

reject_protected_path "--candidate-root" "read from" "${candidate_root}"

python3 scripts/compare_reflection_snapshots.py \
  --base-root tests/fixtures/ufunction_snapshots \
  --candidate-root "${candidate_root}" \
  --readiness-report \
  --target-set minimal-second-source-intake \
  --target-set structure-observer-intake \
  --target-set chat-message-intake \
  --fail-on-readiness-gaps
